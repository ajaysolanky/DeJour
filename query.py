import re
import json
import threading
from langchain import OpenAI
from langchain.chains import LLMChain, ChatVectorDBChain
from langchain.chains.chat_vector_db.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI

from prompts.all_prompts import ANSWER_QUESTION_PROMPT, ANSWER_QUESTION_PROMPT_INLINE, CONDENSE_QUESTION_PROMPT, DOCUMENT_PROMPT, FOLLOWUP_Q_DOCUMENT_PROMPT
from chains.dejour_stuff_documents_chain import DejourStuffDocumentsChain
from chains.chat_vector_db_fetch_q_and_docs_chain import ChatVectorDBFetchQAndDocsChain
from chains.chat_vector_db_chain_intake_docs import ChatVectorDBChainIntakeDocs
from chains.question_extraction_chain import QuestionExtractionChain
from utils import split_text_into_sentences, extract_body_citations_punctuation_from_sentence, get_thread_for_fn

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

    def __init__(self, vector_db, inline=False, followups=False) -> None:
        self.inline = inline
        self.followups = followups
        self.vector_db = vector_db
        self.condense_question_prompt = PromptTemplate.from_template(CONDENSE_QUESTION_PROMPT)
        answer_question_prompt = ANSWER_QUESTION_PROMPT_INLINE if self.inline else ANSWER_QUESTION_PROMPT
        self.answer_question_prompt = PromptTemplate.from_template(answer_question_prompt)
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
        #TODO: these chains were very much hacked together and need cleaning up
        self.fetch_q_and_docs_chain = ChatVectorDBFetchQAndDocsChain(
            vectorstore=self.vector_db.get_vectorstore(),
            combine_docs_chain=doc_chain,
            question_generator=condense_question_chain,
            return_source_documents=True,
            verbose=True
        )
        self.question_extraction_chain = QuestionExtractionChain.from_llm(ChatOpenAI(temperature = 0))
        self.cvdb_chain = ChatVectorDBChainIntakeDocs(
            vectorstore=self.vector_db.get_vectorstore(),
            combine_docs_chain=doc_chain,
            question_generator=condense_question_chain,
            return_source_documents=True,
            verbose=True
        )

    def run_chain(self, chat_history, query):
        fetch_q_and_docs_resp = self.fetch_q_and_docs_chain({
            "question": query,
            "chat_history": chat_history
        })
        new_question = fetch_q_and_docs_resp['question']
        chat_history_str = fetch_q_and_docs_resp['chat_history']
        docs = fetch_q_and_docs_resp['source_documents']

        answer_thread, answer_resp = get_thread_for_fn(self.cvdb_chain, [fetch_q_and_docs_resp])
        answer_thread.start()

        if self.followups:
            followup_q_input_text = ''
            for d in docs:
                title = d.metadata['title']
                article_snippet = d.page_content
                followup_q_input_text += FOLLOWUP_Q_DOCUMENT_PROMPT.format(title=title, article_snippet=article_snippet)
                followup_q_input_text += '\n'

            
            followup_q_thread, followup_q_resp = get_thread_for_fn(self.question_extraction_chain.run, [followup_q_input_text])

            followup_q_thread.start()

        answer_thread.join()
        if self.followups:
            followup_q_thread.join()

        answer = answer_resp.get('response', {}).get('answer')
        followup_questions = followup_q_resp.get('response', [[]])[0] if self.followups else None

        return {
            "answer": answer,
            "source_documents": docs,
            "followup_questions": followup_questions
        }

    def answer_query_with_context(self, chat_history, query):
        if self.inline:
            return self.answer_query_with_context_inline_citation(chat_history, query)
        else:
            return self.answer_query_with_context_regular(chat_history, query)

    def answer_query_with_context_inline_citation(self, chat_history, query):
        """
        inputs:
        chat_history: [(<question1:str>, <answer1:str>), (<question2:str>, <answer2:str>), ...]
        query: <str>
        returns: (<answer:str>, [<src1:str>, <src2:str>, ...])
        """
        chain_resp = self.run_chain(chat_history, query)
        # chain_resp = self.chain({
        #     "question": query,
        #     "chat_history": chat_history
        # })
        answer_and_src_idces = chain_resp['answer']
        source_docs = chain_resp['source_documents']
        followup_qs = chain_resp['followup_questions']
        src_identifier = "SOURCES:"
        try:
            src_idx = answer_and_src_idces.lower().index(src_identifier.lower())
        except: #ValueError
            src_idx = None
        if src_idx:
            answer = answer_and_src_idces[:src_idx].strip()
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

            source_idces_one_indexed = [extract_idx(s.strip()) for s in src_str.split(',')]
            source_idces_one_indexed = list(filter(lambda x: x is not None, source_idces_one_indexed))
        else:
            answer = answer_and_src_idces
            source_idces_one_indexed = []

        # this incredibly convoluted line of code takes in a list of source docs, and outputs a map from src:unique id, where the unique id is one-indexed index of where the source first appears in the list
        doc_to_id_map = {src:idx + 1 for idx, (_, src) in enumerate(sorted(list({v:k for k, v in {d.metadata.get('source'): len(source_docs) - i for i, d in enumerate(source_docs[::-1])}.items()}.items())))}
        id_to_doc_map = {v: k for k, v in doc_to_id_map.items()}

        source_idx_to_id = {}
        for src_idx_plus_one in source_idces_one_indexed:
            src = source_docs[src_idx_plus_one - 1]
            source_idx_to_id.update({src_idx_plus_one: doc_to_id_map[src.metadata.get('source')]})

        for k, v in source_idx_to_id.items():
            answer = answer.replace(f"[{k}]", f"[{v}]")

        source_to_doc_map = {d.metadata.get('source'): d for d in source_docs}
        unique_source_docs = [source_to_doc_map[src] for src in [v for _,v in sorted(id_to_doc_map.items())]]

        sentences = split_text_into_sentences(answer)
        bcp = [extract_body_citations_punctuation_from_sentence(sentence) for sentence in sentences]

        constructed_answer = ''
        for i in range(len(bcp) - 1):
            cur_body, cur_citations, cur_punctuation = bcp[i]
            nex_body, nex_citations, nex_punctuation = bcp[i+1]
            constructed_answer += cur_body
            if cur_citations != nex_citations:
                constructed_answer += "".join([f"[{n}]" for n in cur_citations])
            constructed_answer += cur_punctuation + " "
        b, c, p = bcp[-1]
        constructed_answer += b + "".join([f"[{n}]" for n in c]) + p

        return {
            "answer": constructed_answer,
            "sources": [{prop:fn(d.metadata) for prop,fn in self.SOURCE_FIELD_DB_MAP.items()} for d in unique_source_docs],
            "followup_questions": followup_qs
        }

    def answer_query_with_context_regular(self, chat_history, query):
            """
            inputs:
            chat_history: [(<question1:str>, <answer1:str>), (<question2:str>, <answer2:str>), ...]
            query: <str>
            returns: (<answer:str>, [<src1:str>, <src2:str>, ...])
            """
            chain_resp = self.run_chain(chat_history, query)
            # chain_resp = self.chain({
            #     "question": query,
            #     "chat_history": chat_history
            # })
            answer_and_src_idces = chain_resp['answer']
            source_docs = chain_resp['source_documents']
            followup_qs = chain_resp['followup_questions']
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
                "sources": [{prop:fn(d.metadata) for prop,fn in self.SOURCE_FIELD_DB_MAP.items()} for d in source_docs],
                "followup_questions": followup_qs
            }