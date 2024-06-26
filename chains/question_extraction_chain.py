from __future__ import annotations

from langchain.chains import QAGenerationChain
from langchain.chains.base import Chain
from langchain.chains.llm import LLMChain
from langchain.prompts.base import BasePromptTemplate
from langchain.schema import BaseLanguageModel
from langchain.text_splitter import RecursiveCharacterTextSplitter, TextSplitter
from pydantic import Field
import json
from typing import Any, Dict, List, Optional
from langchain.prompts.prompt import PromptTemplate

from prompts.all_prompts import QUESTION_EXTRACTION_PROMPT

class QuestionExtractionChain(Chain):
    llm_chain: LLMChain
    text_splitter: TextSplitter = Field(
        default=RecursiveCharacterTextSplitter(chunk_overlap=500)
    )
    input_key: str = "text"
    output_key: str = "questions"
    k: Optional[int] = None

    @classmethod
    def from_llm(
        cls,
        llm: BaseLanguageModel,
        prompt: Optional[BasePromptTemplate] = None,
        **kwargs: Any,
    ) -> QuestionExtractionChain:
        _prompt = PromptTemplate.from_template(QUESTION_EXTRACTION_PROMPT)
        chain = LLMChain(llm=llm, prompt=_prompt)
        return cls(llm_chain=chain, **kwargs)

    @property
    def _chain_type(self) -> str:
        raise NotImplementedError

    @property
    def input_keys(self) -> List[str]:
        return [self.input_key]

    @property
    def output_keys(self) -> List[str]:
        return [self.output_key]

    def _call(self, inputs: Dict[str, str]) -> Dict[str, Any]:
        docs = self.text_splitter.create_documents([inputs[self.input_key]])
        #TODO: discarding everything after docs[0]
        docs = docs[:1]
        results = self.llm_chain.generate([{"text": d.page_content} for d in docs])
        qa = [json.loads(res[0].text) for res in results.generations]
        return {self.output_key: qa}

    async def _acall(self, inputs: Dict[str, str]) -> Dict[str, str]:
        raise NotImplementedError
