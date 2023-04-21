from newspaper.source import Category

from .custom_source import CustomSource

class SequoiaSource(CustomSource):
    BASE_URL = 'https://www.sequoiacap.com/stories/'

    def set_categories(self):
        self.categories = [Category(url='https://www.sequoiacap.com/stories/?_story-category=spotlight'),
                           Category(url='https://www.sequoiacap.com/stories/'),
                           Category(url='https://www.sequoiacap.com/stories/?_story-category=perspective'),
                           Category(url='https://www.sequoiacap.com/stories/?_story-category=news')]