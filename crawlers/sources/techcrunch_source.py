from newspaper.source import Category

from .custom_source import CustomSource

class TechCrunchSource(CustomSource):
    BASE_URL = 'https://techcrunch.com'

    def set_categories(self):
        self.categories = [Category(url='https://techcrunch.com/category/startups'),
                           Category(url='https://techcrunch.com/category/venture'),
                           Category(url='https://techcrunch.com/category/security'),
                           Category(url='https://techcrunch.com/category/artificial-intelligence'),
                           Category(url='https://techcrunch.com/category/cryptocurrency'),
                           Category(url='https://techcrunch.com/category/apps'),
                           Category(url='https://techcrunch.com/events')]
