#TODO: severely mucked this up, needs to be cleaned up

import os
import copy
import faiss
import pickle
from abc import ABC, abstractmethod
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.docstore.document import Document
from typing import Dict, List
from langchain.vectorstores.weaviate import Weaviate
import numpy as np
from typing import Any, Dict, Iterable, List, Optional
from langchain.vectorstores.base import VectorStore
from langchain.embeddings.base import Embeddings
import datetime
import pytz
import requests

from weaviate_utils.weaviate_client import WeaviatePythonClient, WeaviateCURL
from utils import LOCAL_DB_FOLDER

class VectorDB(ABC):
    def __init__(self, args) -> None:
        pass

    @abstractmethod
    def add_texts(self, texts: List[str], metadatas: List[Dict]):
        pass

    @abstractmethod
    def get_k_closest_docs(self, query: str, k: int, filters: dict[str, list[str]] = {}):
        pass
    
    @abstractmethod
    def get_vectorstore(self):
        pass

    @abstractmethod
    def dump_old_data(self, cutoff_threshold_hours : int):
        pass

class CustomFAISS(FAISS):
    def similarity_search(
        self, query: str, k: int = 4, **kwargs: Any
    ) -> List[Document]:
        """Return docs most similar to query.

        Args:
            query: Text to look up documents similar to.
            k: Number of Documents to return. Defaults to 4.

        Returns:
            List of Documents most similar to the query.
        """
        filters = kwargs.get('filters', {})
        if filters:
            k_expanded = k * 5 # faiss doesn't let you apply a filter, so as a hack I'm expanding the search 5x and then filtering after
        else:
            k_expanded = k

        docs_and_scores = self.similarity_search_with_score(query, k_expanded)
        #TODO: test this code
        doc_ids_to_be_filtered = set()
        for i, (d, _) in enumerate(docs_and_scores):
            for field, (operator, val) in filters.items():
                doc_val = d.metadata.get(field)
                # https://weaviate.io/developers/weaviate/api/graphql/filters#filter-structure
                if operator == 'GreaterThan':
                    comp = lambda x, y: x > y
                elif operator == 'LessThan':
                    comp = lambda x, y: x < y
                elif operator == 'Equal':
                    comp = lambda x, y: x == y
                elif operator == 'NotEqual':
                    comp = lambda x, y: x != y
                else:
                    raise NotImplementedError()
                if not comp(doc_val, val):
                    doc_ids_to_be_filtered.add(i)
        filter_out_indices = lambda lst, indices: [item for i, item in enumerate(lst) if i not in indices]
        final_docs = [d for d, _ in filter_out_indices(docs_and_scores, doc_ids_to_be_filtered)]
        return final_docs[:k]

class VectorDBLocal(VectorDB):
    def __init__(self, args):
        super().__init__(args)
        self.store = None
        dir_path = f"{LOCAL_DB_FOLDER}/{args['publisher_name']}/vector_db/"
        self.index_file_path = dir_path + 'docs.index'
        self.store_file_path = dir_path + 'faiss_store.pkl'
        if not os.path.isfile(self.index_file_path):
            os.makedirs(os.path.dirname(self.index_file_path))
            with open(self.index_file_path, 'w') as f:
                f.write('')
            with open(self.store_file_path, 'w') as f:
                f.write('')
            init_store = CustomFAISS.from_texts(['test'], OpenAIEmbeddings(), metadatas=[{"source":'test'}])
            self.save_db(init_store)
        self.load_db()

    def get_vectorstore(self):
        return self.store

    def load_db(self):
        index = faiss.read_index(self.index_file_path)
        with open(self.store_file_path, "rb") as f:
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

    #TODO: deprecate this code, it's not used
    def get_k_closest_docs(self, query: str, k: int, filters: dict[str, list[str]] = {}):
        embedding = self.get_embedding(query)
        # faiss doesn't let you apply a filter, so as a hack I'm expanding the search 5x and then filtering after
        full_k = k * 5
        _, indices = self.store.index.search(np.array([embedding], dtype=np.float32), full_k)
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
        
        #TODO: test this code
        docs_to_be_filtered = set()
        for d in docs:
            for field, (operator, val) in filters.items():
                doc_val = d.metadata[field]
                # https://weaviate.io/developers/weaviate/api/graphql/filters#filter-structure
                if operator == 'GreaterThan':
                    comp = lambda x, y: x > y
                elif operator == 'LessThan':
                    comp = lambda x, y: x < y
                elif operator == 'Equal':
                    comp = lambda x, y: x == y
                elif operator == 'NotEqual':
                    comp = lambda x, y: x != y
                else:
                    raise NotImplementedError()
                if not comp(field, val):
                    docs_to_be_filtered.add(d)
        final_docs = [d for d in docs if d not in docs_to_be_filtered]
        return final_docs

    def get_embedding(self, text):
        return self.store.embedding_function(text)

    def save_db(self, store_obj=None):
        if not store_obj:
            store_obj = self.store
        faiss.write_index(store_obj.index, self.index_file_path)
        store_copy = copy.deepcopy(store_obj)
        store_copy.index = None
        with open(self.store_file_path, 'wb') as f:
            pickle.dump(store_copy, f)

    def dump_old_data(self, cutoff_threshold_hours : int):
        print("Haven't implemented dump old data for local vector db")

