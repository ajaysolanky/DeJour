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
    publisher = body['publisher']
    qh = QueryHandler(PublisherEnum(publisher))
    chat_result = qh.get_chat_result(chat_history, query)
    return chat_result

class QueryHandler(object):
    def __init__(self, publisher: PublisherEnum):
        self.vector_db = VectorDBWeaviateCURL(publisher)
        # self.vector_db = VectorDBLocal(publisher)
        self.cq = ChatQuery(self.vector_db)

    def get_chat_result(self, chat_history, query):
        return self.cq.answer_query_with_context(chat_history, query)
