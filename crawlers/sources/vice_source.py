from newspaper.source import Category

from .base_source import BaseSource

class ViceSource(BaseSource):
    BASE_URL = 'https://www.vice.com/'

    def set_categories(self):
        self.categories = [Category(url='https://www.vice.com/en/section/news')]

    def purge_articles(self, reason, articles):
        """Delete rejected articles, if there is an articles param,
        purge from there, otherwise purge from source instance.

        Reference this StackOverflow post for some of the wonky
        syntax below:
        http://stackoverflow.com/questions/1207406/remove-items-from-a-
        list-while-iterating-in-python
        """
        if reason == 'url':
            articles[:] = [a for a in articles if 'Newsdetail' in a.url]
        elif reason == 'body':
            articles[:] = [a for a in articles if a.is_valid_body()]
        return articles
