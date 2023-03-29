import requests
# from ghost import Ghost
import newspaper
import pandas as pd
import cfscrape
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
    
class NYTCrawler:
    CHUNK_SIZE_TOKENS = 300
    CHUNK_OVERLAP_TOKENS = int(CHUNK_SIZE_TOKENS * .2)
    SEPARATOR = '\n'
    MIN_SPLIT_WORDS = 5

    def __init__(self, vector_db, news_db):
        self.get_num_tokens = TokenCountCalculator().get_num_tokens
        self.vector_db = vector_db
        self.news_db = news_db
        self.api_key = os.getenv('NYT_API_KEY', 'not the token')

    def get_article_results(self, date):
        results = []
        for i in range(100):
            params = {"begin_date": date, "end_date": date, "api-key": self.api_key, "page": i}
            base_url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
            response = requests.get(base_url, params=params)
            json_response = response.json()
            if 'status' not in json_response:
                print("No status in response.")
                return results
            status = json_response['status']                
            if status != 'OK':
                print(f"Invalid status. Status is {status} ")
                return results
            articles = json_response['response']['docs']
            results.extend(articles)
            print(f"processed page: {i}")
            hits_count = json_response['response']['meta']['hits']
            if hits_count < 10:
                return results
        return results
    
    # def fetch_article_obj_from_url(self, url):
    #     initial_response_html = session.get("https://myaccount.nytimes.com/auth/enter-email?response_type=cookie&client_id=lgcl&redirect_uri=https%3A%2F%2Fwww.nytimes.com")
    #     soup = BeautifulSoup(initial_response_html.text, "html.parser")
    #     data_auth_options = soup.select_one('.full-page')['data-auth-options']
    #     json_data_auth_options = json.loads(data_auth_options)
    #     token = json_data_auth_options['authToken']
    #     print(token)
    #     payload = {
    #         "userid": "aalhad.patankar@gmail.com",
    #         "password": "37dtu437",
    #         "token": token,
    #         "is_continue": False
    #     }

    #     options = webdriver.ChromeOptions() 
    #     options.headless = True
    #     options.page_load_strategy = 'none' 
    #     chrome_path = ChromeDriverManager().install() 
    #     chrome_service = Service(chrome_path) 
    #     driver = Chrome(options=options, service=chrome_service) 
    #     driver.implicitly_wait(5)
    #     url = "https://www.instacart.com/store/sprouts/collections/bread?guest=True" 
    #     driver.get(url)
    #     time.sleep(10)

    def fetch_new_news_df(self, date):
        articles = self.get_article_results(date) 

        print(len(articles))
        # return
        def convert_to_format(nyt_result):
            try:
                backup_text = nyt_result['abstract'] + nyt_result['lead_paragraph']
                url = nyt_result['web_url']
                title = nyt_result['headline']['main']
                published_date_iso = nyt_result['pub_date']
                published_date = dateutil.parser.isoparse(published_date_iso)
                published_date_string = published_date.strftime("%B %d, %Y at %I:%M %p")
            except Exception as e: 
                print(f"Error in article format converting to format. Error: {e}")

            print(f"Attempting to download full article from url: {url}")
            try:
                # Filter out interactive articles
                if "com/interactive" in url:
                    print(f"Encountered interactive article {url}. Using abstract")
                    text = backup_text
                else:
                    text_nodes = self.get_article_from_url(url)
                    text = ''
                    for node in text_nodes:
                        text += node['text']
                    if len(text) < 100:
                        text = backup_text
            except Exception as e:
                print(f"Failed to extract full article, falling back to abstract. Error: {e}")
                text = backup_text
            date_published_string = "This article was published on: " + published_date_string
            text_with_context = date_published_string + text
            return {
                "text": text_with_context,
                "url": url,
                "title": title,
                "published_date": published_date_iso
            }
        
        mapped_articles = list(map(convert_to_format, articles))
        # print(mapped_articles)
    
        # filter out already processed articles
        print(f"Found mapped articles. Count: {len(mapped_articles)}")
        news_df = pd.DataFrame(mapped_articles)

        print("Getting matched articles")
        matched_artcles = self.news_db.get_matched_articles(news_df.url)

        new_news_df = news_df[news_df['url'].isin(matched_artcles) == False]

        print(f"{len(matched_artcles)} articles already exist in the db. {new_news_df.shape[0]} articles remain.")

        return new_news_df
        # self.add_new_news_to_dbs(news_df)
        # print(_first_article_url)
        # obj = self.get_article_obj_from_url(_first_article_url)
        # self.add_new_news_to_dbs([obj])
        # self.create_session()

    def add_new_news_to_dbs(self, new_news_df):
        if new_news_df.shape[0] == 0:
            return
        
        print("Adding new news to dbs")
        text_splitter = HardTokenSpacyTextSplitter(
            self.get_num_tokens,
            chunk_size=self.CHUNK_SIZE_TOKENS,
            chunk_overlap=self.CHUNK_OVERLAP_TOKENS,
            separator=self.SEPARATOR
            )
        docs = []
        metadatas = []
        orig_idces = []
       
        """
        Takes a new news df and returns
        
        """
        if new_news_df.shape[0] == 0:
            return
        text_splitter = HardTokenSpacyTextSplitter(
            self.get_num_tokens,
            chunk_size=self.CHUNK_SIZE_TOKENS,
            chunk_overlap=self.CHUNK_OVERLAP_TOKENS,
            separator=self.SEPARATOR
            )
        docs = []
        metadatas = []
        orig_idces = []

        for i, r in new_news_df.iterrows():
            if len(r.text) > 1000000:
                print(f"Skipping article with text length {len(r.text)}. url: {r.url}")
                continue
            splits = text_splitter.split_text(r.text)
            splits = [s for s in splits if len(s.split(' ')) > self.MIN_SPLIT_WORDS]
            docs.extend(splits)
            metadatas.extend([{"source": r.url}] * len(splits))
            orig_idces.extend([i] * len(splits))
        
        print("adding texts to VectorDB")
        new_ids = self.vector_db.add_texts(docs, metadatas)
        print("finished adding texts to VectorDB")

        idc_id_map = defaultdict(list)
        for new_id, orig_idx in zip(new_ids, orig_idces):
            idc_id_map[orig_idx].append(new_id)

        idc_id_map_stred = {k: ','.join(v) for k,v in idc_id_map.items()}
        
        # so it doesn't edit the input df
        copy_df = new_news_df.copy()
        copy_df['embedding_ids'] = pd.Series(idc_id_map_stred)

        print("adding news to news db")
        self.news_db.add_news_df(copy_df)
        print("finished adding news to news db")
        
    def create_session(self):
        session = requests.session()
        initial_response_html = session.get("https://myaccount.nytimes.com/auth/enter-email?response_type=cookie&client_id=lgcl&redirect_uri=https%3A%2F%2Fwww.nytimes.com")
        soup = BeautifulSoup(initial_response_html.text, "html.parser")
        data_auth_options = soup.select_one('.full-page')['data-auth-options']
        json_data_auth_options = json.loads(data_auth_options)
        token = json_data_auth_options['authToken']
        payload = {
            # "userid": "aalhad.patankar@gmail.com",
            "password": "37dtu437",
            "token": token,
            "is_continue": False
        }
        # print(token)
        # auth_token = soup.select('full-page')[0].get_text()
        # print(auth_token)
        # print(soup[len(soup) - 1])

        # for a in soup:
        #     print(a)
        #     print('BREAKBREAKBREAK')
        scraper = cfscrape.create_scraper(sess=session)
        print(scraper.post("https://myaccount.nytimes.com/auth/login/?URI=https://www.nytimes.com/2023/03/07/us/politics/nord-stream-pipeline-sabotage-ukraine.html", data=payload).content)

        # response = session.post('https://www.nytimes.com/interactive/2023/03/05/nyregion/election-asians-voting-republicans-nyc.html', data=payload)
        # print(response)
    
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
        
        # print(article["title"] \
        #     + "\n\t\t" + article["published_date"] \
        #     + "\n\n"\
        #     + "\n" + article["text"]\
        #     + "\n\n")
        # options = webdriver.ChromeOptions() 
        # options.headless = True
        # options.page_load_strategy = 'none' 
        # chrome_path = ChromeDriverManager().install() 
        # chrome_service = Service(chrome_path) 
        # driver = Chrome(options=options, service=chrome_service) 
        # driver.implicitly_wait(5)
        # url = "https://www.nytimes.com/2023/03/07/us/politics/nord-stream-pipeline-sabotage-ukraine.html"
        # driver.get(url)
        # time.sleep(3)

        # page_source = driver.page_source
        # text = fulltext(page_source)
        # print(text)
        # with open('sample_article.txt', 'w') as file:
        #     file.write(page_source)

    def full_update(self, date):
        # self.create_session_with_js("https://www.nytimes.com/2023/03/07/us/politics/nord-stream-pipeline-sabotage-ukraine.html")
        # self.create_session()
        news_df = self.fetch_new_news_df(date)
        self.add_new_news_to_dbs(news_df)