from .custom_source import CustomSource

class NYTSource(CustomSource):
    USE_PYPPETEER = True
    BASE_URL = 'https://www.nyt.com'