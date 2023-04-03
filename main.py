# TODO: same article can be pulled twice in the same "new_news_df" df from diff sources
# TODO: safeguard against same vector getting added twice
# TODO: clean out muck from photo captions and other random garbage
# TODO: same text chunk is getting added twice
# TODO: delete old news
# TODO: try SpacyTextSplitter
# TODO: are there race conditions with the vector store?
# TODO: exponentially decay old answers
# TODO: experiment with chunk overlap

import copy
import json
import os
import threading
from datetime import datetime
import pandas as pd
import faiss
import openai
from langchain import OpenAI
from langchain.chains import VectorDBQAWithSourcesChain
from langchain.chains import ConversationalRetrievalChain
from langchain.embeddings import OpenAIEmbeddings
from langchain.docstore.document import Document
from langchain.chains.chat_vector_db.prompts import PromptTemplate#, CONDENSE_QUESTION_PROMPT
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.chains import LLMChain
import pickle
from langchain.vectorstores import FAISS
import time
import nltk
import numpy as np
import tiktoken
from chains.dejour_stuff_documents_chain import DejourStuffDocumentsChain

# from embeddings_model import EmbeddingsModel
from utils import TokenCountCalculator
from news_db import NewsDB

nltk.download('punkt')
openai.api_key = os.getenv('OAI_TK', 'not the token')

class Runner(object):
    CRAWLER_SLEEP_SECONDS = 60 * 15
    def __init__(self, crawler, crawler_prefix):
        self.vector_db = VectorDB(crawler_prefix)
        self.news_db = NewsDB(crawler_prefix)
        self.mq = ManualQuery(self.vector_db, self.news_db)
        self.crawler = crawler(
            self.vector_db,
            self.news_db
            )
        self.chain = VectorDBQAWithSourcesChain.from_llm(
            llm=OpenAI(temperature=0),
            vectorstore=self.vector_db.store
            )
        self.cq = ChatQuery(self.vector_db, self.news_db)

    def run_crawler(self):
        while True:
            self.crawler.full_update()
            print(f"{str(datetime.now())}\nCrawl complete. Sleeping for {self.CRAWLER_SLEEP_SECONDS} seconds. Time: {datetime.now()}")
            time.sleep(self.CRAWLER_SLEEP_SECONDS)

    def get_result_langchain(self, question):
        return self.chain({"question": question})
    
    def get_result_manual(self, question):
        return self.mq.answer_query_with_context(question)

    def run_query_thread(self):
        while True:
            print('What is your question?')
            question = input()
            # result = self.get_result_langchain(question)
            result = self.get_result_manual(question)
            # result = self.chain({"question": question})
            source_str = "\n".join(result['sources'])
            output = f"\nAnswer: {result['answer']}\n\nSources: {source_str}"
            print(output)
    
    def get_chat_result(self, chat_history, query):
        return self.cq.answer_query_with_context(chat_history, query)

class Query:
    SOURCE_FIELD_DB_MAP = {
        'title': lambda r: r.title,
        'top_image_url': lambda r: r.top_image_url,
        'preview': lambda r: r.text[:1000] if r.text else '',
        'url': lambda r: r.url
    }
    SOURCE_FIELDS = ['title', 'top_image_url', 'url', 'text']
    def return_answer_with_src_data(self, answer, source_urls):
        sources_df = self.news_db.get_news_data(source_urls, self.SOURCE_FIELDS)
        return {
            "answer": answer,
            "sources": [{k:v(row) for k,v in self.SOURCE_FIELD_DB_MAP.items()} for i, row in sources_df.iterrows()]
        }

