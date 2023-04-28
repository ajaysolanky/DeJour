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
    qh = QueryHandler(publisher, DebugPublisher(), {
        'inline': False,
        'followups': True,
        'verbose': True,
        'condense_model': 'gpt-3.5-turbo',
        'answer_model': 'gpt-3.5-turbo',
        'streaming': False
    })
    try:
        chat_result = qh.get_chat_result([], query, get_article_info_from_url('adslk'))
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
    def __init__(self, publisher_enum: PublisherEnum, result_publisher, config):
        is_book = publisher_enum.name.startswith('BOOK_')
        if config.get('use_local_vector_db'):
            self.vector_db = VectorDBLocal({'publisher_name': publisher_enum.value})
        else:
            if is_book:
                args = {"weaviate_class": WeaviateClassBookSnippet(publisher_enum.value)}
            else:
                args = {"weaviate_class": WeaviateClassArticleSnippet(publisher_enum.value)}
            self.vector_db = VectorDBWeaviateCURL(args)

        streaming_callback = StreamingSocketOutCallbackHandler(result_publisher)
        config["is_book"] = is_book
        config["streaming_callback"] = streaming_callback
        self.cq = ChatQuery(self.vector_db, config)

    def get_chat_result(self, chat_history, query, cur_article_info):
        return self.cq.answer_query_with_context(chat_history, query, cur_article_info.title)

if __name__ == '__main__':
    p = optparse.OptionParser()
    p.add_option('--url')
    p.add_option('--condense_model', default='gpt-3.5-turbo')
    p.add_option('--answer_model', default='gpt-3.5-turbo')
    p.add_option('--inline', action='store_true')
    p.add_option('--summarize', action='store_true')
    p.add_option('--followups', action='store_true')
    p.add_option('--use_summaries', action='store_true')
    p.add_option('--use_local_vector_db', action='store_true')
    random_connection_id = str(uuid.uuid4())
    p.add_option('--connectionid', default=random_connection_id)
    options, arguments = p.parse_args()

    connection_id = options.connectionid
    in_mem_db = InMemoryDB()

    def get_event(route_key, body):
        event_body = body
        event = {
            "requestContext": {
                "routeKey": route_key,
                "connectionId": connection_id,
                'local': True,
                'in_mem_db': in_mem_db
            },
            "queryStringParameters": event_body
        }
        return event

    print("\nHow can I help you?\n")
    query = input()
    event = get_event('query', {
        'query': query,
        'url': options.url,
        'inline': options.inline,
        'followups': options.followups,
        'use_summaries': options.use_summaries,
        'use_local_vector_db': options.use_local_vector_db,
        'condense_model': options.condense_model,
        'answer_model': options.answer_model
    })
    
    result = lambda_handler(event, None)
    assert result['statusCode'] == 200
