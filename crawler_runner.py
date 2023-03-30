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

google_news_prefix = "google_news"
atlanta_dunia_prefix = "atlanta_dunia"
techcrunch_prefix = "techcrunch"
vice_prefix = "vice"
sf_standard_prefix = "sf_standard"
nba_prefix = "nba"

def run_crawler(crawler_name):
    crawler_dict = {
        google_news_prefix: run_gn_crawler,
        atlanta_dunia_prefix: run_atlanta_dunia_crawler,
        techcrunch_prefix: run_techcrunch_crawler,
        vice_prefix: run_vice_crawler,
        sf_standard_prefix: run_sf_standard_crawler,
        nba_prefix: run_nba_crawler
    }
    crawler_dict[crawler_name]()

def run_gn_crawler():
    Runner(GNCrawler, google_news_prefix).run_crawler()

def run_source_crawler(source, prefix):
    Runner(lambda vdb, ndb: SourceCrawler(source, vdb, ndb), prefix).run_crawler()

def run_atlanta_dunia_crawler():
    run_source_crawler(ADSource, atlanta_dunia_prefix)

def run_techcrunch_crawler():
    run_source_crawler(TechCrunchSource, techcrunch_prefix)

def run_vice_crawler():
    run_source_crawler(ViceSource, vice_prefix)

def run_sf_standard_crawler():
    run_source_crawler(SFStandardSource, sf_standard_prefix)

def run_nba_crawler(): 
    Runner(lambda vdb, ndb: NBACrawler(NBASource, vdb, ndb), nba_prefix).run_crawler()

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) > 1:
        raise Exception('Too many args')
    run_crawler(args[0])