class VectorDBWeaviate(VectorDB, ABC):
    def __init__(self, args) -> None:
        super().__init__(args)
    
    @abstractmethod
    def get_vectorstore(self):
        pass

    def add_texts(self, texts: List[str], metadatas: List[Dict]):
        data = [md | {self.weaviate_service.text_field_name: txt}  for txt, md in zip(texts, metadatas)]
        new_ids = self.weaviate_service.upload_data(data)
        return new_ids
    
    def get_k_closest_docs(self, query: str, k: int, filters: dict[str, list[str]] = {}):
        results = self.weaviate_service.fetch_top_k_matches(query, k, filters)
        docs = []
        for r in results:
            page_content = r.pop(self.weaviate_service.text_field_name)
            metadata = r
            docs.append(Document(
                page_content=page_content,
                metadata=metadata
            ))
        return docs
    
    def dump_old_data(self, cutoff_threshold_hours : int):
        self.weaviate_service.dump_old_data(cutoff_threshold_hours)

    def delete_class(self):
        self.weaviate_service.delete_class()
    
class VectorDBWeaviatePythonClient(VectorDBWeaviate):
    def __init__(self, args) -> None:
        super().__init__(args)
        self.weaviate_service = WeaviatePythonClient(args['weaviate_class'])

    def get_vectorstore(self):
        return Weaviate(self.weaviate_service.client, self.weaviate_service.class_name, self.weaviate_service.text_field_name)
    
class VectorDBWeaviateCURL(VectorDBWeaviate):
    def __init__(self, args) -> None:
        super().__init__(args)
        self.weaviate_service = WeaviateCURL(args["weaviate_class"])

    def get_vectorstore(self):
        return WeaviateVectorStoreCURL(
            self,
            self.weaviate_service.class_name,
            self.weaviate_service.text_field_name
        )

class WeaviateVectorStoreCURL(VectorStore):
    """Wrapper around Weaviate vector database.

    To use, you should have the ``weaviate-client`` python package installed.

    Example:
        .. code-block:: python

            import weaviate
            from langchain.vectorstores import Weaviate
            client = weaviate.Client(url=os.environ["WEAVIATE_URL"], ...)
            weaviate = Weaviate(client, index_name, text_key)

    """

    def __init__(
        self,
        curl_client: Any,
        index_name: str,
        text_key: str,
        attributes: Optional[List[str]] = None,
    ):
        """Initialize with Weaviate client."""
        try:
            import weaviate
        except ImportError:
            raise ValueError(
                "Could not import weaviate python package. "
                "Please install it with `pip install weaviate-client`."
            )
        self._curl_client = curl_client
        self._index_name = index_name
        self._text_key = text_key
        self._query_attrs = [self._text_key]
        if attributes is not None:
            self._query_attrs.extend(attributes)
    
    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        **kwargs: Any,
    ) -> List[str]:
        """Upload texts with metadata (properties) to Weaviate."""
        return self._curl_client.add_texts(texts, metadatas)

    def similarity_search(
        self, query: str, k: int = 4, **kwargs: Any
    ) -> List[Document]:
        filters = kwargs.get('filters')
        return self._curl_client.get_k_closest_docs(query, k, filters)

    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[dict]] = None,
        **kwargs: Any,
    ) -> VectorStore:
        """Not implemented for Weaviate yet."""
        raise NotImplementedError("weaviate does not currently support `from_texts`.")
