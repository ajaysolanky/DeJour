import os
import copy
import faiss
import pickle
import pandas as pd
from abc import ABC, abstractmethod
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.docstore.document import Document
from typing import Dict, List

import numpy as np

from weaviate_utils.weaviate_client import WeaviateClient

class VectorDB(ABC):
    def __init__(self, publisher) -> None:
        self.publisher = publisher

    @abstractmethod
    def add_texts(self, texts: List[str], metadatas: List[Dict]):
        pass

    @abstractmethod
    def get_k_closest_docs(self, query: str, k: int):
        pass

class VectorDBLocal(VectorDB):
    def __init__(self, publisher):
        super().__init__(publisher)
        self.store = None
        folder_name = ""
        self.index_file_name = folder_name + self.publisher.value + "_" + 'docs.index'
        self.store_file_name = folder_name + self.publisher.value + "_" + 'faiss_store.pkl'
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
    
    def add_texts(self, texts: List[str], metadatas: List[Dict]):
        new_ids = self.store.add_texts(
            texts,
            metadatas
            )
        self.save_db()
        return new_ids
    
    def get_k_closest_docs(self, query: str, k: int):
        embedding = self.get_embedding(query)
        _, indices = self.store.index.search(np.array([embedding], dtype=np.float32), k)
        docs = []
        for i in indices[0]:
            if i == -1:
                # This happens when not enough docs are returned.
                continue
            _id = self.store.index_to_docstore_id[i]
            doc = self.store.docstore.search(_id)
            if not isinstance(doc, Document):
                raise ValueError(f"Could not find document for id {_id}, got {doc}")
            docs.append(doc)
        return docs

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

class VectorDBWeaviate(VectorDB):
    def __init__(self, publisher) -> None:
        super().__init__(publisher)
        self.weaviate_client = WeaviateClient(self.publisher)
    
    def add_texts(self, texts: List[str], metadatas: List[Dict]):
        data = [md.update({'snippet': txt}) for txt, md in zip(texts, metadatas)]
        self.weaviate_client.upload_data(data)
    
    def get_k_closest_docs(self, query: str, k: int):
        results = self.weaviate_client.fetch_top_k_matches(query, k)
        docs = []
        for r in results:
            page_content = r.pop(self.weaviate_client.TEXT_FIELD_NAME)
            metadata = r
            docs.append(Document(
                page_content=page_content,
                metadata=metadata
            ))
        return docs