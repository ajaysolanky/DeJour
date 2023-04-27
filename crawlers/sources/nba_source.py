from newspaper.source import Category

from .custom_source import CustomSource

class NBASource(CustomSource):
    USE_PYPPETEER = True
    BASE_URL = 'https://www.nba.com/'

    def set_categories(self):
        self.categories = [
            # Category(url='https://www.nba.com/news'),
                           Category(url='https://www.nba.com/news/category/top-stories'),
                        #    Category(url='https://www.nba.com/news/category/power-rankings'),
                        #    Category(url='https://www.nba.com/draft/2023'),
                        #    Category(url='https://www.nba.com/history')
                           ]
        
    def purge_articles(self, reason, articles):
        if reason == 'url':
            articles[:] = [a for a in articles if ('/news/' in a.url and '/category' not in a.url)]
        elif reason == 'body':
            articles[:] = [a for a in articles if a.is_valid_body()]
        return articles