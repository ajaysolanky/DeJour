import json
import uuid
import logging
import optparse
from query import ChatQuery
from vector_db import VectorDBWeaviateCURL, VectorDBWeaviatePythonClient, VectorDBLocal
from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from publisher_enum import PublisherEnum

logging.getLogger().setLevel(logging.INFO)

def lambda_handler(event, context):
    logging.info("EVENT: %s ; CONTEXT: %s" % (event, context))
    body = event["body"]
    if isinstance(body, str):
        body = json.loads(body)
    
    chat_history = body['chat_history']
    query = body['query']
    # publisher = body['publisher']
    url = body['url']
    current_article_title = body.get('article_title')
    inline = body.get('inline')
    followups = body.get('followups')
    streaming = body.get('streaming')
    if streaming:
        streaming_callback = StreamingStdOutCallbackHandler()
    try:
        publisher = get_publisher_for_url(url)
        qh = QueryHandler(publisher, inline, followups, streaming, streaming_callback=streaming_callback)
        chat_result = qh.get_chat_result(chat_history, query, current_article_title)
        return chat_result
    except Exception as e:
        print(f"Get publisher failed with error: {e}")
        print(f"Invalid url: {url}")
        return format_error_response_as_answer("DeJour is not supported on this website")
    
def format_error_response_as_answer(error):
    return {
        "answer": error,
        "sources": []
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
    def __init__(
            self,
            publisher: PublisherEnum,
            inline: bool,
            followups: bool,
            streaming: bool,
            streaming_callback: BaseCallbackHandler = None,
            verbose: bool = True):
        self.vector_db = VectorDBWeaviateCURL(publisher)
        # self.vector_db = VectorDBLocal(publisher)
        self.cq = ChatQuery(
            self.vector_db,
            inline=inline,
            followups=followups,
            streaming=streaming,
            streaming_callback=streaming_callback,
            verbose=verbose)

    def get_chat_result(self, chat_history, query, current_article_title):
        return self.cq.answer_query_with_context(chat_history, query, current_article_title)

if __name__ == '__main__':
    p = optparse.OptionParser()
    p.add_option('--publisher')
    p.add_option('--current_article_title')
    p.add_option('--inline', action='store_true', default=False)
    p.add_option('--followups', action='store_true', default=False)
    p.add_option('--streaming', action='store_true', default=False)
    options, arguments = p.parse_args()
    qh = QueryHandler(
        publisher=PublisherEnum(options.publisher),
        inline=options.inline,
        followups=options.followups,
        streaming=options.streaming,
        streaming_callback=StreamingStdOutCallbackHandler() if options.streaming else None,
        verbose=False
    )
    chat_history = []
    while True:
        print("What's your question?\n")
        user_input = input()
        resp = qh.get_chat_result(
            chat_history=chat_history,
            query=user_input,
            current_article_title=options.current_article_title
            )
        answer = resp['answer']
        sources = resp['sources']
        followups = resp['followup_questions']
        chat_history.append((user_input, answer))
        if not options.streaming:
            print("\n")
            print(answer)
            print()
        for i, source in enumerate(sources):
            print(f"[{i+1}]: Title: {source['title']} | URL: {source['url']}\n")
        if options.followups:
            print(f"Suggested Followups:\n{followups[:4]}")