class ChatQuery(Query):
    CHAT_MODEL_CONDENSE_QUESTION = 'gpt-3.5-turbo'
    CHAT_MODEL_ANSWER_QUESTION = 'gpt-3.5-turbo'

    def __init__(self, vector_db, news_db) -> None:
        self.vector_db = vector_db
        self.news_db = news_db
        self.condense_question_prompt = self.load_prompt_from_json('./prompts/condense_question_prompt.json')
        self.answer_question_prompt = self.load_prompt_from_json('./prompts/answer_question_prompt.json')
        self.document_prompt = self.load_prompt_from_json('./prompts/document_prompt.json')
        condense_llm = OpenAI(temperature=0, model_name=self.CHAT_MODEL_CONDENSE_QUESTION)
        answer_llm = OpenAI(temperature=0, model_name=self.CHAT_MODEL_ANSWER_QUESTION)
        question_generator = LLMChain(llm=condense_llm, prompt=self.condense_question_prompt, verbose=True)
        doc_chain = DejourStuffDocumentsChain(
            llm_chain=LLMChain(llm=answer_llm, prompt=self.answer_question_prompt, verbose=True),
            document_variable_name="summaries",
            document_prompt=self.document_prompt,
            verbose=True
        )
        # doc_chain = load_qa_with_sources_chain(
        #     answer_llm,
        #     chain_type="stuff",
        #     prompt=self.answer_question_prompt,
        #     document_prompt=self.document_prompt,
        #     verbose=True)
        self.chain = ConversationalRetrievalChain(
            retriever=self.vector_db.store.as_retriever(),
            question_generator=question_generator,
            combine_docs_chain=doc_chain,
            verbose=True
        )

    @staticmethod
    def load_prompt_from_json(fpath):
        with open(fpath) as f:
            return PromptTemplate.from_template(json.load(f)['template'])

    def answer_query_with_context(self, chat_history, query):
        """
        inputs:
        chat_history: [(<question1:str>, <answer1:str>), (<question2:str>, <answer2:str>), ...]
        query: <str>
        returns: (<answer:str>, [<src1:str>, <src2:str>, ...])
        """
        answer_and_src = self.chain({
            "question": query,
            "chat_history": chat_history
        })['answer']
        src_identifiers = ["SOURCES:", "Sources:"]
        for src_identifier in src_identifiers:
            try:
                src_idx = answer_and_src.index(src_identifier)
                break
            except: #ValueError
                src_idx = None
        if src_idx:
            answer = answer_and_src[:src_idx]
            src_str = answer_and_src[src_idx + len(src_identifier):]
            source_urls = [s.strip() for s in src_str.split(',')]
        else:
            answer = answer_and_src
            source_urls = []
        return self.return_answer_with_src_data(answer, list(set(source_urls)))

