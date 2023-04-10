from newspaper.source import Category

from .base_source import BaseSource

class BBCIndiaSource(BaseSource):
    BASE_URL = 'https://www.bbc.com/news/world/asia/india'
    USE_PYPPETEER = True

    def set_categories(self):
        category_urls = [
            'https://www.bbc.com/news/world/asia/india',
        ]
        self.categories = [Category(url=url) for url in category_urls]

    def purge_articles(self, reason, articles):
        if reason == 'url':
            articles[:] = [a for a in articles if ('/news/world-asia-' in a.url)]
        elif reason == 'body':
            articles[:] = [a for a in articles if a.is_valid_body()]
        return articles
