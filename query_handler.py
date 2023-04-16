import json
import logging
from query import ChatQuery
from vector_db import VectorDBWeaviateCURL, VectorDBWeaviatePythonClient, VectorDBLocal

from publisher_enum import PublisherEnum

logging.getLogger().setLevel(logging.INFO)

def lambda_handler(event, context):
    logging.info("EVENT: %s ; CONTEXT: %s" % (event, context))
    body = event["body"]
    if isinstance(body, str):
        body = json.loads(body)
    
    chat_history = body['chat_history']
    query = body['query']
    # publisher = body['publisher']
    url = body['url']
    inline = body.get('inline')
    followups = body.get('followups')
    try:
        publisher = get_publisher_for_url(url)
        qh = QueryHandler(publisher, inline, followups)
        chat_result = qh.get_chat_result(chat_history, query)
        return chat_result
    except Exception as e:
        print(f"Get publisher failed with error: {e}")
        print(f"Invalid url: {url}")
        return format_error_response_as_answer("DeJour is not supported on this website")
    
def format_error_response_as_answer(error):
    return {
        "answer": error,
        "sources": []
    }

def get_publisher_for_url(url):
    if "atlantadunia" in url:
        return PublisherEnum.ATLANTA_DUNIA
    elif "bbc" in url:
        return PublisherEnum.BBC_INDIA
    elif "google" in url:
        return PublisherEnum.GOOGLE_NEWS
    elif "nba" in url:
        return PublisherEnum.NBA
    elif "sfstandard" in url:
        return PublisherEnum.SF_STANDARD
    elif "techcrunch" in url:
        return PublisherEnum.TECHCRUNCH
    elif "vice" in url:
        return PublisherEnum.VICE
    else:
        raise Exception("Invalid url")


class QueryHandler(object):
    def __init__(self, publisher: PublisherEnum, inline: bool, followups: bool):
        self.vector_db = VectorDBWeaviateCURL(publisher)
        # self.vector_db = VectorDBLocal(publisher)
        self.cq = ChatQuery(self.vector_db, inline, followups)

    def get_chat_result(self, chat_history, query):
        return self.cq.answer_query_with_context(chat_history, query)
