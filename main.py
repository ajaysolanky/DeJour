# TODO: same article can be pulled twice in the same "new_news_df" df from diff sources
# TODO: safeguard against same vector getting added twice
# TODO: investigate how langchain is doing Q+A
# TODO: clean out muck from photo captions and other random garbage
# TODO: same text chunk is getting added twice
# TODO: wtf is this: `WARNING: Created a chunk of size 3072, which is longer than the specified 1500`
# TODO: delete old news
# TODO: filter photo captions
# TODO: try SpacyTextSplitter
# TODO: are there race conditions with the vector store?
# TODO: exponentially decay old answers
# TODO: periodically reload the db in the query thread
# TODO: experiment with chunk overlap

import copy
import os
import threading
from gnews import GNews
from datetime import datetime
import pandas as pd
import faiss
import openai
from langchain import OpenAI
from langchain.chains import VectorDBQAWithSourcesChain
from langchain.embeddings import OpenAIEmbeddings
from text_splitter import HardTokenSpacyTextSplitter
from langchain.docstore.document import Document
import sqlite3
import pickle
from langchain.vectorstores import FAISS
from collections import defaultdict
import time
import nltk
import numpy as np
import tiktoken

# from embeddings_model import EmbeddingsModel
from utils import HiddenPrints, TokenCountCalculator

nltk.download('punkt')
openai.api_key = os.getenv('OAI_TK', 'not the token')

class Runner:
    GN_CRAWLER_SLEEP_SECONDS = 60 * 15
    def __init__(self):
        self.vector_db = VectorDB()
        self.news_db = NewsDB()
        self.mq = ManualQuery(self.vector_db)
        self.gn_crawler = GNCrawler(
            self.vector_db,
            self.news_db
            )
        self.chain = VectorDBQAWithSourcesChain.from_llm(
            llm=OpenAI(temperature=0),
            vectorstore=self.vector_db.store
            )

    def run_gn_crawler(self):
        while True:
            self.gn_crawler.full_update()
            print(f"Crawl complete. Sleeping for {self.GN_CRAWLER_SLEEP_SECONDS} seconds. Time: {datetime.now()}")
            time.sleep(self.GN_CRAWLER_SLEEP_SECONDS)

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
            # result = self.chain({"question": question})
            output = f"Answer: {result['answer']}\nSources: {result['sources']}"
            print(output)

    # def run(self):
    #     # import pdb; pdb.set_trace()
    #     gn_crawl_th = threading.Thread(
    #         target=self.run_gn_crawler,
    #         args=()
    #         )
    #     gn_crawl_th.start()
    #     # # TODO: hacky
    #     while self.vector_db.store is None:
    #         time.sleep(5)
    #     self.run_query_thread()

