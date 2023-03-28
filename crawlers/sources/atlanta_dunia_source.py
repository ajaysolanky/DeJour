from newspaper.source import Source, Category
from .utils import build

class ADSource(Source):
    def set_categories(self):
        self.categories = [Category(url='https://www.atlantadunia.com/Dunia/NewsList.aspx')]

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
    
    @staticmethod
    def get_build():
        return build(ADSource, 'https://www.atlantadunia.com/Dunia/NewsList.aspx', memoize_articles=False)
