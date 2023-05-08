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
from utilities.result_publisher import BasePublisher, ResultPublisher, DebugPublisher
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_utils.streaming_socket_callback_handler import StreamingSocketOutCallbackHandler

from publisher_enum import PublisherEnum
from weaviate_utils.weaviate_class import WeaviateClassArticleSnippet, WeaviateClassBookSnippet
from utils import get_article_info_from_url

dynamodb = boto3.resource('dynamodb')
logging.getLogger().setLevel(logging.INFO)

HISTORY_LOOKBACK_LEN = 5

def lambda_handler(event, context):
    response = {'statusCode': 200}
    # get necessary request context
    route_key = event.get('requestContext', {}).get('routeKey')
    connection_id = event.get('requestContext', {}).get('connectionId')
    if connection_id is None or route_key is None:
        return {'statusCode': 400}
    logging.info(f"Successfully invoked! with route_key: {route_key}")

    local = event.get('requestContext', {}).get('local', False)
    db = event.get('requestContext')['in_mem_db'] if local else ChatHistoryDB()
    chat_db = ChatHistoryService(connection_id, db)
    result_publisher = DebugPublisher() if local else ResultPublisher(event, connection_id)
    body = json.loads(event.get("body", "{}"))
    if route_key == '$connect':
        logging.info("Route connect")
        try:
            chat_db.create_chat_history()
            url = body.get("url")
            response['statusCode'] = 200
        except Exception as e:
            logging.error(f"Failed to create chat history with error {e}")
            response['statusCode'] = 500
    elif route_key == '$disconnect':
        logging.info("Route disconnect")
        try:
            chat_db.remove_chat_history()
            response['statusCode'] = 200
        except Exception as e:
            logging.error(f"Failed to remove chat history with error {e}")
            response['statusCode'] = 500
    elif route_key == 'intro':
        logging.info("Route intro")
        response = handle_intro_query(result_publisher, event)
    elif route_key == 'query':
        logging.info("Route query")
        response = handle_query_or_summarize("query", body, chat_db, result_publisher)
    elif route_key == 'summarize':
        logging.info('Route summarize')
        response = handle_query_or_summarize("summarize", body, chat_db, result_publisher)
        # try:
        #     response = handle_query(event, chat_db, result_publisher)
        # except Exception as e:
        #     logging.error(f"Failed to handle query with error {e}")
        #     response = {
        #         'statusCode': 500,
        #         'body': ('Failed to handle query with error' + str(e))
        #     }
    return response

def handle_query_or_summarize(req_type, body, chat_db: ChatHistoryService, result_publisher):
    logging.info(f"Received {req_type} body: " + json.dumps(body))
    if req_type == 'summarize':
        query = "Summarize this article"
    elif req_type == 'query':
        query = body['query']
    else:
        raise Exception('req type should be "summarize" or "query"')

    config = {
        'url': body.get("url", ""),
        'use_local_vector_db': body.get("use_local_vector_db", False),
        'inline': body.get("inline", False),
        'followups': body.get("followups", False),
        'use_summaries': body.get("use_summaries", True),
        'condense_model': body.get("condense_model", "gpt-3.5-turbo"),
        'answer_model': body.get("answer_model", "gpt-3.5-turbo"),
        'streaming': True,
        'verbose': True
    }

    return _handle_query(query, result_publisher, chat_db, config)

def handle_intro_query(result_publisher, event):
    body = json.loads(event.get("body", ""))
    url = body.get("url", "")
    publisher = get_publisher_for_url(url)
    
    intro_questions_for_publisher = {
        PublisherEnum.ATLANTA_DUNIA: [""],
        PublisherEnum.BBC_INDIA: [""],
        PublisherEnum.GOOGLE_NEWS: ["What is the latest in the Ukraine crisis?", "What are some movies that came out this week?"],
        PublisherEnum.HORTICULT: ["What's the lineup at the SB Orchid Show?", "What are some fun plant-based gift ideas?"],
        PublisherEnum.NBA: ["What are the biggest storylines in the NBA playoffs?", "Who's the leading scorer in the NBA playoffs?"],
        PublisherEnum.SF_STANDARD: [""],
        PublisherEnum.TECHCRUNCH: ["What are some startups that raised money recently?", "What are some features in the latest iOS?"],
        PublisherEnum.VICE: ['What are some of the top stories today?'],
        PublisherEnum.SEQUOIA: ["What are some recent investments by Sequoia?", "What's the latest in generative AI?"]
    }
    intro_questions = intro_questions_for_publisher.get(publisher)
    if intro_questions is None:
        intro_questions = ["What are some of the top stories today?"]

    message = "Hi, I'm DeJour, your personal news assistant. You can ask me questions like:"
    message_fragments = re.split('([\s.,;()]+)', message)
    for fragment in message_fragments:
        result_publisher.post_to_connection(json.dumps({
            "type": "intro",
            "message": fragment,
            "questions": []
        }))
        time.sleep(0.05)
    result_publisher.post_to_connection(json.dumps({
        "type": "intro",
        "message": "",
        "questions": intro_questions
    }))
    result_publisher.post_to_connection(json.dumps({
        "type": "end",
    }))

    # qh = QueryHandler(publisher, result_publisher, False)
    # intro_query = ChatQuery("intro")
    # intro_result = qh.get_chat_result([], intro_query)
    return {
        'statusCode': 200,
    }

