import time
import logging
import cleantext
import pandas as pd
from collections import defaultdict
from newspaper import Article
from datetime import datetime
import pytz
from abc import ABC, abstractmethod
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts.prompt import PromptTemplate

from prompts.all_prompts import ARTICLE_SUMMARIZATION_PROMPT
from text_splitter import HardTokenSpacyTextSplitter
from utils import TokenCountCalculator, get_isoformat_and_add_tz_if_not_there

class BaseCrawler(ABC):
    CHUNK_SIZE_TOKENS = 300
    CHUNK_OVERLAP_TOKENS = int(CHUNK_SIZE_TOKENS * .2)
    SEPARATOR = '\n'
    MIN_SPLIT_WORDS = 5
    CRAWLER_SLEEP_SECONDS = 900
    UPLOAD_BATCH_SIZE = 10
    SUMMARY_MODEL = 'gpt-3.5-turbo'
    SUMMARY_PROMPT = ARTICLE_SUMMARIZATION_PROMPT

    def __init__(self, vector_db, news_db, add_summaries):
        self.vector_db = vector_db
        self.news_db = news_db
        self.failed_dl_cache = set()
        self.get_num_tokens = TokenCountCalculator().get_num_tokens
        self.add_summaries = add_summaries

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
            date = getattr(article, "publish_date", None)
            print(f"Publish date: {date}")
            return pd.Series({
                "text": getattr(article, "text", None),
                "preview": None,
                "top_image_url": getattr(article, "top_image", None),
                "authors": ','.join(getattr(article, "authors", [])),
                "publish_timestamp": get_isoformat_and_add_tz_if_not_there(date),
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

            filter_series = (batch_df['text'].isna() | (batch_df['text'] == ''))
            self.failed_dl_cache |= set(batch_df[filter_series].url)
            batch_df = batch_df[filter_series == False]

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
        texts = []
        metadatas = []
        orig_idces = []
        for i, r in new_news_df.iterrows():
            cleaned_text = cleantext.clean(r.text, clean_all=False)
            base_metadata = {
                    "title": r.title,
                    "source": r.url,
                    "publish_timestamp": r.publish_timestamp,
                    "fetch_timestamp": r.fetch_timestamp,
                    "top_image_url": r.top_image_url,
                }
            if self.add_summaries:
                try:
                    summary_text = self.get_summary(cleaned_text, r.title)
                    summary_metadata = base_metadata | {"idx": -1, "is_summary": True}
                    texts.append(summary_text)
                    metadatas.append(summary_metadata)
                except Exception as e:
                    logging.info(f"Exception while generating summary: {e}")
            splits = text_splitter.split_text(cleaned_text)
            splits = [s for s in splits if len(s.split(' ')) > self.MIN_SPLIT_WORDS]
            texts.extend(splits)
            for split_idx in range(len(splits)):
                #TODO: should build some common interface with the weaviate class
                metadatas.append(base_metadata | {"idx": split_idx, "is_summary": False})
            orig_idces.extend([i] * len(splits))
        
        logging.info("adding texts to VectorDB")
        new_ids = self.vector_db.add_texts(texts, metadatas)
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

    def get_summary(self, article_text, article_title):
        #TODO: recursive summarization
        # don't overload the context window
        while self.get_num_tokens(article_text) > 3700:
            text_len = len(article_text)
            ten_pct_len = int(text_len * .1)
            article_text = article_text[:-ten_pct_len]
        summary_llm = ChatOpenAI(temperature=0, model_name=self.SUMMARY_MODEL)
        summary_prompt = PromptTemplate.from_template(self.SUMMARY_PROMPT)
        summarize_chain = LLMChain(
            llm=summary_llm,
            prompt=summary_prompt,
            )
        return summarize_chain.run(
            article_title=article_title,
            article_text=article_text
        )

    def run_crawler(self):
        while True:
            self.fetch_and_upload_news()
            logging.info(f"{str(datetime.now())}\nCrawl complete. Sleeping for {self.CRAWLER_SLEEP_SECONDS} seconds. Time: {datetime.now()}")
            time.sleep(self.CRAWLER_SLEEP_SECONDS)
