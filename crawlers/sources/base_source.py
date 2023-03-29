from newspaper.source import Source
from newspaper.configuration import Configuration
from newspaper.utils import extend_config
import pdb

class BaseSource(Source):
    BASE_URL = ''

    @classmethod
    def get_build(cls, url='', dry=False, config=None, **kwargs) -> Source:
        """Returns a constructed source object without
        downloading or parsing the articles
        """
        config = config or Configuration()
        config = extend_config(config, kwargs)
        url = url or cls.BASE_URL
        s = cls(url, config=config)
        if not dry:
            s.build()
        # pdb.set_trace()
        return s
