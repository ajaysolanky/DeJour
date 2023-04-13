from newspaper.source import Category

from .base_source import BaseSource

class BBCSource(BaseSource):
    BASE_URL = 'https://www.bbc.com'

    def set_categories(self):
        self.categories = [Category(url='https://www.bbc.com/news'),
                           Category(url='https://www.bbc.com/news/science-environment-56837908'),
                           Category(url='https://www.bbc.com/news/world'),
                           Category(url='https://www.bbc.com/news/world/us_and_canada'),
                           Category(url='https://www.bbc.com/news/uk'),
                           Category(url='https://www.bbc.com/news/business'),
                           Category(url='https://www.bbc.com/news/science_and_environment'),
                           Category(url='https://www.bbc.com/news/stories'),
                           Category(url='https://www.bbc.com/news/entertainment_and_arts'),
                           Category(url='https://www.bbc.com/news/health')]