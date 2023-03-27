from newspaper import Source
from newspaper.configuration import Configuration
from newspaper.utils import extend_config

def build(custom_source=Source, url='', dry=False, config=None, **kwargs) -> Source:
    """Returns a constructed source object without
    downloading or parsing the articles
    """
    config = config or Configuration()
    config = extend_config(config, kwargs)
    url = url or ''
    s = custom_source(url, config=config)
    if not dry:
        s.build()
    return s