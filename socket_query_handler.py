import json
import optparse
import logging
import boto3
import uuid
from query import ChatQuery
from vector_db import VectorDBWeaviateCURL, VectorDBWeaviatePythonClient, VectorDBLocal
from utilities.chat_history_db import ChatHistoryService, ChatHistoryDB, InMemoryDB
from utilities.result_publisher import ResultPublisher, DebugPublisher
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_utils.streaming_socket_callback_handler import StreamingSocketOutCallbackHandler

from publisher_enum import PublisherEnum

dynamodb = boto3.resource('dynamodb')
logging.getLogger().setLevel(logging.INFO)

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
    elif route_key == 'query':
        logging.info("Route query")
        try:
            response = handle_query(connection_id, event, chat_db, result_publisher)
        except Exception as e:
            logging.error(f"Failed to handle query with error {e}")
            response = {
                'statusCode': 500,
                'body': ('Failed to handle query with error' + str(e))
            }
    return response

def handle_query(connection_id, event, chat_db, result_publisher):
    # Handle the query event
    # Here, you can retrieve the query parameter from the request and process it
    # For example, you can print the value of the 'query' parameter
    body = json.loads(event.get("body", ""))
    logging.info("Received query body: " + str(body))
    query = body.get("query", "")
    url = body.get("url", "")
    inline = body.get("inline", False)
    logging.info("Received query: " + query)
    
    return _handle_query(query, url, inline, connection_id, chat_db, result_publisher)

def _handle_query(query, url, inline, connection_id, chat_db, result_publisher):
    chat_history = chat_db.get_chat_history()
    response = _make_query(query, url, chat_history, inline, result_publisher)
    formatted_response = json.dumps(response)
    result_publisher.post_to_connection(formatted_response)

    # Update chat history
    answer = response['answer']
    if response.get("error") is not None:
        return {
            'statusCode': 200,
            'body': response['error']
        }

    chat_db.update_chat_history(query, answer)
    chat_history = chat_db.get_chat_history()
    chat_history_response = json.dumps(chat_history)
    result_publisher.post_to_connection(chat_history_response) # This is just for debuggings
    return {
        'statusCode': 200,
        'body': 'Query processed.'
    }

def _make_query(query, url, chat_history, inline, result_publisher):
    try:
        publisher = get_publisher_for_url(url)
        qh = QueryHandler(publisher, result_publisher, inline)
        try:
            chat_result = qh.get_chat_result(chat_history, query)
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
    def __init__(self, publisher: PublisherEnum, result_publisher, inline: bool):
        self.vector_db = VectorDBWeaviateCURL(publisher)
        # self.vector_db = VectorDBLocal(publisher)
        streaming_callback = StreamingSocketOutCallbackHandler(result_publisher)
        self.cq = ChatQuery(self.vector_db, result_publisher, inline, streaming=True, streaming_callback=streaming_callback)

    def get_chat_result(self, chat_history, query):
        return self.cq.answer_query_with_context(chat_history, query)
    
if __name__ == '__main__':
    p = optparse.OptionParser()
    p.add_option('--url', default="https://www.news.google.com")
    p.add_option('--inline', action='store_true')
    random_connection_id = str(uuid.uuid4())
    random_query = "What is the biggest news today?"
    p.add_option('--query', default=random_query)
    p.add_option('--connectionid', default=random_connection_id)
    # p.add_option('--use_local_news_db', action='store_true')
    options, arguments = p.parse_args()

    connection_id = options.connectionid
    db = InMemoryDB()
    chat_db = ChatHistoryService(connection_id, db)
    chat_db.create_chat_history()
    result_publisher = DebugPublisher()
    result = _handle_query(options.query, options.url, options.inline, connection_id, chat_db, result_publisher)
    # crawler = build_crawler(publisher_str, options.use_local_vector_db, options.use_local_news_db)
    # crawler.run_crawler()