class ManualQuery:
    SEPARATOR = "\n* "
    MAX_SECTION_LEN = 1000
    MAX_RESPONSE_TOKENS = 300
    COMPLETIONS_MODEL = "text-davinci-003"
    CHAT_MODEL = "gpt-3.5-turbo"
    COMPLETIONS_API_PARAMS = {
        # We use temperature of 0.0 because it gives the most predictable, factual answer.
        "temperature": 0.0,
        "max_tokens": MAX_RESPONSE_TOKENS,
        "model": COMPLETIONS_MODEL,
    }
    CHAT_API_PARAMS = {
        "temperature": 0.0,
        "max_tokens": MAX_RESPONSE_TOKENS,
        "model": CHAT_MODEL
    }

    def __init__(self, vector_db):
        self.vector_db = vector_db
        self.get_num_tokens = TokenCountCalculator().get_num_tokens
        self.separator_len = self.get_num_tokens(self.SEPARATOR)

    def get_top_docs(self, query, k=10):
        # I think the first arg is distances
        embedding = self.vector_db.get_embedding(query)
        _, indices = self.vector_db.store.index.search(np.array([embedding], dtype=np.float32), k)
        docs = []
        for i in indices[0]:
            if i == -1:
                # This happens when not enough docs are returned.
                continue
            _id = self.vector_db.store.index_to_docstore_id[i]
            doc = self.vector_db.store.docstore.search(_id)
            if not isinstance(doc, Document):
                raise ValueError(f"Could not find document for id {_id}, got {doc}")
            docs.append(doc)
        return docs

    def construct_prompt(self, query):
        """
        Fetch relevant 
        """        
        most_relevant_docs = self.get_top_docs(query)

        chosen_sections = []
        chosen_sections_sources = []
        chosen_sections_len = 0
        for doc in most_relevant_docs:
            # Add contexts until we run out of space.        
            doc_text = doc.page_content
            doc_metadata = doc.metadata
            
            # TODO: preprocess and store num tokens so we don't have to redo this every time
            chosen_sections_len += self.get_num_tokens(doc_text) + self.separator_len
            if chosen_sections_len > self.MAX_SECTION_LEN:
                break
                
            chosen_sections.append(self.SEPARATOR + doc_text.replace("\n", " "))
            chosen_sections_sources.append(doc_metadata['source'])
                
        # # Useful diagnostic information
        # print(f"Selected {len(chosen_sections)} document sections:")
        
        # header = """Answer the question as truthfully as possible using the provided context, and if the answer is not contained within the text below, say "I don't know."\n\nContext:\n"""
        header = """Answer the question as truthfully as possible using the provided context, and if the answer is not contained within the text below, say "I don't know." Do not reference the fact that you have been provided with context.\n\nContext:\n"""
        
        return (
            header + "".join(chosen_sections) + "\n\n Q: " + query + "\n A:",
            chosen_sections_sources
        )

    def answer_with_openai_completions(self, prompt):
        response = openai.Completion.create(
            prompt=prompt,
            **self.COMPLETIONS_API_PARAMS
            )
        return response["choices"][0]["text"].strip(" \n")
    
    def answer_with_openai_chat(self, prompt):
        response = openai.ChatCompletion.create(
            messages=[
                {"role": "system", "content": "You are an AI assistant that answers questions about the news truthfully."},
                {"role": "user", "content": prompt}
            ],
            **self.CHAT_API_PARAMS
        )
        return response['choices'][0]['message']['content']

    def answer_query_with_context(self, query):
        prompt, sources = self.construct_prompt(query)
        print(f"prompt:\n\n{prompt}\n\n")
        # answer = self.answer_with_openai_completions(prompt)
        answer = self.answer_with_openai_chat(prompt)
        return {
            "answer": answer,
            "sources": set(sources)
        }

class GNCrawler:
    CHUNK_SIZE_TOKENS = 300
    CHUNK_OVERLAP_TOKENS = int(CHUNK_SIZE_TOKENS * .2)
    SEPARATOR = '\n'
    MIN_SPLIT_WORDS = 5

    def __init__(self, vector_db, news_db):
        self.gn_client = GNews()
        self.vector_db = vector_db
        self.news_db = news_db
        self.failed_dl_cache = set()
        self.get_num_tokens = TokenCountCalculator().get_num_tokens

    def get_article_obj_from_url(self, url):
        # this call is super noisy, so I'm silencing it
        with HiddenPrints():
            return self.gn_client.get_full_article(url)

    def fetch_new_news_df(self):
        top_news = self.gn_client.get_top_news()

        topics = [
            'WORLD',
            'NATION',
            'BUSINESS',
            'TECHNOLOGY',
            'ENTERTAINMENT',
            'SPORTS',
            'SCIENCE',
            'HEALTH'
            ]
        topics_news = []
        for topic in topics:
            topics_news += self.gn_client.get_news_by_topic(topic)

        all_news = top_news + topics_news

        print(f"fetched {len(all_news)} articles")

        news_df = pd.DataFrame(all_news)

        matched_artcles = self.news_db.get_matched_articles(news_df.url)

        new_news_df = news_df[news_df['url'].isin(matched_artcles | self.failed_dl_cache) == False]

        print(f"{len(matched_artcles)} articles already exist in the db. {new_news_df.shape[0]} articles remain.")

        def fetch_text(r):
            print(f"fetching article @ url: {r.url}")
            article = self.get_article_obj_from_url(r.url)
            if article:
                return article.text
            else:
                return None

        new_news_df['text'] = new_news_df.apply(fetch_text, axis=1)
        self.failed_dl_cache |= set(new_news_df[new_news_df['text'].isna()].url)
        new_news_df = new_news_df[new_news_df['text'].isna() == False]
        print(f"These urls failed to download: {self.failed_dl_cache}. Finally {new_news_df.shape[0]} articles will be processed.")
        printable_titles = '\n'.join(new_news_df.title)
        print(f"new article titles:\n{printable_titles}")

        return new_news_df

    def add_new_news_to_dbs(self, new_news_df):
        """
        Takes a new news df and returns
        
        """
        if new_news_df.shape[0] == 0:
            return
        text_splitter = HardTokenSpacyTextSplitter(
            self.get_num_tokens,
            chunk_size=self.CHUNK_SIZE_TOKENS,
            chunk_overlap=self.CHUNK_OVERLAP_TOKENS,
            separator=self.SEPARATOR
            )
        docs = []
        metadatas = []
        orig_idces = []
        for i, r in new_news_df.iterrows():
            splits = text_splitter.split_text(r.text)
            splits = [s for s in splits if len(s.split(' ')) > self.MIN_SPLIT_WORDS]
            docs.extend(splits)
            metadatas.extend([{"source": r.url}] * len(splits))
            orig_idces.extend([i] * len(splits))
        
        print("adding texts to VectorDB")
        new_ids = self.vector_db.add_texts(docs, metadatas)
        print("finished adding texts to VectorDB")

        idc_id_map = defaultdict(list)
        for new_id, orig_idx in zip(new_ids, orig_idces):
            idc_id_map[orig_idx].append(new_id)

        idc_id_map_stred = {k: ','.join(v) for k,v in idc_id_map.items()}
        
        # so it doesn't edit the input df
        copy_df = new_news_df.copy()
        copy_df['embedding_ids'] = pd.Series(idc_id_map_stred)

        print("adding news to news db")
        self.news_db.add_news_df(copy_df)
        print("finished adding news to news db")
    
    def full_update(self):
        new_news_df = self.fetch_new_news_df()
        self.add_new_news_to_dbs(new_news_df)
    
