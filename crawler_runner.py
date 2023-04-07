import sys

from crawlers.gn_crawler import GNCrawler
from crawlers.source_crawler import SourceCrawler
from crawlers.sources.atlanta_dunia_source import ADSource
from crawlers.sources.techcrunch_source import TechCrunchSource
from crawlers.sources.vice_source import ViceSource
from crawlers.sources.sfstandard_source import SFStandardSource
from crawlers.sources.nba_source import NBASource
from crawlers.nbacrawler import NBACrawler
from publisher_enum import PublisherEnum

import time
from datetime import datetime
from langchain import OpenAI
from langchain.chains import VectorDBQAWithSourcesChain

from news_db import NewsDB
from query import ChatQuery
from vector_db import VectorDBWeaviateCURL, VectorDBWeaviatePythonClient
from publisher_enum import PublisherEnum
from crawlers.base_crawler import BaseCrawler

class CrawlerRunner(object):
    CRAWLER_SLEEP_SECONDS = 60 * 15
    def __init__(self, crawler: BaseCrawler, publisher: PublisherEnum):
        # self.vector_db = VectorDBWeaviateCURL(publisher)
        self.vector_db = VectorDBWeaviatePythonClient(publisher)
        # self.vector_db = VectorDBLocal(publisher)
        self.news_db = NewsDB(publisher)
        self.crawler = crawler(
            self.vector_db,
            self.news_db
            )

    def run_crawler(self):
        while True:
            self.crawler.full_update()
            print(f"{str(datetime.now())}\nCrawl complete. Sleeping for {self.CRAWLER_SLEEP_SECONDS} seconds. Time: {datetime.now()}")
            time.sleep(self.CRAWLER_SLEEP_SECONDS)


def run_crawler(crawler_name):
    crawler_dict = {
        PublisherEnum.ATLANTA_DUNIA : run_atlanta_dunia_crawler,
        PublisherEnum.GOOGLE_NEWS : run_gn_crawler,
        PublisherEnum.NBA : run_nba_crawler,
        PublisherEnum.SF_STANDARD : run_sf_standard_crawler,
        PublisherEnum.TECHCRUNCH : run_techcrunch_crawler,
        PublisherEnum.VICE : run_vice_crawler,
    }
    crawler_dict[PublisherEnum(crawler_name)]()

def run_gn_crawler():
    CrawlerRunner(GNCrawler, PublisherEnum.GOOGLE_NEWS).run_crawler()

def run_source_crawler(source, prefix):
    CrawlerRunner(lambda vdb, ndb: SourceCrawler(source, vdb, ndb), prefix).run_crawler()

def run_atlanta_dunia_crawler():
    run_source_crawler(ADSource, PublisherEnum.ATLANTA_DUNIA)

def run_techcrunch_crawler():
    run_source_crawler(TechCrunchSource, PublisherEnum.TECHCRUNCH)

def run_vice_crawler():
    run_source_crawler(ViceSource, PublisherEnum.VICE)

def run_sf_standard_crawler():
    run_source_crawler(SFStandardSource, PublisherEnum.SF_STANDARD)

def run_nba_crawler(): 
    CrawlerRunner(lambda vdb, ndb: NBACrawler(NBASource, vdb, ndb), PublisherEnum.NBA).run_crawler()

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) > 1:
        raise Exception('Too many args')
    run_crawler(args[0])