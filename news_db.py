import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime

import pytz

# to read dates from db: https://stackoverflow.com/questions/3305413/how-to-preserve-timezone-when-parsing-date-time-strings-with-strptime
class NewsDB(object):
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
    TABLE_NAME = 'news_data'

    def __init__(self, file_name_prefix):
        folder_name = ""
        self.db_file_name = folder_name + file_name_prefix + "_" + 'news.db'
        con = self.get_con()
        cur = con.cursor()
        cur.execute(f"CREATE TABLE IF NOT EXISTS {self.TABLE_NAME}({', '.join(self.COLUMNS)})")
        con.commit()

    def get_con(self):
        return sqlite3.connect(self.db_file_name)

    def add_news_df(self, news_df):
        con = self.get_con()
        cur = con.cursor()
        table_info = cur.execute(f"PRAGMA table_info({self.TABLE_NAME});").fetchall()
        existing_table_columns = [c[1] for c in table_info]

        copy_df = news_df.copy()
        for tc in existing_table_columns:
            if tc not in copy_df.columns:
                copy_df[tc] = None
            copy_df[tc] = copy_df[tc].astype(str)
        data = list(copy_df[existing_table_columns].itertuples(index=False, name=None))
        cur.executemany(f"INSERT INTO {self.TABLE_NAME} VALUES({', '.join(['?'] * len(existing_table_columns))})", data)
        con.commit()

    def get_news_data(self, urls, fields):
        cur = self.get_con().cursor()
        res = cur.execute(f"SELECT {','.join(fields)} FROM {self.TABLE_NAME} WHERE url IN ({', '.join(['?']*len(urls))})", urls)
        data = res.fetchall()
        return pd.DataFrame(data, columns=fields)

    def get_matched_articles(self, urls):
        """
        <input>
        urls: list of urls

        <return>
        set of the queried urls that already exist in the news db
        """
        matched = self.get_news_data(urls, fields=['url'])
        exist_set = set(matched.url.unique())
        return exist_set
    
    def drop_table(self):
        con = self.get_con()
        cur = con.cursor()
        cur.execute(f"DROP TABLE IF EXISTS {self.TABLE_NAME}")
        con.commit()