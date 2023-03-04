import logging
logger = logging.getLogger()
import numpy as np
import cleantext
from typing import Any, Dict, List, Optional, Iterable
from langchain.text_splitter import TextSplitter, SpacyTextSplitter

logger = logging.getLogger()

# TODO: this could end up splitting words
class HardTokenSpacyTextSplitter(SpacyTextSplitter):
    def __init__(self, token_length_function, **kwargs) -> None:
        super().__init__(length_function=token_length_function, **kwargs)

    def split_text(self, text: str) -> List[str]:
        """Split incoming text and return chunks."""
        splits = (str(s) for s in self._tokenizer(text).sents)
        second_splits = []
        for i, split in enumerate(splits):
            if self._length_function(split) < self._chunk_size:
                second_splits.append(split)
            else:
                try:
                    # doing all this bs bc _length_function isn't necessarily just len()
                    num_splits = 2
                    while True:
                        if num_splits >= 10:
                            raise Exception("too long to split... something funky with this chunk")
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
                except Exception as e:
                    print(f"ERROR IN SPLITTING: {e}. FROM text: {split[:500]}. On split idx: {i}")
                    continue
        final_splits = [cleantext.clean(s) for s in second_splits]
        return self._merge_splits(final_splits, self._separator)
    
    # overrode this because the package version sometimes allows chunks to go over the limit
    def _merge_splits(self, splits: Iterable[str], separator: str) -> List[str]:
        # We now want to combine these smaller pieces into medium size
        # chunks to send to the LLM.
        separator_len = self._length_function(separator)

        docs = []
        current_doc: List[str] = []
        total = 0
        for d in splits:
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
