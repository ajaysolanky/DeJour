import sys

from main import Runner
from crawlers.gn_crawler import GNCrawler
from crawlers.source_crawler import SourceCrawler
from crawlers.sources.atlanta_dunia_source import ADSource
from crawlers.sources.techcrunch_source import TechCrunchSource
from crawlers.sources.vice_source import ViceSource
from crawlers.sources.sfstandard_source import SFStandardSource
from crawlers.sources.nba_source import NBASource
from crawlers.nbacrawler import NBACrawler
from publisher_enum import PublisherEnum

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
    Runner(GNCrawler, PublisherEnum.GOOGLE_NEWS).run_crawler()

def run_source_crawler(source, prefix):
    Runner(lambda vdb, ndb: SourceCrawler(source, vdb, ndb), prefix).run_crawler()

def run_atlanta_dunia_crawler():
    run_source_crawler(ADSource, PublisherEnum.ATLANTA_DUNIA)

def run_techcrunch_crawler():
    run_source_crawler(TechCrunchSource, PublisherEnum.TECHCRUNCH)

def run_vice_crawler():
    run_source_crawler(ViceSource, PublisherEnum.VICE)

def run_sf_standard_crawler():
    run_source_crawler(SFStandardSource, PublisherEnum.SF_STANDARD)

def run_nba_crawler(): 
    Runner(lambda vdb, ndb: NBACrawler(NBASource, vdb, ndb), PublisherEnum.NBA).run_crawler()

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) > 1:
        raise Exception('Too many args')
    run_crawler(args[0])