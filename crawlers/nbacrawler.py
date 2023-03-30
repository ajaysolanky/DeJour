
import pandas as pd
import requests
import json
from bs4 import BeautifulSoup as bs
from urllib.parse import urljoin
from .base_crawler import BaseCrawler
import pdb

class NBACrawler(BaseCrawler):
    crawler_prefix = "nba_"
    def __init__(self, source, vector_db, news_db):
        super().__init__(vector_db, news_db)
        self.source = source
        self.articles = {}


    def download_article(self, url):
        print (f"fetching article @ url: {url}")
        # initialize a session
        session = requests.Session()
        # set the User-agent as a regular browser
        session.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36"
        html = session.get(url).content

        # parse HTML using beautiful soup
        soup = bs(html, "html.parser")
        # get the JavaScript files
        script_files = []

        scripts =  soup.find_all("script")
        for script in scripts:
            data = json.loads(soup.find('script', type='application/ld+json').string)
            if "headline" not in data:
                raise Exception("no headline found")
            if "articleBody" not in data:
                raise Exception("no headline found")

            if "headline" in data:
                return {
                    "title": data["headline"],
                    "url": url,
                    "text": data["articleBody"],
                    "preview": None,
                    "top_image_url": data["image"],
                    "authors": data["author"]["name"],
                    "publish_date": data["datePublished"]
                }
    
    def fetch_news_df(self):
        source_build = self.source.get_build(memoize_articles=False, dry=False)
        articles = source_build.articles
        for article in articles:
            if article.url is None or article.url == "":
                print("skipping article with no url")
                continue
            if "/video" in article.url:
                continue
            try:
                article_dict = self.download_article(article.url)
                self.articles[article.url] = article_dict
            except:
                print(f"error downloading article: {article.url}")
                continue
        articles_list = list(self.articles.values())
        lightweight_articles = []
        for article in articles_list:
            if article is None:
                pdb.set_trace()
                print("article is none. this is unexpected")
            lightweight_articles.append({
                "url": article["url"],
                "title": article["title"]
            })
        return pd.DataFrame(lightweight_articles)

    def augment_data(self, url):
        if url in self.articles:
            article = self.articles[url]
            text = None
            if "text" in article:
                text = article["text"]
            top_image_url = None
            if "top_image_url" in article:
                top_image_url = article["top_image_url"]
            authors = ""
            if "authors" in article:
                authors = article["authors"]
            publish_date = None
            if "publish_date" in article:
                publish_date = article["publish_date"]
            return pd.Series({
                "text": text,
                "preview": None,
                "top_image_url": top_image_url,
                "authors": authors,
                "publish_date": publish_date
            })
        else:
            print(f"article not found in articles dict: {url}")
                