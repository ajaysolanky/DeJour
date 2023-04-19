from newspaper.source import Category

from .custom_source import CustomSource

class ADSource(CustomSource):
    BASE_URL = 'https://www.atlantadunia.com/Dunia/NewsList.aspx'

    def set_categories(self):
        self.categories = [Category(url='https://www.atlantadunia.com/Dunia/NewsList.aspx')]

    def purge_articles(self, reason, articles):
        if reason == 'url':
            articles[:] = [a for a in articles if 'Newsdetail' in a.url]
        elif reason == 'body':
            articles[:] = [a for a in articles if a.is_valid_body()]
        return articles
