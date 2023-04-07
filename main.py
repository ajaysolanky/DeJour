# TODO: same article can be pulled twice in the same "new_news_df" df from diff sources
# TODO: safeguard against same vector getting added twice
# TODO: clean out muck from photo captions and other random garbage
# TODO: same text chunk is getting added twice
# TODO: delete old news
# TODO: try SpacyTextSplitter
# TODO: are there race conditions with the vector store?
# TODO: exponentially decay old answers
# TODO: experiment with chunk overlap

import time
from datetime import datetime
from langchain import OpenAI
from langchain.chains import VectorDBQAWithSourcesChain

from news_db import NewsDB
from query import ChatQuery
from vector_db import VectorDBWeaviateCURL, VectorDBWeaviatePythonClient
from publisher_enum import PublisherEnum
from crawlers.base_crawler import BaseCrawler

class Runner(object):
    CRAWLER_SLEEP_SECONDS = 60 * 15
    def __init__(self, crawler: BaseCrawler, publisher: PublisherEnum):
        # self.vector_db = VectorDBWeaviateCURL(publisher)
        self.vector_db = VectorDBWeaviatePythonClient(publisher)
        # self.vector_db = VectorDBLocal(publisher)
        self.news_db = NewsDB(publisher)
        self.crawler = crawler(
            self.vector_db,
            self.news_db
            )
        self.chain = VectorDBQAWithSourcesChain.from_llm(
            llm=OpenAI(temperature=0),
            vectorstore=self.vector_db.get_vectorstore()
            )

    def run_crawler(self):
        while True:
            self.crawler.full_update()
            print(f"{str(datetime.now())}\nCrawl complete. Sleeping for {self.CRAWLER_SLEEP_SECONDS} seconds. Time: {datetime.now()}")
            time.sleep(self.CRAWLER_SLEEP_SECONDS)
