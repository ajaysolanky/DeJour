import logging
from flask import Flask, jsonify, request
from flask import send_from_directory
from flask_cors import CORS, cross_origin
from utils import use_ghetto_disk_cache
from crawlers.gn_crawler import GNCrawler
from crawlers.source_crawler import SourceCrawler
from crawlers.nbacrawler import NBACrawler
from utilities.memory_cache import ChatHistoryMemoryService
from utilities.html_reader import HTMLReader
from publisher_enum import PublisherEnum
from query import ChatQuery
from query_handler import QueryHandler
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from vector_db import VectorDBWeaviateCURL, VectorDBWeaviatePythonClient, VectorDBLocal
from utilities.chat_history_db import ChatHistoryService, ChatHistoryDB, InMemoryDB
from utilities.result_publisher import ResultPublisher, DebugPublisher
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_utils.streaming_socket_callback_handler import StreamingSocketOutCallbackHandler

from publisher_enum import PublisherEnum
from weaviate_utils.weaviate_class import WeaviateClassArticleSnippet, WeaviateClassBookSnippet
from utils import get_article_info_from_url

app = Flask(__name__)
chat_history_service = ChatHistoryMemoryService()
CORS(app)

#TODO: consolidate this code with lambda_handler in query_handler.py
@app.route('/summarize', methods=['GET'])
def handle_summarize():
    query = "Summarize this article"
    url = request.args['url']
    qh = QueryHandler(PublisherEnum.TECHCRUNCH, DebugPublisher(), False, followups=True, verbose=True)
    try:
        chat_result = qh.get_chat_result([], query, url)
        return {
            "answer": chat_result["answer"]
        }
    except Exception as e:
        logging.error(f"Chat result failed with error: {e}")
        return {
            "answer": "DeJour is not supported on this website"
        }

@app.route('/logo.png', methods=['GET'])
def serve_logo():
    response = send_from_directory('.well-known', 'logo.png')
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/query', methods=['GET'])
def handle_chatgpt_query():
    query = request.args['query']
    question_topic = request.args['topic']
    default_publisher = PublisherEnum.GOOGLE_NEWS
    publisher = default_publisher
    if question_topic == "tech":
        publisher = PublisherEnum.TECHCRUNCH
    elif question_topic == "basketball":
        publisher = PublisherEnum.NBA
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
        return {
            "answer": chat_result["answer"],
            "sources": mapped_sources,
            # "followup_queries": followup_prompts
        }
    except Exception as e:
        logging.error(f"Chat result failed with error: {e}")
        return {
            "answer": "DeJour is not supported on this website",
            "sources": [],
            "error": "Dejour is not supported on this website"
        }



@app.route('/.well-known/ai-plugin.json', methods=['GET'])
def serve_manifest():
    response = send_from_directory('.well-known', 'ai-plugin.json')
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/.well-known/openai.yaml', methods=['GET'])
def serve_api_spec():
    print("Hi")
    response = send_from_directory('.well-known', 'openai.yaml')
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

# @app.route('/query', methods=['GET'])
# # @cross_origin(origin='*')
# def handle_query():
#     import time
#     st = time.time()
#     new_query = request.args['query']
#     session_id = request.args['session_id']
#     # source = request.args['source']
#     url = request.args['url']
#     current_article_title = request.args.get('article_title')
#     inline = request.args.get('inline') == 'True'
#     followups = request.args.get('followups') == 'True'
#     streaming = request.args.get('streaming') == 'True'
#     streaming_callback = StreamingStdOutCallbackHandler() if streaming else None

#     if not new_query:
#         raise Exception("Query is empty")
#     if not session_id:
#         raise Exception("Session id is empty")
#     if not url:
#         raise Exception("Url is empty")
    
#     try:
#         logging.info(f"Received query for url: {url}")
#         source = get_publisher_for_url(url)
#         logging.info(f"Url mapped to source: {source}")
#         chat_history = chat_history_service.get_chat_history(session_id)
    
#         # Call your api with the chat history and the new query 

#         result = answer_query(chat_history, new_query, source, inline, followups, streaming, streaming_callback, current_article_title)
#         response = jsonify(result)
#         response.headers.add('Access-Control-Allow-Origin', '*')

#         # Update the chat history
#         chat_history_service.add_object_if_needed(session_id, new_query, result["answer"])
#         updated_chat_history = chat_history_service.get_chat_history(session_id)
#         logging.info(updated_chat_history)
#         logging.info(f"TIME: {time.time() - st}")
#         return response
#     except:
#         logging.info(f"Invalid url: {url}")
#         return format_error_response_as_answer("DeJour is not supported on this website")

def format_error_response_as_answer(error):
    response = jsonify({
        "answer": error,
        "sources": []
    })
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
    logging.info("Starting server...")
    # html_reader = HTMLReader()
