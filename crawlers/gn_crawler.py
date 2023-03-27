from gnews import GNews
import pandas as pd
from collections import defaultdict

from text_splitter import HardTokenSpacyTextSplitter
from utils import HiddenPrints, TokenCountCalculator
from .crawler import Crawler

class GNCrawler(Crawler):
    def __init__(self, vector_db, news_db):
        super().__init__(vector_db, news_db)
        self.gn_client = GNews()

    def fetch_news_df(self):
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

        return pd.DataFrame(all_news)
