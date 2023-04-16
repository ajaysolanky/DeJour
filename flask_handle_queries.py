import logging
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from utils import use_ghetto_disk_cache
from crawlers.gn_crawler import GNCrawler
from crawlers.source_crawler import SourceCrawler
from crawlers.nbacrawler import NBACrawler
from utilities.memory_cache import ChatHistoryMemoryService
from utilities.html_reader import HTMLReader
from publisher_enum import PublisherEnum
from query_handler import QueryHandler

app = Flask(__name__)
chat_history_service = ChatHistoryMemoryService()
CORS(app)

@app.route('/query', methods=['GET'])
# @cross_origin(origin='*')
def handle_query():
    import time
    st = time.time()
    new_query = request.args['query']
    session_id = request.args['session_id']
    # source = request.args['source']
    url = request.args['url']
    inline = request.args.get('inline') == 'True'
    followups = request.args.get('followups') == 'True'

    if not new_query:
        raise Exception("Query is empty")
    if not session_id:
        raise Exception("Session id is empty")
    if not url:
        raise Exception("Url is empty")
    
    try:
        logging.info(f"Received query for url: {url}")
        source = get_publisher_for_url(url)
        logging.info(f"Url mapped to source: {source}")
        chat_history = chat_history_service.get_chat_history(session_id)
    
        # Call your api with the chat history and the new query 

        result = answer_query(chat_history, new_query, source, inline, followups)
        response = jsonify(result)
        response.headers.add('Access-Control-Allow-Origin', '*')

        # Update the chat history
        chat_history_service.add_object_if_needed(session_id, new_query, result["answer"])
        updated_chat_history = chat_history_service.get_chat_history(session_id)
        logging.info(updated_chat_history)
        logging.info(f"TIME: {time.time() - st}")
        return response
    except:
        logging.info(f"Invalid url: {url}")
        return format_error_response_as_answer("DeJour is not supported on this website")

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
    
def answer_query(chat_history, query, source, inline, followups):
    # runner = runner_dict.get(PublisherEnum(source))()
    query_handler = QueryHandler(source, inline, followups)
    if query_handler:
        return query_handler.get_chat_result(chat_history, query)
    else:
        raise Exception("Invalid source")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
    logging.info("Starting server...")
    # html_reader = HTMLReader()