#TODO: use Query parent class
class ManualQuery(object):
    SEPARATOR = "\n* "
    MAX_SECTION_LEN = 1000
    MAX_RESPONSE_TOKENS = 300
    COMPLETIONS_MODEL = "text-davinci-003"
    CHAT_MODEL = "gpt-4"
    COMPLETIONS_API_PARAMS = {
        # We use temperature of 0.0 because it gives the most predictable, factual answer.
        "temperature": 0.0,
        "max_tokens": MAX_RESPONSE_TOKENS,
        "model": COMPLETIONS_MODEL,
    }
    CHAT_API_PARAMS = {
        "temperature": 0.0,
        "max_tokens": MAX_RESPONSE_TOKENS,
        "model": CHAT_MODEL
    }

    def __init__(self, vector_db, news_db):
        self.vector_db = vector_db
        self.news_db = news_db
        self.get_num_tokens = TokenCountCalculator().get_num_tokens
        self.separator_len = self.get_num_tokens(self.SEPARATOR)

    def get_top_docs(self, query, k=10):
        # I think the first arg is distances
        embedding = self.vector_db.get_embedding(query)
        _, indices = self.vector_db.store.index.search(np.array([embedding], dtype=np.float32), k)
        docs = []
        for i in indices[0]:
            if i == -1:
                # This happens when not enough docs are returned.
                continue
            _id = self.vector_db.store.index_to_docstore_id[i]
            doc = self.vector_db.store.docstore.search(_id)
            if not isinstance(doc, Document):
                raise ValueError(f"Could not find document for id {_id}, got {doc}")
            docs.append(doc)
        return docs

    def construct_prompt(self, query):
        """
        Fetch relevant 
        """        
        most_relevant_docs = self.get_top_docs(query)

        chosen_sections = []
        chosen_sections_sources = []
        chosen_sections_len = 0
        for doc in most_relevant_docs:
            # Add contexts until we run out of space.        
            doc_text = doc.page_content
            doc_metadata = doc.metadata
            
            # TODO: preprocess and store num tokens so we don't have to redo this every time
            chosen_sections_len += self.get_num_tokens(doc_text) + self.separator_len
            if chosen_sections_len > self.MAX_SECTION_LEN:
                break
                
            chosen_sections.append(self.SEPARATOR + doc_text.replace("\n", " "))
            chosen_sections_sources.append(doc_metadata['source'])
                
        # # Useful diagnostic information
        # print(f"Selected {len(chosen_sections)} document sections:")
        
        # header = """Answer the question as truthfully as possible using the provided context, and if the answer is not contained within the text below, say "I don't know."\n\nContext:\n"""
        header = """Answer the question as truthfully as possible using the provided context, and if the answer is not contained within the text below, say "I don't know." Do not reference the fact that you have been provided with context.\n\nContext:\n"""
        
        return (
            header + "".join(chosen_sections) + "\n\n Q: " + query + "\n A:",
            chosen_sections_sources
        )

    def answer_with_openai_completions(self, prompt):
        response = openai.Completion.create(
            prompt=prompt,
            **self.COMPLETIONS_API_PARAMS
            )
        return response["choices"][0]["text"].strip(" \n")
    
    def answer_with_openai_chat(self, prompt):
        response = openai.ChatCompletion.create(
            messages=[
                {"role": "system", "content": "You are an AI assistant that answers questions about the news truthfully."},
                {"role": "user", "content": prompt}
            ],
            **self.CHAT_API_PARAMS
        )
        return response['choices'][0]['message']['content']

    def answer_query_with_context(self, query, noisy=True):
        prompt, source_urls = self.construct_prompt(query)
        sources_df = self.news_db.get_news_data(source_urls, ['title', 'top_image_url', 'url', 'text'])
        if noisy:
            print(f"prompt:\n\n{prompt}\n\n")
        answer = self.answer_with_openai_chat(prompt)
        source_li = [
            {
                "title": row.title,
                "top_image_url": row.top_image_url,
                "preview": row.text[:1000] if row.text else '',
                "url": row.url
            }
            for i, row in sources_df.iterrows()
        ]
        return {
            "answer": answer,
            "sources": source_li
        }

class VectorDB:
    def __init__(self, file_name_prefix):
        self.store = None
        folder_name = ""
        self.index_file_name = folder_name + file_name_prefix + "_" + 'docs.index'
        self.store_file_name = folder_name + file_name_prefix + "_" + 'faiss_store.pkl'
        if not os.path.isfile(self.index_file_name):
            init_store = FAISS.from_texts(['test'], OpenAIEmbeddings(), metadatas=[{"source":'test'}])
            self.save_db(init_store)
        self.load_db()

    def load_db(self):
        index = faiss.read_index(self.index_file_name)
        with open(self.store_file_name, "rb") as f:
            store = pickle.load(f)
            store.index = index
        self.store = store
    
    def add_texts(self, texts, metadatas):
        new_ids = self.store.add_texts(
            texts,
            metadatas
            )
        self.save_db()
        return new_ids
    
    def get_embedding(self, text):
        return self.store.embedding_function(text)

    def save_db(self, store_obj=None):
        if not store_obj:
            store_obj = self.store
        faiss.write_index(store_obj.index, self.index_file_name)
        store_copy = copy.deepcopy(store_obj)
        store_copy.index = None
        with open(self.store_file_name, 'wb') as f:
            pickle.dump(store_copy, f)
