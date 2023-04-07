import pandas as pd
from collections import defaultdict
from newspaper import Article
from datetime import datetime
import pytz

from text_splitter import HardTokenSpacyTextSplitter
from utils import HiddenPrints, TokenCountCalculator, unstructured_time_string_to_structured

class BaseCrawler:
    CHUNK_SIZE_TOKENS = 300
    CHUNK_OVERLAP_TOKENS = int(CHUNK_SIZE_TOKENS * .2)
    SEPARATOR = '\n'
    MIN_SPLIT_WORDS = 5

    def __init__(self, vector_db, news_db):
        self.vector_db = vector_db
        self.news_db = news_db
        self.failed_dl_cache = set()
        self.get_num_tokens = TokenCountCalculator().get_num_tokens

    def fetch_news_df(self):
        raise NotImplementedError()
    
    def augment_data(self, url):
            print (f"fetching article @ url: {url}")
            # article = self.get_article_obj_from_url(url)
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
                "publish_timestamp": getattr(article, "publish_date", None).isoformat() if getattr(article, "publish_date", None) else None,
                "fetch_timestamp": pytz.utc.localize(datetime.utcnow()).isoformat()
            })
    
    def fetch_news_df_filtered(self):
        news_df = self.fetch_news_df()

        matched_artcles = self.news_db.get_matched_articles(news_df.url)

        new_news_df = news_df[news_df['url'].isin(matched_artcles | self.failed_dl_cache) == False]

        print(f"{len(matched_artcles)} articles already exist in the db. {new_news_df.shape[0]} articles remain.")

        if new_news_df.shape[0] == 0:
            return None


        fetched_data = new_news_df.url.apply(self.augment_data)
        new_news_df = new_news_df.join(fetched_data)

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
            metadata = {
                "title": r.title,
                "source": r.url,
                "publish_timestamp": r.publish_timestamp,
                "fetch_timestamp": r.fetch_timestamp,
                "top_image_url": r.top_image_url
            }
            metadatas.extend([metadata] * len(splits))
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
        #TODO: prolly don't wanna store embedding ids in the news db
        copy_df['embedding_ids'] = pd.Series(idc_id_map_stred)

        #TODO: use commits so we can do this first and then unwind if vector db update fails
        print("adding news to news db")
        self.news_db.add_news_df(copy_df)
        print("finished adding news to news db")

    def full_update(self):
        new_news_df = self.fetch_news_df_filtered()
        if new_news_df is not None:
            self.add_new_news_to_dbs(new_news_df)
