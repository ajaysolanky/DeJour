
from newspaper.source import Category

from .custom_source import CustomSource

class SFStandardSource(CustomSource):
    BASE_URL = 'https://sfstandard.com/'

    def set_categories(self):
        self.categories = [Category(url='https://sfstandard.com/category/politics'),
                           Category(url='https://sfstandard.com/category/education'),
                           Category(url='https://sfstandard.com/category/criminal-justice'),
                           Category(url='https://sfstandard.com/category/business'),
                           Category(url='https://sfstandard.com/category/housing-development'),
                           Category(url='https://sfstandard.com/category/transportation'),
                           Category(url='https://sfstandard.com/category/public-health'),
                           Category(url='https://sfstandard.com/category/community'),
                           Category(url='https://sfstandard.com/category/arts-culture'),
                           Category(url='https://sfstandard.com/category/sports')]
    