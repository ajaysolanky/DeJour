import pandas as pd

from .base_crawler import BaseCrawler

class SourceCrawler(BaseCrawler):
    def __init__(self, source, vector_db, news_db):
        super().__init__(vector_db, news_db)
        self.source = source

    def fetch_news_df(self):
        source_build = self.source.get_build(memoize_articles=False)
        articles = source_build.articles

        print(f"fetched {len(articles)} articles")

        all_news = []
        for a in articles:
            a.download()
            a.parse()
            all_news.append({
                "url": a.url,
                "title": a.title
            })

        all_news = [{
            "url": a.url,
            "title": a.title
        } for a in articles]

        return pd.DataFrame(all_news)
