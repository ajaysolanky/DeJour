import logging
import asyncio
from pyppeteer import launch
from newspaper.source import Source
from newspaper.utils import extend_config
from newspaper.configuration import Configuration

class BaseSource(Source):
    BASE_URL = ''
    USE_PYPPETEER = False

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
        return s

    def download_categories(self):
        if self.USE_PYPPETEER:
            self.download_categories_pyppeteer()
        else:
            return super().download_categories()

    def download_categories_pyppeteer(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.download_categories_async())

    async def download_categories_async(self):
        browser = await launch(
            headless=True,
            dumpio=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1920x1080',
                '--disable-software-rasterizer',
                '--disable-features=VizDisplayCompositor',
                '--disable-gl-drawing-for-tests',
                '--disable-extensions',
                '--disable-infobars',
            ],
        )
        for index, category in enumerate(self.categories):
            self.categories[index].html = await self.get_html_pyppeteer(category.url, browser)
        self.categories = [c for c in self.categories if c.html]
        await browser.close()

    async def get_html_pyppeteer(self, url, browser, sleep_time=5):
        page = await browser.newPage()
        await page.goto(url)
        await asyncio.sleep(sleep_time)
        html = await page.content()
        await page.close()
        return html
