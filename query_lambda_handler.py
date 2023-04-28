import json
import re
import optparse
import logging
import boto3
import time
import uuid
from query import ChatQuery
from vector_db import VectorDBWeaviateCURL, VectorDBWeaviatePythonClient, VectorDBLocal
from utilities.chat_history_db import ChatHistoryService, ChatHistoryDB, InMemoryDB
from utilities.result_publisher import ResultPublisher, DebugPublisher
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_utils.streaming_socket_callback_handler import StreamingSocketOutCallbackHandler

from publisher_enum import PublisherEnum
from weaviate_utils.weaviate_class import WeaviateClassArticleSnippet, WeaviateClassBookSnippet
from utils import get_article_info_from_url

dynamodb = boto3.resource('dynamodb')
logging.getLogger().setLevel(logging.INFO)

HISTORY_LOOKBACK_LEN = 5

def lambda_handler(event, context):
    logging.info("EVENT: %s ; CONTEXT: %s" % (event, context))
    response = {
        "statusCode": 200,
         "headers": {
            "Content-Type": "application/json"
        }
    }

    query_params = event.get("queryStringParameters", {})
    query = query_params.get("query")
    question_topic = query_params.get("topic")
    default_publisher = PublisherEnum.GOOGLE_NEWS
    publisher = default_publisher
    if question_topic == "tech":
        publisher = PublisherEnum.TECHCRUNCH
    elif question_topic == "basketball":
        publisher = PublisherEnum.GOOGLE_NEWS
    elif question_topic == "general" or question_topic == "unknown":
        publisher = PublisherEnum.GOOGLE_NEWS
    qh = QueryHandler(publisher, DebugPublisher(), False, followups=True, verbose=True)
    try:
        chat_result = qh.get_chat_result([], query, query)
        def transform_sources(source):
            return source["url"]
        mapped_sources = list(map(transform_sources, chat_result["sources"]))
        if "followup_questions" in chat_result:
            followup_prompts = chat_result["followup_questions"]
        else:
            followup_prompts = []
        logging.info("Chat result: %s" % chat_result)
        response["body"] = json.dumps({
            "answer": chat_result["answer"],
            "sources": mapped_sources,
        })
        response["answer"] = chat_result["answer"]
        response["sources"] = mapped_sources
        return response
    except Exception as e:
        logging.error(f"Chat result failed with error: {e}")
        return {
            "statusCode": 500,
            "answer": "DeJour is not supported on this website",
            "sources": [],
            "error": "Dejour is not supported on this website"
        }

def format_error_response_as_answer(error):
    response = {
        "statusCode": 200,
        "answer": error,
        "sources": []
    }
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

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
    def __init__(self, publisher_enum: PublisherEnum, result_publisher, inline: bool, followups: bool, verbose: bool):
        is_book = publisher_enum.name.startswith('BOOK_')
        if is_book:
            args = {"weaviate_class": WeaviateClassBookSnippet(publisher_enum.value)}
        else:
            args = {"weaviate_class": WeaviateClassArticleSnippet(publisher_enum.value)}
        self.vector_db = VectorDBWeaviateCURL(args)
        # self.vector_db = VectorDBLocal(publisher)
        streaming_callback = StreamingSocketOutCallbackHandler(result_publisher)
        self.cq = ChatQuery(self.vector_db, inline, followups, streaming=False, streaming_callback=streaming_callback, verbose=verbose, book=is_book)

    def get_chat_result(self, chat_history, query, cur_article_info):
        return self.cq.answer_query_with_context(chat_history, query, cur_article_info.title)