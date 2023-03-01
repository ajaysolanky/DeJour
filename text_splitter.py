import logging
logger = logging.getLogger()
import numpy as np
import cleantext
from typing import Any, Dict, List, Optional, Iterable
from langchain.text_splitter import TextSplitter, SpacyTextSplitter

logger = logging.getLogger()

# class HardTokenSpacyTextSplitter(TextSplitter):
#     """Implementation of splitting text that looks at sentences using Spacy.
#     Having issues with the package version, hence I just am overriding code here.
#     """

#     def __init__(
#         self, token_length_function, separator: str = "\n\n", pipeline: str = "en_core_web_sm", **kwargs: Any
#     ):
#         """Initialize the spacy text splitter."""
#         super().__init__(length_function=token_length_function, **kwargs)
#         try:
#             import spacy
#         except ImportError:
#             raise ImportError(
#                 "Spacy is not installed, please install it with `pip install spacy`."
#             )
#         # I had to run this: https://stackoverflow.com/questions/54334304/spacy-cant-find-model-en-core-web-sm-on-windows-10-and-python-3-5-3-anacon
#         self._tokenizer = spacy.load(pipeline)
#         self._separator = separator
#         assert self._chunk_overlap < self._chunk_size, "overlap shouldn't be greater than chunk size"

#     def split_text(self, text: str) -> List[str]:
#         """Split incoming text and return chunks."""
#         splits = [str(s) for s in self._tokenizer(text).sents]
#         second_splits = []
#         for split in splits:
#             if self._length_function(split) < self._chunk_size:
#                 second_splits.append(split)
#             else:
#                 # doing all this bs bc _length_function isn't necessarily just len()
#                 num_splits = 2
#                 while True:
#                     sub_chunks = np.array_split(np.array(list(split)), num_splits)
#                     all_shorter = all([
#                         self._length_function(sc) <= self._chunk_size
#                         for sc in sub_chunks 
#                     ])
#                     if all_shorter:
#                         break
#                 second_splits.extend(sub_chunks)
#         final_splits = [cleantext.clean(s) for s in second_splits]
#         return self._merge_splits(final_splits)

    # def _merge_splits(self, splits: Iterable[str], separator: str) -> List[str]:
    #     # We now want to combine these smaller pieces into medium size
    #     # chunks to send to the LLM.
    #     docs = []
    #     current_doc: List[str] = []
    #     total = 0
    #     for d in splits:
    #         _len = self._length_function(d)
    #         if total + _len >= self._chunk_size:
    #             if total > self._chunk_size:
    #                 logger.warning(
    #                     f"Created a chunk of size {total}, "
    #                     f"which is longer than the specified {self._chunk_size}"
    #                 )
    #             if len(current_doc) > 0:
    #                 doc = self._join_docs(current_doc, separator)
    #                 if doc is not None:
    #                     docs.append(doc)
    #                 # Keep on popping if:
    #                 # - we have a larger chunk than in the chunk overlap
    #                 # - or if we still have any chunks and the length is long
    #                 while total > self._chunk_overlap or (
    #                     total + _len > self._chunk_size and total > 0
    #                 ):
    #                     total -= self._length_function(current_doc[0])
    #                     current_doc = current_doc[1:]
    #         current_doc.append(d)
    #         total += _len
    #     doc = self._join_docs(current_doc, separator)
    #     if doc is not None:
    #         docs.append(doc)
    #     return docs

    # def _merge_splits(self, splits: Iterable[str]) -> List[str]:
    #     # We now want to combine these smaller pieces into medium size
    #     # chunks to send to the LLM.
    #     docs = []
    #     current_doc: List[str] = []
    #     total = 0
    #     for i, d in enumerate(splits):
    #         if i == 55:
    #             import pdb; pdb.set_trace()
    #         _len = self._length_function(d)
    #         if total + _len >= self._chunk_size:
    #             if _len > self.chunk_size:
    #                 raise Exception(f"Text fragment is of size {total}, "
    #                                 f"which is longer than the specified {self._chunk_size}")
    #             if total > self._chunk_size:
    #                 raise Exception(
    #                     f"current doc size {total}, "
    #                     f"which is longer than the specified {self._chunk_size}"
    #                 )
    #             assert len(current_doc) > 0, "this should be true, there's a bug if it's not"
    #             docs.append(self._separator.join(current_doc))
    #             while total > self._chunk_overlap:
    #                 total -= self._length_function(current_doc[0])
    #                 current_doc = current_doc[1:]
    #         current_doc.append(d)
    #         total += _len
    #     docs.append(self._separator.join(current_doc))
    #     return docs


# TODO: this could end up splitting words
class HardTokenSpacyTextSplitter(SpacyTextSplitter):
    def __init__(self, token_length_function, **kwargs) -> None:
        super().__init__(length_function=token_length_function, **kwargs)

    def split_text(self, text: str) -> List[str]:
        """Split incoming text and return chunks."""
        splits = (str(s) for s in self._tokenizer(text).sents)
        second_splits = []
        for split in splits:
            if self._length_function(split) < self._chunk_size:
                second_splits.append(split)
            else:
                # doing all this bs bc _length_function isn't necessarily just len()
                num_splits = 2
                while True:
                    if num_splits >= 20:
                        raise Exception("something funky with this chunk")
                    sub_chunks = np.array_split(np.array(split.split(" ")), num_splits)
                    sub_chunks = [" ".join(sc) for sc in sub_chunks]
                    all_shorter = all([
                        self._length_function(sc) <= self._chunk_size
                        for sc in sub_chunks 
                    ])
                    if all_shorter:
                        break
                    num_splits += 1
                second_splits.extend(sub_chunks)
        final_splits = [cleantext.clean(s) for s in second_splits]
        return self._merge_splits(final_splits, self._separator)
    
    def _merge_splits(self, splits: Iterable[str], separator: str) -> List[str]:
        # We now want to combine these smaller pieces into medium size
        # chunks to send to the LLM.
        separator_len = self._length_function(separator)

        docs = []
        current_doc: List[str] = []
        total = 0
        for i, d in enumerate(splits):
            calced = sum(self._length_function(d) for d in current_doc) + separator_len * (max([len(current_doc) - 1, 0]))
            # print(f"i: {i} total: {total} , calc: {calced}")
            # if calced != total:
            #     import pdb; pdb.set_trace()
            # if i == 56:
            #     import pdb; pdb.set_trace()
            _len = self._length_function(d)
            if total + _len + (separator_len if len(current_doc) > 0 else 0) >= self._chunk_size:
                if total > self._chunk_size:
                    logger.warning(
                        f"Created a chunk of size {total}, "
                        f"which is longer than the specified {self._chunk_size}"
                    )
                if len(current_doc) > 0:
                    doc = self._join_docs(current_doc, separator)
                    if doc is not None:
                        docs.append(doc)
                    # Keep on popping if:
                    # - we have a larger chunk than in the chunk overlap
                    # - or if we still have any chunks and the length is long
                    while total > self._chunk_overlap or (
                        total + _len + (separator_len if len(current_doc) > 0 else 0) > self._chunk_size and total > 0
                    ):
                        total -= self._length_function(current_doc[0]) + (separator_len if len(current_doc) > 1 else 0)
                        current_doc = current_doc[1:]
            current_doc.append(d)
            total += _len + (separator_len if len(current_doc) > 1 else 0)
        doc = self._join_docs(current_doc, separator)
        if doc is not None:
            docs.append(doc)
        return docs
