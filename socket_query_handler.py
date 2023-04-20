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
from weaviate_utils.weaviate_class import WeaviateClassArticleSnippet

dynamodb = boto3.resource('dynamodb')
logging.getLogger().setLevel(logging.INFO)

HISTORY_LOOKBACK_LEN = 3

def lambda_handler(event, context):
    response = {'statusCode': 200}
    # get necessary request context
    route_key = event.get('requestContext', {}).get('routeKey')
    connection_id = event.get('requestContext', {}).get('connectionId')
    if connection_id is None or route_key is None:
        return {'statusCode': 400}
    logging.info(f"Successfully invoked! with route_key: {route_key}")

    db = ChatHistoryDB()
    chat_db = ChatHistoryService(connection_id, db)
    result_publisher = ResultPublisher(event, connection_id)
    if route_key == '$connect':
        logging.info("Route connect")
        try:
            chat_db.create_chat_history()
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
        response = handle_query(event, chat_db, result_publisher)
        # try:
        #     response = handle_query(event, chat_db, result_publisher)
        # except Exception as e:
        #     logging.error(f"Failed to handle query with error {e}")
        #     response = {
        #         'statusCode': 500,
        #         'body': ('Failed to handle query with error' + str(e))
        #     }
    return response

def handle_query(event, chat_db, result_publisher):
    # Handle the query event
    # Here, you can retrieve the query parameter from the request and process it
    # For example, you can print the value of the 'query' parameter
    body = json.loads(event.get("body", ""))
    logging.info("Received query body: " + str(body))
    query = body.get("query", "")
    url = body.get("url", "")
    inline = body.get("inline", False)
    followups = body.get("followups", False)
    logging.info("Received query: " + query)
    
    return _handle_query(query, url, inline, chat_db, result_publisher, followups)

def handle_intro_query(result_publisher, event):
    body = json.loads(event.get("body", ""))
    url = body.get("url", "")
    publisher = get_publisher_for_url(url)
    
    intro_questions_for_publisher = {
        PublisherEnum.ATLANTA_DUNIA: [""],
        PublisherEnum.BBC_INDIA: [""],
        PublisherEnum.GOOGLE_NEWS: ["What is the latest in the Ukraine crisis?", "What are some movies that came out this week?"],
        PublisherEnum.NBA: ["What are the biggest storylines in the NBA playoffs?", "Who's the leading scorer in the NBA playoffs?"],
        PublisherEnum.SF_STANDARD: [""],
        PublisherEnum.TECHCRUNCH: ["What are some startups that raised money recently?", "What are some features in the latest iOS?"],
        PublisherEnum.VICE: ['What are some of the top stories today?']
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
    

    # qh = QueryHandler(publisher, result_publisher, False)
    # intro_query = ChatQuery("intro")
    # intro_result = qh.get_chat_result([], intro_query)
    return {
        'statusCode': 200,
    }

def _handle_query(query, url, inline, chat_db: ChatHistoryService, result_publisher, followups):
    logging.info("Handling query: " + query)
    chat_history = chat_db.get_chat_history()
    logging.info("Got chat history: " + str(chat_history))
    response = _make_query(query, url, chat_history, inline, result_publisher, followups)
    formatted_response = json.dumps(response)
    logging.info("Formatted response: " + formatted_response)
    sources = response.get("sources")
    if sources is None:
        logging.error("Missing sources")
        return {
            'statusCode': 200,
            'body': "Missing sources"
        }
    sources_message = {
        "type": "message",
        "sources": sources
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

def _make_query(query, url, chat_history, inline, result_publisher, followups):
    chat_history_tups = [(e['question'], e['answer']) for e in chat_history]
    chat_history_tups = chat_history_tups[-1*HISTORY_LOOKBACK_LEN:]
    try:
        publisher = get_publisher_for_url(url)
        qh = QueryHandler(publisher, result_publisher, inline, followups=followups, verbose=True)
        try:
            chat_result = qh.get_chat_result(chat_history_tups, query)
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
    def __init__(self, publisher: PublisherEnum, result_publisher, inline: bool, followups: bool, verbose: bool):
        args = {"weaviate_class": WeaviateClassArticleSnippet(publisher.value)}
        self.vector_db = VectorDBWeaviateCURL(publisher, args)
        # self.vector_db = VectorDBLocal(publisher)
        streaming_callback = StreamingSocketOutCallbackHandler(result_publisher)
        self.cq = ChatQuery(self.vector_db, result_publisher, inline, followups, streaming=True, streaming_callback=streaming_callback, verbose=verbose)

    def get_chat_result(self, chat_history, query):
        return self.cq.answer_query_with_context(chat_history, query, None)
    
if __name__ == '__main__':
    p = optparse.OptionParser()
    p.add_option('--url', default="https://www.news.google.com")
    p.add_option('--inline', action='store_true')
    p.add_option('--followups', action='store_true')
    random_connection_id = str(uuid.uuid4())
    # random_query = "What is the biggest news today?"
    # p.add_option('--query', default=random_query)
    p.add_option('--connectionid', default=random_connection_id)
    # p.add_option('--use_local_news_db', action='store_true')
    options, arguments = p.parse_args()

    connection_id = options.connectionid
    db = InMemoryDB()
    chat_db = ChatHistoryService(connection_id, db)
    chat_db.create_chat_history()
    result_publisher = DebugPublisher()

    while True:
        print("\nHow can I help you?\n")
        query = input()
        event = {
            "body": json.dumps({"query": query, "url": options.url, "inline": options.inline, "followups": options.followups})
        }
        
        result = handle_query(event, chat_db, result_publisher)
