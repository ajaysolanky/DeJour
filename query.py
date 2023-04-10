import re
import json
from langchain import OpenAI
from langchain.chains import LLMChain, ChatVectorDBChain
from langchain.chains.chat_vector_db.prompts import PromptTemplate

from prompts.all_prompts import ANSWER_QUESTION_PROMPT, CONDENSE_QUESTION_PROMPT, DOCUMENT_PROMPT
from chains.dejour_stuff_documents_chain import DejourStuffDocumentsChain

class Query:
    SOURCE_FIELD_DB_MAP = {
        'title': lambda r: r.get('title'),
        'top_image_url': lambda r: r.get('top_image_url'),
        'preview': lambda r: r.get('text','')[:1000],
        'url': lambda r: r.get('source')
    }

class ChatQuery(Query):
    CHAT_MODEL_CONDENSE_QUESTION = 'gpt-3.5-turbo'
    CHAT_MODEL_ANSWER_QUESTION = 'gpt-3.5-turbo'

    def __init__(self, vector_db) -> None:
        self.vector_db = vector_db
        self.condense_question_prompt = PromptTemplate.from_template(CONDENSE_QUESTION_PROMPT)
        self.answer_question_prompt = PromptTemplate.from_template(ANSWER_QUESTION_PROMPT)
        self.document_prompt = PromptTemplate.from_template(DOCUMENT_PROMPT)
        condense_llm = OpenAI(temperature=0, model_name=self.CHAT_MODEL_CONDENSE_QUESTION)
        answer_llm = OpenAI(temperature=0, model_name=self.CHAT_MODEL_ANSWER_QUESTION)
        condense_question_chain = LLMChain(llm=condense_llm, prompt=self.condense_question_prompt, verbose=True)
        doc_chain = DejourStuffDocumentsChain(
            llm_chain=LLMChain(llm=answer_llm, prompt=self.answer_question_prompt, verbose=True),
            document_variable_name="summaries",
            document_prompt=self.document_prompt,
            verbose=True
        )
        self.chain = ChatVectorDBChain(
            vectorstore=self.vector_db.get_vectorstore(),
            combine_docs_chain=doc_chain,
            question_generator=condense_question_chain,
            return_source_documents=True,
            verbose=True
        )

    def answer_query_with_context(self, chat_history, query):
        """
        inputs:
        chat_history: [(<question1:str>, <answer1:str>), (<question2:str>, <answer2:str>), ...]
        query: <str>
        returns: (<answer:str>, [<src1:str>, <src2:str>, ...])
        """
        chat_history_mapped = []
        for chat in chat_history:
            chat_history_mapped.append((chat['question'], chat['answer']))
        chain_resp = self.chain({
            "question": query,
            "chat_history": chat_history_mapped
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
        source_docs = {d.metadata.get('source'):d for d in source_docs}.values() #de-dupe by source
        return {
            "answer": answer,
            "sources": [{prop:fn(d.metadata) for prop,fn in self.SOURCE_FIELD_DB_MAP.items()} for d in source_docs]
        }