def _handle_query(query, result_publisher: BasePublisher, chat_db: ChatHistoryService, config: dict):
    url = config.get('url')
    logging.info("Handling query: " + query)
    chat_history = chat_db.get_chat_history()
    logging.info("Got chat history: " + str(chat_history))
    cur_article_info = get_article_info_from_url(url)
    config['cur_article_info'] = cur_article_info
    response = _make_query(query, result_publisher, chat_history, config)
    formatted_response = json.dumps(response)
    logging.info("Formatted response: " + formatted_response)
    sources = response.get("sources")
    followup_questions = response.get("followup_questions")
    if sources is None:
        logging.error("Missing sources")
        return {
            'statusCode': 200,
            'body': "Missing sources"
        }
    if followup_questions is None:
        followup_questions = []
    sources_message = {
        "type": "message",
        "sources": sources,
        "questions": followup_questions
    }
    formatted_sources_message = json.dumps(sources_message)
    result_publisher.post_to_connection(formatted_sources_message)

    # Update chat history
    if response.get("error") is not None:
        logging.error("Failed to update chat history with error: " + response['error'])
        return {
            'statusCode': 200,
            'body': response['error']
        }
    answer = response['answer']
    chat_db.update_chat_history(query, answer)
    return {
        'statusCode': 200,
        'body': 'Query processed.'
    }

def _make_query(query, result_publisher: BasePublisher, chat_history, config: dict):
    chat_history_tups = [(e['question'], e['answer']) for e in chat_history]
    chat_history_tups = chat_history_tups[-1*HISTORY_LOOKBACK_LEN:]
    url = config.get('url')
    try:
        publisher = get_publisher_for_url(url)
        # qh = QueryHandler(publisher, result_publisher, inline, followups=followups, use_summaries=use_summaries, use_local_vector_db=use_local_vector_db, verbose=True)
        qh = QueryHandler(publisher, result_publisher, config)
        try:
            chat_result = qh.get_chat_result(chat_history_tups, query, config.get('cur_article_info'))
            if "followup_questions" in chat_result:
                chat_result["questions"] = chat_result["followup_questions"]
            return chat_result
        except Exception as e:
            logging.error(f"Chat result failed with error: {e}")
            return {
                "answer": "DeJour is not supported on this website",
                "sources": [],
                "error": "Dejour is not supported on this website"
            }

    except Exception as e:
        logging.error(f"Get publisher failed with error: {e}")
        logging.error(f"Invalid url: {url}")
        return {
            "answer": "DeJour is not supported on this website",
            "sources": [],
            "error": "Dejour is not supported on this website"
        }
    
def get_publisher_for_url(url):
    if "atlantadunia" in url:
        return PublisherEnum.ATLANTA_DUNIA
    elif "bbc" in url:
        return PublisherEnum.BBC_INDIA
    elif "google" in url:
        return PublisherEnum.GOOGLE_NEWS
    elif "horticult" in url:
        return PublisherEnum.HORTICULT
    elif "nba" in url:
        return PublisherEnum.NBA
    elif "sfstandard" in url:
        return PublisherEnum.SF_STANDARD
    elif "techcrunch" in url:
        return PublisherEnum.TECHCRUNCH
    elif "vice" in url:
        return PublisherEnum.VICE
    elif "sequoia" in url:
        return PublisherEnum.SEQUOIA    
    elif PublisherEnum.BOOK_HEART_OF_DARKNESS_PDF.value in url:
        return PublisherEnum.BOOK_HEART_OF_DARKNESS_PDF
    elif PublisherEnum.BOOK_LOTR_PDF.value in url:
        return PublisherEnum.BOOK_LOTR_PDF
    else:
        raise Exception("Invalid url")

class QueryHandler(object):
    def __init__(self, publisher_enum: PublisherEnum, result_publisher, config):
    # def __init__(self, publisher_enum: PublisherEnum, result_publisher, inline: bool, followups: bool, use_summaries: bool, verbose: bool, use_local_vector_db: bool = False):
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
        # self.cq = ChatQuery(self.vector_db, condense_model=condense_model, chat_model=chat_model, inline=inline, followups=followups, streaming=True, streaming_callback=streaming_callback, use_summaries=use_summaries, verbose=verbose, book=is_book)

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
            "body": json.dumps(event_body)
        }
        return event
    
    event = get_event('$connect', {"url": options.url})
    connect_resp = lambda_handler(event, None)
    assert connect_resp['statusCode'] == 200

    def get_event(route_key, body):
        event_body = body
        event = {
            "requestContext": {
                "routeKey": route_key,
                "connectionId": connection_id,
                'local': True,
                'in_mem_db': in_mem_db
            },
            "body": json.dumps(event_body)
        }
        return event
    
    event = get_event('intro', {"url": options.url})
    connect_resp = lambda_handler(event, None)
    assert connect_resp['statusCode'] == 200

    if options.summarize:
        event = get_event('summarize', {
            'url': options.url,
            'inline': options.inline,
            'followups': options.followups
        })

        result = lambda_handler(event, None)
        assert result['statusCode'] == 200
    else:
        while True:
            print("\nHow can I help you?\n")
            query = input()
            #TODO: add followups model too
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
