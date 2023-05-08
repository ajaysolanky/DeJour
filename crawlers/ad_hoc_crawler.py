import logging
import pandas as pd
from .base_crawler import BaseCrawler
from newspaper import Article

class AdHocCrawler(BaseCrawler):
    def __init__(self, url, vector_db, news_db, add_summaries, delete_old):
        
        super().__init__(vector_db, news_db, add_summaries, delete_old)
        self.url = url

    def fetch_news_df(self):
        a = Article(url=self.url)
        all_news = []
        a.download()
        a.parse()
        if "video" in a.url:
            logging.error("Cannot process ad-hoc article that is video")
            raise Exception('Cannot process video')
        if a.url is None or a.url == "":
            logging.error("Cannot process ad hoc article with no url")
            raise Exception('Cannot process ad hoc article with no url')
        if a.title is None or a.title == "":
            logging.error(f"Article has no title. Falling back to url: {a.url}")
            title = a.url
        else:
            title = a.title
        
        all_news.append({
            "url": a.url,
            "title": title
        })

        return pd.DataFrame(all_news)
