from main import Runner
from flask import Flask, jsonify, request
from utils import use_ghetto_disk_cache

app = Flask(__name__)

@app.route('/query', methods=['GET'])
def handle_query():
    query = request.args['query']
    result = use_ghetto_disk_cache(answer_query)(query)
    response = jsonify(result)
    return response

def answer_query(query):
    return Runner().get_result_manual(query)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
