import re
import json
import openai
import numpy as np
from langchain import OpenAI
from langchain.chains import LLMChain
from langchain.docstore.document import Document
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.chat_vector_db.prompts import PromptTemplate

from chains.dejour_stuff_documents_chain import DejourStuffDocumentsChain
from utils import TokenCountCalculator

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
        self.chain = ConversationalRetrievalChain(
            retriever=self.vector_db.store.as_retriever(),
            question_generator=question_generator,
            combine_docs_chain=doc_chain,
            return_source_documents=True,
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
        chain_resp = self.chain({
            "question": query,
            "chat_history": chat_history
        })
        answer_and_src_idces = chain_resp['answer']
        source_docs = chain_resp['source_documents']
        src_identifier = "SOURCES:"
        try:
            src_idx = answer_and_src_idces.lower().index(src_identifier.lower())
        except: #ValueError
            src_idx = None
        if src_idx:
            answer = answer_and_src_idces[:src_idx]
            src_str = answer_and_src_idces[src_idx + len(src_identifier):]
            def extract_idx(idx_str):
                #TODO: move this somewhere central and consolidate w/ the code in dejour_stuff_documents_chain.py
                idx_pattern = r'^\[(\d+)\]$'
                result = re.match(idx_pattern, idx_str)
                if result:
                    try:
                        return int(result.group(1))
                    except:
                        pass
                return None

            source_idces = [extract_idx(s.strip()) for s in src_str.split(',')]
            source_idces = list(filter(lambda x: x is not None, source_idces))
        else:
            answer = answer_and_src_idces
            source_idces = []
        source_idx_dict = dict(enumerate(source_docs))
        source_docs = [source_idx_dict.get(idx) for idx in source_idces]
        source_docs = list(filter(lambda x: x is not None, source_docs))
        source_urls = [d.metadata.get('source') for d in source_docs]
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
        return self.vector_db.get_k_closest_docs(query, k)

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