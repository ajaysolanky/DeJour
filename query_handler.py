from news_db import NewsDB
from query import ChatQuery
from vector_db import VectorDBWeaviateCURL, VectorDB

from publisher_enum import PublisherEnum

class QueryHandler(object):
    def __init__(self, publisher: PublisherEnum):
        self.vector_db = VectorDBWeaviateCURL(publisher)
        self.cq = ChatQuery(self.vector_db)

    def get_chat_result(self, chat_history, query):
        return self.cq.answer_query_with_context(chat_history, query)
