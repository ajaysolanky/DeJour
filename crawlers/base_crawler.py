import time
import logging
import pandas as pd
from collections import defaultdict
from newspaper import Article
from datetime import datetime
import pytz
from abc import ABC, abstractmethod

from text_splitter import HardTokenSpacyTextSplitter
from utils import HiddenPrints, TokenCountCalculator, unstructured_time_string_to_structured, get_isoformat_and_add_tz_if_not_there

class BaseCrawler(ABC):
    CHUNK_SIZE_TOKENS = 300
    CHUNK_OVERLAP_TOKENS = int(CHUNK_SIZE_TOKENS * .2)
    SEPARATOR = '\n'
    MIN_SPLIT_WORDS = 5
    CRAWLER_SLEEP_SECONDS = 900
    UPLOAD_BATCH_SIZE = 10

    def __init__(self, vector_db, news_db):
        self.vector_db = vector_db
        self.news_db = news_db
        self.failed_dl_cache = set()
        self.get_num_tokens = TokenCountCalculator().get_num_tokens

    @abstractmethod
    def fetch_news_df(self):
        pass
    
    def augment_data(self, url):
            print (f"fetching article @ url: {url}")
            article = Article(url=url)
            try:
                article.download()
                article.parse()
            except:
                article = None
            if article is None:
                article = object()
            return pd.Series({
                "text": getattr(article, "text", None),
                "preview": None,
                "top_image_url": getattr(article, "top_image", None),
                "authors": ','.join(getattr(article, "authors", [])),
                "publish_timestamp": get_isoformat_and_add_tz_if_not_there(getattr(article, "publish_date", None)),
                "fetch_timestamp": pytz.utc.localize(datetime.utcnow()).isoformat()
            })

    def fetch_and_upload_news(self):
        logging.info("fetching news df")
        news_df = self.fetch_news_df()

        logging.info("getting matched articles")
        matched_artcles = self.news_db.get_matched_articles(news_df.url.tolist())

        logging.info("filtering news df")
        new_news_df = news_df[news_df['url'].isin(matched_artcles | self.failed_dl_cache) == False]

        logging.info(f"{len(matched_artcles)} articles already exist in the db. {new_news_df.shape[0]} articles remain.")

        if new_news_df.shape[0] == 0:
            return None

        # Process the augment calls and upload the news in the same batch
        num_batches = (new_news_df.shape[0] + self.UPLOAD_BATCH_SIZE - 1) // self.UPLOAD_BATCH_SIZE
        for i in range(num_batches):
            start = i * self.UPLOAD_BATCH_SIZE
            end = min((i + 1) * self.UPLOAD_BATCH_SIZE, new_news_df.shape[0])
            batch_df = new_news_df.iloc[start:end]
            
            fetched_batch_data = batch_df.url.apply(self.augment_data)
            batch_df = batch_df.join(fetched_batch_data)

            self.failed_dl_cache |= set(batch_df[batch_df['text'].isna()].url)
            batch_df = batch_df[batch_df['text'].isna() == False]

            printable_titles = '\n'.join(batch_df.title)
            logging.info(f"Batch {i + 1} of {num_batches} article titles:\n{printable_titles}")

            self.add_news_to_dbs(batch_df)
            logging.info(f"Batch {i + 1} of {num_batches} uploaded successfully")

        return new_news_df

    def add_news_to_dbs(self, new_news_df):
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
            for split_idx in range(len(splits)):
                metadatas.append({
                    "title": r.title,
                    "source": r.url,
                    "publish_timestamp": r.publish_timestamp,
                    "fetch_timestamp": r.fetch_timestamp,
                    "top_image_url": r.top_image_url,
                    "idx": split_idx
                })
            orig_idces.extend([i] * len(splits))
        
        logging.info("adding texts to VectorDB")
        new_ids = self.vector_db.add_texts(docs, metadatas)
        logging.info("finished adding texts to VectorDB")

        idc_id_map = defaultdict(list)
        for new_id, orig_idx in zip(new_ids, orig_idces):
            idc_id_map[orig_idx].append(new_id)

        idc_id_map_stred = {k: ','.join(v) for k,v in idc_id_map.items()}
        
        # so it doesn't edit the input df
        copy_df = new_news_df.copy()
        #TODO: prolly don't wanna store embedding ids in the news db
        copy_df['embedding_ids'] = pd.Series(idc_id_map_stred)

        #TODO: use commits so we can do this first and then unwind if vector db update fails
        logging.info("adding news to news db")
        self.news_db.add_news_df(copy_df)
        logging.info("finished adding news to news db")

    def run_crawler(self):
        while True:
            self.fetch_and_upload_news()
            logging.info(f"{str(datetime.now())}\nCrawl complete. Sleeping for {self.CRAWLER_SLEEP_SECONDS} seconds. Time: {datetime.now()}")
            time.sleep(self.CRAWLER_SLEEP_SECONDS)