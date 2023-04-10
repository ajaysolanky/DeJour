from newspaper.source import Category

from .base_source import BaseSource

class ViceSource(BaseSource):
    BASE_URL = 'https://www.vice.com/'
    USE_PYPPETEER = True

    def set_categories(self):
        category_urls = [
            'https://www.vice.com/en/section/news',
            'https://www.vice.com/en/section/tech',
            'https://www.vice.com/en/section/world'
        ]
        self.categories = [Category(url=url) for url in category_urls]

    def purge_articles(self, reason, articles):
        if reason == 'url':
            articles[:] = [a for a in articles if ('/article/' in a.url and a.title is not None)]
        elif reason == 'body':
            articles[:] = [a for a in articles if a.is_valid_body()]
        return articles
