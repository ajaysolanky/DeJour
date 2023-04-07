import sys
import optparse

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

from news_db import NewsDB
from query import ChatQuery
from vector_db import VectorDBWeaviateCURL, VectorDBWeaviatePythonClient, VectorDBLocal
from publisher_enum import PublisherEnum
from crawlers.base_crawler import BaseCrawler

def run_crawler(publisher, local_vector_db):
    crawler_dict = {
        PublisherEnum.ATLANTA_DUNIA : get_source_crawler(ADSource),
        PublisherEnum.GOOGLE_NEWS : GNCrawler,
        PublisherEnum.NBA : lambda vdb, ndb: NBACrawler(NBASource, vdb, ndb),
        PublisherEnum.SF_STANDARD : get_source_crawler(SFStandardSource),
        PublisherEnum.TECHCRUNCH : get_source_crawler(TechCrunchSource),
        PublisherEnum.VICE : get_source_crawler(ViceSource),
    }

    publisher_enum = PublisherEnum(publisher)

    if local_vector_db:
        vector_db_class = VectorDBLocal
    else:
        vector_db_class = VectorDBWeaviatePythonClient

    vector_db = vector_db_class(publisher_enum)
    news_db = NewsDB(publisher_enum)

    crawler_dict[publisher_enum](vector_db, news_db).run_crawler()

def get_source_crawler(source):
    return lambda ndb, vdb: SourceCrawler(source, ndb, vdb)

if __name__ == '__main__':
    p = optparse.OptionParser()
    p.add_option('--use_local_vector_db')
    p.add_option('--publisher')
    options, arguments = p.parse_args()

    options = options.__dict__

    publisher = options.get('publisher', 'false')
    if not publisher:
        raise Exception('must specify a publisher')

    use_local_vector_db_flag = options.get('use_local_vector_db', 'false')
    if use_local_vector_db_flag == 'true':
        local_vector_db = True
    elif use_local_vector_db_flag == 'false':
        local_vector_db = False
    else:
        raise Exception('invalid flag option for use_local_vector_db')

    run_crawler(publisher, local_vector_db)