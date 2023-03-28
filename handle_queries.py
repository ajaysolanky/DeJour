from main import Runner
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin

from utils import use_ghetto_disk_cache
from crawlers.gn_crawler import GNCrawler

app = Flask(__name__)
CORS(app)


@app.route('/query', methods=['GET'])
# @cross_origin(origin='*')
def handle_query():
    query = request.args['query']
    use_cache = request.args.get('use_cache', True)
    function = answer_query
    if use_cache:
        function = use_ghetto_disk_cache(function)
    result = function(query)
    response = jsonify(result)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

def answer_query(query):
    return Runner(GNCrawler).get_result_manual(query)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
