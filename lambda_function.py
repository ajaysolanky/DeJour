import os
# os.environ["PYTHONBREAKPOINT"] = "ipdb.set_trace"

import json
import logging

from query_handler import QueryHandler
from publisher_enum import PublisherEnum

logging.getLogger().setLevel(logging.INFO)

def lambda_handler(event, context):
    # breakpoint()
    logging.info("EVENT: %s ; CONTEXT: %s" % (event, context))
    body = event["body"]
    if isinstance(body, str):
        body = json.loads(body)
    
    chat_history = body['chat_history']
    query = body['query']
    publisher = body['publisher']
    qh = QueryHandler(PublisherEnum(publisher))
    chat_result = qh.get_chat_result(chat_history, query)
    return chat_result