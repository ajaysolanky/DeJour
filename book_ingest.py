import time
import logging
import pandas as pd
from collections import defaultdict
from newspaper import Article
from datetime import datetime
import pytz
from abc import ABC, abstractmethod
from langchain.document_loaders import PagedPDFSplitter

from text_splitter import HardTokenSpacyTextSplitter
from utils import HiddenPrints, TokenCountCalculator, unstructured_time_string_to_structured, get_isoformat_and_add_tz_if_not_there
from weaviate_utils.weaviate_class import WeaviateClassBookSnippet
from weaviate_utils.weaviate_client import WeaviatePythonClient
from publisher_enum import PublisherEnum
from query import ChatQuery
from vector_db import VectorDBWeaviatePythonClient

CHUNK_SIZE_TOKENS = 300
CHUNK_OVERLAP_TOKENS = int(CHUNK_SIZE_TOKENS * .2)
SEPARATOR = '\n'
MIN_SPLIT_WORDS = 5
CRAWLER_SLEEP_SECONDS = 900
UPLOAD_BATCH_SIZE = 10

class BookDejour(object):
    def __init__(self, book_fname) -> None:
        self.book_fname = book_fname
        class_name_map = {
            "heart_of_darkness.pdf": PublisherEnum.BOOK_HEART_OF_DARKNESS_PDF.value,
            "lotr.pdf": PublisherEnum.BOOK_LOTR_PDF.value
        }
        class_name = class_name_map[book_fname]

        self.vector_db = VectorDBWeaviatePythonClient({"weaviate_class": WeaviateClassBookSnippet(class_name)})

    def upload_book(self):
        text_splitter = HardTokenSpacyTextSplitter(
            TokenCountCalculator().get_num_tokens,
            chunk_size=CHUNK_SIZE_TOKENS,
            chunk_overlap=CHUNK_OVERLAP_TOKENS,
            separator=SEPARATOR
            )

        loader = PagedPDFSplitter(f"./books/{self.book_fname}")
        docs = loader.load_and_split(text_splitter=text_splitter)

        texts = []
        metadatas = []
        idx = 0
        prev_page = None
        for doc in docs:
            page = doc.metadata['page']
            if page == prev_page:
                idx = 0
            else:
                idx += 1
            prev_page = page

            texts.append(doc.page_content)
            metadatas.append({
                "source": str(page),
                "idx": idx
            })

        self.vector_db.add_texts(texts, metadatas)

    # def retrieve_docs(self, query, k):
    #     return self.weaviate_client.fetch_top_k_matches(query, k)



if __name__ == '__main__':
    hod_dj = BookDejour('lotr.pdf')
    hod_dj.upload_book()

    # chat_query = ChatQuery(
    #     hod_dj.vector_db,
    #     )
    
    # chat_history = []
    # while True:
    #     print("What is your question?")
    #     query = input()
    #     resp = chat_query.answer_query_with_context(chat_history, query, None)
    #     chat_history += [(query, resp['answer'])]
    #     print(resp['answer'])
