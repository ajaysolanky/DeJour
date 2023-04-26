import logging
import pandas as pd
from .base_crawler import BaseCrawler

class SourceCrawler(BaseCrawler):
    def __init__(self, source, vector_db, news_db, add_summaries):
        super().__init__(vector_db, news_db, add_summaries)
        self.source = source

    def fetch_news_df(self):
        source_build = self.source.get_build(memoize_articles=False)
        articles = source_build.articles

        logging.info(f"fetched {len(articles)} articles")

        all_news = []
        for a in articles:
            #TODO: article is dled twice
            a.download()
            a.parse()
            if "video" in a.url:
                continue
            if a.url is None or a.url == "":
                logging.info("skipping article with no url")
                continue
            if a.title is None or a.title == "":
                logging.info(f"skipping article with no title. Url: {a.url}")
                continue
            all_news.append({
                "url": a.url,
                "title": a.title
            })

        all_news = [{
            "url": a.url,
            "title": a.title
        } for a in articles]

        return pd.DataFrame(all_news)
