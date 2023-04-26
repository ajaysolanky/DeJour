import pytz
import copy
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
from newspaper.cleaners import DocumentCleaner
from newspaper.videos.extractors import VideoExtractor
from newspaper.outputformatters import OutputFormatter

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
    def __init__(self, vector_db, news_db, add_summaries):
        super().__init__(vector_db, news_db, add_summaries)
        self.api_key = os.getenv('NYT_API_KEY', 'not the token')
        self.article_bodies = {}

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

    def augment_data(self, url):
            print (f"fetching article @ url: {url}")
            article = Article(url=url)
            try:
                article.download()
                article.parse()
            except:
                article = None
            if article is None:
                article = object()
            date = getattr(article, "publish_date", None)
            print(f"Publish date: {date}")
            return pd.Series({
                "text": getattr(article, "text", None),
                "preview": None,
                "top_image_url": getattr(article, "top_image", None),
                "authors": ','.join(getattr(article, "authors", [])),
                "publish_timestamp": get_isoformat_and_add_tz_if_not_there(date),
                "fetch_timestamp": pytz.utc.localize(datetime.utcnow()).isoformat()
            })
    
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
                # "text": text,
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
        article = NYTArticle(url=url, language='en')
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

        return formatted_article

class NYTArticle(Article):
    def parse(self):
        self.throw_if_not_downloaded_verbose()

        self.doc = self.config.get_parser().fromstring(self.html)
        self.clean_doc = copy.deepcopy(self.doc)

        if self.doc is None:
            # `parse` call failed, return nothing
            return

        # TODO: Fix this, sync in our fix_url() method
        parse_candidate = self.get_parse_candidate()
        self.link_hash = parse_candidate.link_hash  # MD5

        document_cleaner = DocumentCleaner(self.config)
        output_formatter = OutputFormatter(self.config)

        title = self.extractor.get_title(self.clean_doc)
        self.set_title(title)

        authors = self.extractor.get_authors(self.clean_doc)
        self.set_authors(authors)

        meta_lang = self.extractor.get_meta_lang(self.clean_doc)
        self.set_meta_language(meta_lang)

        if self.config.use_meta_language:
            self.extractor.update_language(self.meta_lang)
            output_formatter.update_language(self.meta_lang)

        meta_favicon = self.extractor.get_favicon(self.clean_doc)
        self.set_meta_favicon(meta_favicon)

        meta_description = \
            self.extractor.get_meta_description(self.clean_doc)
        self.set_meta_description(meta_description)

        canonical_link = self.extractor.get_canonical_link(
            self.url, self.clean_doc)
        self.set_canonical_link(canonical_link)

        tags = self.extractor.extract_tags(self.clean_doc)
        self.set_tags(tags)

        meta_keywords = self.extractor.get_meta_keywords(
            self.clean_doc)
        self.set_meta_keywords(meta_keywords)

        meta_data = self.extractor.get_meta_data(self.clean_doc)
        self.set_meta_data(meta_data)

        self.publish_date = self.extractor.get_publishing_date(
            self.url,
            self.clean_doc)

        # Before any computations on the body, clean DOM object
        self.doc = document_cleaner.clean(self.doc)
        
        from lxml.cssselect import CSSSelector
        selector = CSSSelector('div.StoryBodyCompanionColumn')
        top_nodes = selector(self.doc)
        # self.top_node = self.extractor.calculate_best_node(self.doc)
        self.top_node = top_nodes[0]
        if self.top_node is not None:
            video_extractor = VideoExtractor(self.config, self.top_node)
            self.set_movies(video_extractor.get_videos())

            top_nodes = [self.extractor.post_cleanup(tn) for tn in top_nodes]
            self.top_node = top_nodes[0]
            # self.top_node = self.extractor.post_cleanup(self.top_node)
            self.clean_top_node = copy.deepcopy(self.top_node)

            full_text, full_article_html = "", ""
            for node in top_nodes:
                text, article_html = output_formatter.get_formatted(
                    node)
                full_text += text + "\n"
                full_article_html += article_html
            if len(full_text) <= 32500:
                self.set_article_html(full_article_html)
                self.set_text(full_text)

        self.fetch_images()

        self.is_parsed = True
        self.release_resources()