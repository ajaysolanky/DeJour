from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from langchain.chains import ChatVectorDBChain
from langchain.schema import BaseLanguageModel, BaseRetriever, Document

class ChatVectorDBChainIntakeDocs(ChatVectorDBChain):
    @property
    def input_keys(self) -> List[str]:
        """Input keys."""
        return ["question", "chat_history", "source_documents"]

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        docs = inputs['source_documents']
        new_inputs = inputs.copy()
        answer, _ = self.combine_docs_chain.combine_docs(docs, **new_inputs)
        if self.return_source_documents:
            return {self.output_key: answer, "source_documents": docs}
        else:
            return {self.output_key: answer}
