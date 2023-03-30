from newspaper.source import Category

from .base_source import BaseSource

class NBASource(BaseSource):
    USE_SELENIUM = True
    BASE_URL = 'https://www.nba.com/'

    def set_categories(self):
        self.categories = [Category(url='https://www.nba.com/news'),
                           Category(url='https://www.nba.com/news/category/top-stories'),
                           Category(url='https://www.nba.com/news/category/power-rankings'),
                           Category(url='https://www.nba.com/draft/2023'),
                        #    Category(url='https://www.nba.com/history')
                           ]