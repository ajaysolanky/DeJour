import logging
import hashlib
import os
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime
from abc import ABC, abstractmethod
import firebase_admin
from firebase_admin import credentials, firestore, app_check

from publisher_enum import PublisherEnum
from utils import LOCAL_DB_FOLDER

# to read dates from db: https://stackoverflow.com/questions/3305413/how-to-preserve-timezone-when-parsing-date-time-strings-with-strptime
class NewsDB(ABC):
    COLUMNS = [
        'title',
        'url',
        'embedding_ids',
        'fetch_date',
        'text',
        'preview',
        'top_image_url',
        'authors',
        'publish_date'
    ]
    TABLE_NAME_PREFIX = 'news_data'

    def __init__(self, publisher) -> None:
        self.publisher = publisher

    def get_table_name(self):
        return f"{self.TABLE_NAME_PREFIX}_{self.publisher.value}"

    @abstractmethod
    def add_news_df(self, news_df):
        pass

    @abstractmethod
    def get_news_data(self, urls, fields):
        pass

    def get_news_id(self, url):
        """
        args:
            url (str): the url of the news article
        
        Returns:
            str: id string for the news object
        """
        return hashlib.md5(url.encode('utf-8')).hexdigest()

    @abstractmethod
    def get_matched_articles(self, urls):
        """
        args:
            urls (list[str]): list of urls

        Returns:
            Set: Set of urls that already exist in the DB
        """
        pass
    
    @abstractmethod
    def create_table(self):
        pass

    @abstractmethod
    def drop_table(self):
        pass

class NewsDBLocal(NewsDB):
    "Sqlite3 implementation"
    def __init__(self, publisher: PublisherEnum) -> None:
        super().__init__(publisher)
        dir_path = f"{LOCAL_DB_FOLDER}/{self.publisher.value}/news_db/"
        self.db_file_path = dir_path + 'news.db'
        if not os.path.isfile(self.db_file_path):
            os.makedirs(dir_path)
        self.create_table()

    def get_con(self):
        return sqlite3.connect(self.db_file_path)
    
    def get_table_name(self):
        return self.TABLE_NAME_PREFIX
    
    def add_news_df(self, news_df):
        con = self.get_con()
        cur = con.cursor()
        table_info = cur.execute(f"PRAGMA table_info({self.get_table_name()});").fetchall()
        existing_table_columns = [c[1] for c in table_info]

        copy_df = news_df.copy()
        for tc in existing_table_columns:
            if tc not in copy_df.columns:
                copy_df[tc] = None
            copy_df[tc] = copy_df[tc].astype(str)
        data = list(copy_df[existing_table_columns].itertuples(index=False, name=None))
        cur.executemany(f"INSERT INTO {self.get_table_name()} VALUES({', '.join(['?'] * len(existing_table_columns))})", data)
        con.commit()

    def create_table(self):
        con = self.get_con()
        cur = con.cursor()
        cur.execute(f"CREATE TABLE IF NOT EXISTS {self.get_table_name()}({', '.join(self.COLUMNS)})")
        con.commit()

    def get_news_data(self, urls, fields):
        cur = self.get_con().cursor()
        res = cur.execute(f"SELECT {','.join(fields)} FROM {self.get_table_name()} WHERE url IN ({', '.join(['?']*len(urls))})", urls)
        data = res.fetchall()
        return pd.DataFrame(data, columns=fields)
    
    def get_matched_articles(self, urls):
        matched = self.get_news_data(urls, fields=['url'])
        exist_set = set(matched.url.unique())
        return exist_set
    
    def drop_table(self):
        con = self.get_con()
        cur = con.cursor()
        cur.execute(f"DROP TABLE IF EXISTS {self.get_table_name()}")
        con.commit()

#TODO: Firestore database might not be the most scalable way of doing this, could be worth looking into other options
class NewsDBFirestoreDatabase(NewsDB):
    def __init__(self, publisher) -> None:
        super().__init__(publisher)
        if not firebase_admin._apps:
            cred = credentials.Certificate("./dejour_firebase_credentials.json")
            firebase_admin.initialize_app(cred)  # connecting to firebase

        self.db = firestore.client()

    def add_news_df(self, news_df):
        records = news_df.to_dict('records')

        collection_ref = self.db.collection(self.get_table_name())
        for record in records:
            id = self.get_news_id(record['url'])
            doc_ref = collection_ref.document(id)  # Create a new document for each record
            doc_ref.set(record)

        logging.info(f"Uploaded {len(records)} records to the '{self.get_table_name()}' collection in Firestore.")

    def get_news_data(self, urls, fields):
        documents = []
        for url in urls:
            # Fetch the document by 'url'
            doc_ref = self.db.collection(self.get_table_name()).document(url)
            doc = doc_ref.get()

            if doc.exists:
                doc_data = doc.to_dict()
                # Retrieve only the specified fields
                filtered_data = {field: doc_data.get(field) for field in fields}
                documents.append(filtered_data)
            else:
                logging.info(f"No document found with url: {url}")
                documents.append(None)

        return documents

    def check_existing_urls(self, urls):
        # Query documents with the specified URLs
        collection_ref = self.db.collection(self.get_table_name())
        query = collection_ref.where('url', 'in', urls)
        query_results = query.stream()

        # Collect the 'url' values of the existing documents
        existing_urls = set(doc.to_dict()['url'] for doc in query_results)

        return existing_urls

    def get_matched_articles(self, urls):
        CHUNK_SIZE = 10
        def query_existing_urls(chunk):
            collection_ref = self.db.collection(self.get_table_name())
            query = collection_ref.where('url', 'in', chunk)
            query_results = query.stream()
            return [doc.to_dict()['url'] for doc in query_results]

        existing_urls = []
        for i in range(0, len(urls), CHUNK_SIZE):
            chunk = urls[i:i + CHUNK_SIZE]
            existing_urls.extend(query_existing_urls(chunk))

        return set(existing_urls)
    
    def create_table(self):
        pass

    def drop_table(self):
        pass