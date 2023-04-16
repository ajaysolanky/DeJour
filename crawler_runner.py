import sys
import optparse
import json
import logging
from crawlers.gn_crawler import GNCrawler
from crawlers.source_crawler import SourceCrawler
from crawlers.sources.atlanta_dunia_source import ADSource
from crawlers.sources.techcrunch_source import TechCrunchSource
from crawlers.sources.vice_source import ViceSource
from crawlers.sources.sfstandard_source import SFStandardSource
from crawlers.sources.nba_source import NBASource
from crawlers.sources.bbc_india_source import BBCIndiaSource
from crawlers.nbacrawler import NBACrawler
from publisher_enum import PublisherEnum
from weaviate_utils.weaviate_client import WeaviatePythonClient

from news_db import NewsDBLocal, NewsDBFirestoreDatabase
from vector_db import VectorDBWeaviateCURL, VectorDBWeaviatePythonClient, VectorDBLocal
from publisher_enum import PublisherEnum

logging.getLogger().setLevel(logging.INFO)

def lambda_handler(event, context):
    logging.info("EVENT: %s ; CONTEXT: %s" % (event, context))
    body = event["body"]
    publisher_str = body['publisher']
    crawler = build_crawler(publisher_str, use_local_vector_db=False, use_local_news_db=False)
    crawler.fetch_and_upload_news()
    logging.info("FINISHED fetch_and_upload_news")
    return {
        "status": "ok"
    }

def build_crawler(publisher_str: str, use_local_vector_db: bool, use_local_news_db: bool):
    crawler_dict = {
        PublisherEnum.ATLANTA_DUNIA : get_source_crawler(ADSource),
        PublisherEnum.BBC_INDIA : get_source_crawler(BBCIndiaSource),
        PublisherEnum.GOOGLE_NEWS : GNCrawler,
        PublisherEnum.NBA : lambda vdb, ndb: NBACrawler(NBASource, vdb, ndb),
        PublisherEnum.SF_STANDARD : get_source_crawler(SFStandardSource),
        PublisherEnum.TECHCRUNCH : get_source_crawler(TechCrunchSource),
        PublisherEnum.VICE : get_source_crawler(ViceSource),
    }

    publisher_enum = PublisherEnum(publisher_str)
    if use_local_vector_db:
        vector_db_class = VectorDBLocal
    else:
        weaviate_client = WeaviatePythonClient(publisher_enum)
        weaviate_client.try_create_weaviate_class()
        vector_db_class = VectorDBWeaviatePythonClient

    vector_db = vector_db_class(publisher_enum)

    if use_local_news_db:
        news_db_class = NewsDBLocal
    else:
        news_db_class = NewsDBFirestoreDatabase

    news_db = news_db_class(publisher_enum)

    return crawler_dict[publisher_enum](vector_db, news_db)

def get_source_crawler(source):
    return lambda ndb, vdb: SourceCrawler(source, ndb, vdb)
