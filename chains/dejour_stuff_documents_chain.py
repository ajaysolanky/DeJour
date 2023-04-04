from typing import Any, Dict, List, Optional, Tuple
from langchain.docstore.document import Document

from langchain.chains.combine_documents.stuff import StuffDocumentsChain

from utils import get_current_structured_time_string

class DejourStuffDocumentsChain(StuffDocumentsChain):
    #things I've changed: (A) it doesn't just commit suicide if a field is missing (B) it adds today's date as an input (C) uses index as source
    def _get_inputs(self, docs: List[Document], **kwargs: Any) -> dict:
        # Get relevant information from each document.
        doc_dicts = []
        for i, doc in enumerate(docs):
            base_info = {"page_content": doc.page_content}
            base_info.update(doc.metadata)
            base_info['source'] = f"[{i}]"
            document_info = {
                k: base_info.get(k,'UNKNOWN') for k in self.document_prompt.input_variables
            }
            doc_dicts.append(document_info)
        # Format each document according to the prompt
        doc_strings = [self.document_prompt.format(**doc) for doc in doc_dicts]
        # Join the documents together to put them in the prompt.
        inputs = {
            k: v
            for k, v in kwargs.items()
            if k in self.llm_chain.prompt.input_variables
        }
        inputs[self.document_variable_name] = "\n\n".join(doc_strings)
        inputs['today_date'] = get_current_structured_time_string()
        return inputs