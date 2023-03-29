import sys
from main import Runner
from crawlers.gn_crawler import GNCrawler
from crawlers.source_crawler import SourceCrawler
from crawlers.sources.atlanta_dunia_source import ADSource

google_news_prefix = "google_news"
atlanta_dunia_prefix = "atlanta_dunia"

def run_crawler(crawler_name):
    crawler_dict = {
        google_news_prefix: run_gn_crawler,
        atlanta_dunia_prefix: run_atlanta_dunia_crawler
    }
    crawler_dict[crawler_name]()

def run_gn_crawler():
    Runner(GNCrawler, google_news_prefix).run_crawler()

def run_source_crawler(source):
    Runner(lambda vdb, ndb: SourceCrawler(source, vdb, ndb), atlanta_dunia_prefix).run_crawler()

def run_atlanta_dunia_crawler():
    run_source_crawler(ADSource)

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) > 1:
        raise Exception('Too many args')
    run_crawler(args[0])