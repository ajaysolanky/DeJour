import time
from newspaper.source import Source
from newspaper.configuration import Configuration
from newspaper.utils import extend_config
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

class BaseSource(Source):
    BASE_URL = ''
    USE_SELENIUM = False

    @classmethod
    def get_build(cls, url='', dry=False, config=None, **kwargs) -> Source:
        """Returns a constructed source object without
        downloading or parsing the articles
        """
        default_config = Configuration()
        default_config.memoize_articles = False
        config = config or default_config
        config = extend_config(config, kwargs)
        url = url or cls.BASE_URL
        s = cls(url, config=config)
        if not dry:
            s.build()
        # pdb.set_trace()
        return s

    def download_categories(self):
        if self.USE_SELENIUM:
            return self.download_categories_selenium()
        else:
            return super().download_categories()

    #TODO: bring back multithreading
    def download_categories_selenium(self):
        # requests = network.multithread_request(category_urls, self.config)
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("enable-automation")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(ChromeDriverManager().install(),options=options)
        for index, category in enumerate(self.categories):
            self.categories[index].html = self.get_html_selenium(category.url, driver)
            # req = requests[index]
        self.categories = [c for c in self.categories if c.html]

    @staticmethod
    def get_html_selenium(url, driver, sleep_time=5):
        driver.get(url)
        time.sleep(sleep_time)
        html = driver.page_source
        return html
