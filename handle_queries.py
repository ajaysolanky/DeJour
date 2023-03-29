from main import Runner
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin

from utils import use_ghetto_disk_cache
from crawlers.gn_crawler import GNCrawler
from utilities.disk_cache import ChatHistoryService

app = Flask(__name__)
chat_history_service = ChatHistoryService()
CORS(app)

# helpful tut for setting up ec2: https://www.twilio.com/blog/deploy-flask-python-app-aws

@app.route('/query', methods=['GET'])
# @cross_origin(origin='*')
def handle_query():
    new_query = request.args['query']
    session_id = request.args['session_id']
    chat_history = chat_history_service.get_chat_history(session_id)
    if chat_history is None:
        chat_history = ""
    
    # Call your api with the chat history and the new query 

    # Update chat history
    chat_history_service.add_object_if_needed(session_id, chat_history + new_query)

    use_cache = request.args.get('use_cache', True)
    function = answer_query
    if use_cache:
        function = use_ghetto_disk_cache(function)
    result = function(new_query, chat_history)
    response = jsonify(result)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response
    
def answer_query(query):
    return Runner(GNCrawler).get_result_manual(query)

if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=8080)
    print("Starting server...")
