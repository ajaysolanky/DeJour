from main import Runner
from crawlers.source_crawler import SourceCrawler
from crawlers.sources.atlanta_dunia_source import ADSource

import pdb; pdb.set_trace()
Runner(lambda vdb, ndb: SourceCrawler(ADSource, vdb, ndb)).run_crawler()