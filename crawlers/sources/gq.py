from newspaper.source import Category

from .custom_source import CustomSource

class GQSource(CustomSource):
    BASE_URL = 'https://www.gq.com/'

    def set_categories(self):
        self.categories = [Category(url='https://www.gq.com/style')]

    def purge_articles(self, reason, articles):
        if reason == 'url':
            articles[:] = [a for a in articles if ('#respond' not in a.url) and a.is_valid_url()]
        elif reason == 'body':
            articles[:] = [a for a in articles if a.is_valid_body()]
        return articles
