
import optparse
import logging
from weaviate_utils.weaviate_client import WeaviatePythonClient
from weaviate_utils.weaviate_class import WeaviateClassArticleSnippet

logging.getLogger().setLevel(logging.INFO)
if __name__ == '__main__':
    p = optparse.OptionParser()
    p.add_option('--publisher')
    p.add_option('--action')

    options, arguments = p.parse_args()
    publisher_str = options.publisher
    action = options.action
    if not publisher_str:
        raise Exception('must specify a publisher')
    if not options.action:
        raise Exception('must specify an action')
    
    if action == "delete":
        weaviate_client = WeaviatePythonClient(weaviate_class=WeaviateClassArticleSnippet(publisher_str))
        weaviate_client.delete_class()
    else:
        raise Exception('unsupported action')


    