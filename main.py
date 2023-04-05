# TODO: same article can be pulled twice in the same "new_news_df" df from diff sources
# TODO: safeguard against same vector getting added twice
# TODO: clean out muck from photo captions and other random garbage
# TODO: same text chunk is getting added twice
# TODO: delete old news
# TODO: try SpacyTextSplitter
# TODO: are there race conditions with the vector store?
# TODO: exponentially decay old answers
# TODO: experiment with chunk overlap

from datetime import datetime
import openai
from langchain import OpenAI
from langchain.chains import VectorDBQAWithSourcesChain
import time
import nltk
import os

from news_db import NewsDB
from query import ManualQuery, ChatQuery
from vector_db import VectorDBLocal, VectorDBWeaviate
from publisher_enum import PublisherEnum
from crawlers.base_crawler import BaseCrawler

nltk.download('punkt')
openai.api_key = os.getenv('OAI_TK', 'not the token')

class Runner(object):
    CRAWLER_SLEEP_SECONDS = 60 * 15
    def __init__(self, crawler: BaseCrawler, publisher: PublisherEnum):
        self.vector_db = VectorDBWeaviate(publisher)
        # self.vector_db = VectorDBLocal(publisher)
        self.news_db = NewsDB(publisher)
        self.mq = ManualQuery(self.vector_db, self.news_db)
        self.crawler = crawler(
            self.vector_db,
            self.news_db
            )
        self.chain = VectorDBQAWithSourcesChain.from_llm(
            llm=OpenAI(temperature=0),
            vectorstore=self.vector_db.store
            )
        self.cq = ChatQuery(self.vector_db, self.news_db)

    def run_crawler(self):
        while True:
            self.crawler.full_update()
            print(f"{str(datetime.now())}\nCrawl complete. Sleeping for {self.CRAWLER_SLEEP_SECONDS} seconds. Time: {datetime.now()}")
            time.sleep(self.CRAWLER_SLEEP_SECONDS)

    def get_result_langchain(self, question):
        return self.chain({"question": question})
    
    def get_result_manual(self, question):
        return self.mq.answer_query_with_context(question)

    def run_query_thread(self):
        while True:
            print('What is your question?')
            question = input()
            # result = self.get_result_langchain(question)
            result = self.get_result_manual(question)
            source_str = "\n".join(result['sources'])
            output = f"\nAnswer: {result['answer']}\n\nSources: {source_str}"
            print(output)
    
    def get_chat_result(self, chat_history, query):
        return self.cq.answer_query_with_context(chat_history, query)
