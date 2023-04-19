from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from langchain.chains import LLMChain, ChatVectorDBChain
from langchain.chains.conversational_retrieval.base import _get_chat_history

from prompts.all_prompts import CURRENT_ARTICLE_FETCH_DOCUMENT_PROMPT

class ChatVectorDBFetchQAndDocsChain(ChatVectorDBChain):
    @property
    def input_keys(self) -> List[str]:
        """Input keys."""
        return ["question", "chat_history", "article_title"]
    
    @property
    def output_keys(self) -> List[str]:
        """Return the output keys.

        :meta private:
        """
        return ["question", "source_documents", "chat_history"]

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        question = inputs["question"]
        get_chat_history = self.get_chat_history or _get_chat_history
        chat_history_str = get_chat_history(inputs["chat_history"])
        article_title = inputs["article_title"]

        if chat_history_str:
            new_question = self.question_generator.run(
                question=question, chat_history=chat_history_str
            )
        else:
            new_question = question

        if article_title:
            new_question = CURRENT_ARTICLE_FETCH_DOCUMENT_PROMPT.format(
                article_title=article_title,
                user_question=new_question
            )

        docs = self._get_docs(new_question, inputs)
        return {"question": new_question, "source_documents": docs, "chat_history": chat_history_str}
