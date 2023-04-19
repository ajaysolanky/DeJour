import pytz
import logging
import requests
# from ghost import Ghost
import newspaper
import pandas as pd
import datetime
import os
import json
import time
from typing import List
from bs4 import BeautifulSoup
from text_splitter import HardTokenSpacyTextSplitter
from utils import TokenCountCalculator
from collections import defaultdict
import pandas as pd 
from selenium import webdriver 
from selenium.webdriver import Chrome 
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.common.by import By 
from webdriver_manager.chrome import ChromeDriverManager
from lxml import html
from newspaper import fulltext
import dateutil.parser
from newspaper import Article

from .base_crawler import BaseCrawler
from utils import get_isoformat_and_add_tz_if_not_there

try:
    from typing import TypedDict
except:
    from typing_extensions import TypedDict

class NYTArticle(TypedDict):
    abstract: str
    web_url: str
    lead_paragraph: str

class NYTArticleQueryResponse(TypedDict):
    abstract: List[NYTArticle]
    
class NYTAPIResponse(TypedDict):
    docs: NYTArticleQueryResponse
    
class NYTCrawler(BaseCrawler):
    def __init__(self, vector_db, news_db):
        super().__init__(vector_db, news_db)
        self.api_key = os.getenv('NYT_API_KEY', 'not the token')

    def get_article_results(self):
        cur_dt = pytz.utc.localize(datetime.datetime.utcnow()).astimezone(pytz.timezone('America/New_York'))
        cur_date_str = cur_dt.strftime('%Y%m%d')
        yday_date_str = (cur_dt - datetime.timedelta(days=1)).strftime('%Y%m%d')

        results = []
        for i in range(100):
            params = {"begin_date": yday_date_str, "end_date": cur_date_str, "api-key": self.api_key, "page": i}
            base_url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
            response = requests.get(base_url, params=params)
            json_response = response.json()
            if 'status' not in json_response:
                logging.info("No status in response.")
                return results
            status = json_response['status']                
            if status != 'OK':
                logging.info(f"Invalid status. Status is {status} ")
                return results
            articles = json_response['response']['docs']
            results.extend(articles)
            logging.info(f"processed page: {i}")
            hits_count = json_response['response']['meta']['hits']
            if hits_count < 10:
                return results
        return results

    def fetch_news_df(self):
        articles = self.get_article_results() 

        logging.info(len(articles))
        def convert_to_format(nyt_result):
            try:
                backup_text = nyt_result['abstract'] + nyt_result['lead_paragraph']
                url = nyt_result['web_url']
                title = nyt_result['headline']['main']
                published_date_iso = nyt_result['pub_date']
            except Exception as e: 
                logging.info(f"Error in article format converting to format. Error: {e}")

            logging.info(f"Attempting to download full article from url: {url}")
            try:
                # Filter out interactive articles
                if "com/interactive" in url:
                    logging.info(f"Encountered interactive article {url}. Using abstract")
                    text = backup_text
                else:
                    text_nodes = self.get_article_from_url(url)
                    text = ''
                    for node in text_nodes:
                        text += node['text']
                    if len(text) < 100:
                        text = backup_text
            except Exception as e:
                logging.info(f"Failed to extract full article, falling back to abstract. Error: {e}")
                text = backup_text
            return {
                "text": text,
                "url": url,
                "title": title,
                "published_date": published_date_iso
            }
        
        mapped_articles = list(map(convert_to_format, articles))
    
        # filter out already processed articles
        logging.info(f"Found mapped articles. Count: {len(mapped_articles)}")
        news_df = pd.DataFrame(mapped_articles)

        return news_df

    def get_article_from_url(self, url):
        article = newspaper.Article(url=url, language='en')
        article.download()
        article.parse()

        formatted_article ={
            "title": str(article.title),
            "text": str(article.text),
            "authors": article.authors,
            "published_date": str(article.publish_date),
            "top_image": str(article.top_image),
            "videos": article.movies,
            "keywords": article.keywords,
            "summary": str(article.summary)
        }

        all_nodes = article.get_all_nodes()
        return all_nodes

    # def augment_data(self, url):
    #     print (f"fetching article @ url: {url}")
    #     article = Article(url=url)
    #     try:
    #         article.download()
    #         article.parse()
    #     except:
    #         article = None
    #     if article is None:
    #         article = object()
    #     return pd.Series({
    #         "text": getattr(article, "text", None),
    #         "preview": None,
    #         "top_image_url": getattr(article, "top_image", None),
    #         "authors": ','.join(getattr(article, "authors", [])),
    #         "publish_timestamp": get_isoformat_and_add_tz_if_not_there(getattr(article, "publish_date", None)),
    #         "fetch_timestamp": pytz.utc.localize(datetime.utcnow()).isoformat()
    #     })