class NewsDB:
    COLUMNS = [
        'title',
        'url',
        'embedding_ids',
        'date'
    ]
    TABLE_NAME = 'news_data'
    DB_FILE_NAME = 'news.db'

    def __init__(self):
        con = self.get_con()
        cur = con.cursor()
        cur.execute(f"CREATE TABLE IF NOT EXISTS {self.TABLE_NAME}({', '.join(self.COLUMNS)})")
        con.commit()

    def get_con(self):
        return sqlite3.connect(self.DB_FILE_NAME)

    def add_news_df(self, news_df):
        copy_df = news_df.copy()
        copy_df['date'] = datetime.now().strftime('%Y-%m-%d')
        data = list(copy_df[self.COLUMNS].itertuples(index=False, name=None))
        con = self.get_con()
        cur = con.cursor()
        cur.executemany(f"INSERT INTO {self.TABLE_NAME} VALUES({', '.join(['?'] * len(self.COLUMNS))})", data)
        con.commit()


    def get_matched_articles(self, urls):
        """
        <input>
        urls: list of urls

        <return>
        set of the queried urls that already exist in the news db
        """
        cur = self.get_con().cursor()
        # TODO: could be better to insert the ids and do a join
        res = cur.execute(f"SELECT url FROM {self.TABLE_NAME} WHERE url IN ({', '.join(['?']*len(urls))})", urls)
        exist_set = set(e[0] for e in res.fetchall())
        return exist_set
    
    def drop_table(self):
        con = self.get_con()
        cur = con.cursor()
        cur.execute(f"DROP TABLE IF EXISTS {self.TABLE_NAME}")
        con.commit()

class VectorDB:
    INDEX_FILE_NAME = 'docs.index'
    STORE_FILE_NAME = 'faiss_store.pkl'
    def __init__(self):
        self.store = None
        if not os.path.isfile(self.INDEX_FILE_NAME):
            init_store = FAISS.from_texts(['test'], OpenAIEmbeddings(), metadatas=[{"source":'test'}])
            self.save_db(init_store)
        self.load_db()

    def load_db(self):
        index = faiss.read_index(self.INDEX_FILE_NAME)
        with open(self.STORE_FILE_NAME, "rb") as f:
            store = pickle.load(f)
            store.index = index
        self.store = store
    
    def add_texts(self, texts, metadatas):
        new_ids = self.store.add_texts(
            texts,
            metadatas
            )
        self.save_db()
        return new_ids
    
    def get_embedding(self, text):
        return self.store.embedding_function(text)

    def save_db(self, store_obj=None):
        if not store_obj:
            store_obj = self.store
        faiss.write_index(store_obj.index, self.INDEX_FILE_NAME)
        store_copy = copy.deepcopy(store_obj)
        store_copy.index = None
        with open(self.STORE_FILE_NAME, 'wb') as f:
            pickle.dump(store_copy, f)
