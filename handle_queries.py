from main import Runner
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin

from utils import use_ghetto_disk_cache
from crawlers.gn_crawler import GNCrawler
from utilities.memory_cache import ChatHistoryMemoryService

app = Flask(__name__)
chat_history_service = ChatHistoryMemoryService()
CORS(app)


@app.route('/query', methods=['GET'])
# @cross_origin(origin='*')
def handle_query():
    new_query = request.args['query']
    session_id = request.args['session_id']
    chat_history = chat_history_service.get_chat_history(session_id)
    
    # Call your api with the chat history and the new query 

    use_cache = request.args.get('use_cache', True)
    function = answer_query
    # if use_cache:
    #     function = use_ghetto_disk_cache(function)
    result = function(chat_history, new_query)
    response = jsonify(result)
    response.headers.add('Access-Control-Allow-Origin', '*')

    # Update the chat history
    chat_history_service.add_object_if_needed(session_id, (new_query, response.answer))
    updated_chat_history = chat_history_service.get_chat_history(session_id)
    print(updated_chat_history)
    return response
    
def answer_query(chat_history, query):
    return Runner(GNCrawler).get_chat_result(chat_history, query)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
    print("Starting server...")
