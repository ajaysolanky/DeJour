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
from crawlers.sources.sequoia_source import SequoiaSource
from crawlers.sources.nba_source import NBASource
from crawlers.sources.bbc_india_source import BBCIndiaSource
from crawlers.sources.horticult import HorticultSource
from crawlers.nbacrawler import NBACrawler
# from crawlers.nytcrawler import NYTCrawler
from publisher_enum import PublisherEnum
from news_db import NewsDBLocal, NewsDBFirestoreDatabase
from vector_db import VectorDBWeaviateCURL, VectorDBWeaviatePythonClient, VectorDBLocal
from publisher_enum import PublisherEnum
from weaviate_utils.weaviate_class import WeaviateClassArticleSnippet

logging.getLogger().setLevel(logging.INFO)

def lambda_handler(event, context):
    logging.info("EVENT: %s ; CONTEXT: %s" % (event, context))
    body = event["body"]
    publisher_str = body['publisher']
    add_summaries = body.get("add_summaries", False)
    delete_old = body.get("delete_old", False)
    use_local_vector_db = body.get("use_local_vector_db", False)
    use_local_news_db = body.get("use_local_news_db", False)
    crawler = build_crawler(publisher_str, add_summaries, delete_old, use_local_vector_db, use_local_news_db)
    crawler.fetch_and_upload_news()
    logging.info("FINISHED fetch_and_upload_news")
    return {
        "status": "ok"
    }

def build_crawler(publisher_str: str, add_summaries: bool, delete_old: bool, use_local_vector_db: bool, use_local_news_db: bool):
    crawler_dict = {
        PublisherEnum.ATLANTA_DUNIA : get_source_crawler(ADSource),
        PublisherEnum.BBC_INDIA : get_source_crawler(BBCIndiaSource),
        PublisherEnum.GOOGLE_NEWS : GNCrawler,
        PublisherEnum.HORTICULT : get_source_crawler(HorticultSource),
        PublisherEnum.NBA : get_source_crawler(NBASource),
        # PublisherEnum.NY_TIMES: NYTCrawler,
        PublisherEnum.SF_STANDARD : get_source_crawler(SFStandardSource),
        PublisherEnum.TECHCRUNCH : get_source_crawler(TechCrunchSource),
        PublisherEnum.VICE : get_source_crawler(ViceSource),
        PublisherEnum.SEQUOIA: get_source_crawler(SequoiaSource)
    }

    publisher_enum = PublisherEnum(publisher_str)
    if use_local_vector_db:
        args = {'publisher_name': publisher_enum.value}
        vector_db_class = VectorDBLocal
    else:
        args = {"weaviate_class": WeaviateClassArticleSnippet(publisher_enum.value)}
        vector_db_class = VectorDBWeaviatePythonClient

    vector_db = vector_db_class(args)

    if use_local_news_db:
        news_db_class = NewsDBLocal
    else:
        news_db_class = NewsDBFirestoreDatabase

    news_db = news_db_class(publisher_enum)

    return crawler_dict[publisher_enum](vector_db, news_db, add_summaries, delete_old)

def get_source_crawler(source):
    return lambda ndb, vdb, add_summaries, delete_old: SourceCrawler(source, ndb, vdb, add_summaries, delete_old)

if __name__ == '__main__':
    p = optparse.OptionParser()
    p.add_option('--publisher')
    p.add_option('--add_summaries', action='store_true')
    p.add_option('--delete_old', action='store_true')
    p.add_option('--use_local_vector_db', action='store_true')
    p.add_option('--use_local_news_db', action='store_true')
    options, arguments = p.parse_args()

    publisher_str = options.publisher
    if not publisher_str:
        raise Exception('must specify a publisher')
    
    event = {
        "body": {
            "publisher": publisher_str,
            "add_summaries": options.add_summaries,
            "delete_old": options.delete_old,
            "use_local_vector_db": options.use_local_vector_db,
            "use_local_news_db": options.use_local_news_db
        }
    }

    lambda_handler(event, {})
