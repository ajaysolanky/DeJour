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

from weaviate_utils.weaviate_client import WeaviatePythonClient, WeaviateCURL
from utils import LOCAL_DB_FOLDER

class VectorDB(ABC):
    def __init__(self, publisher) -> None:
        self.publisher = publisher

    @abstractmethod
    def add_texts(self, texts: List[str], metadatas: List[Dict]):
        pass

    @abstractmethod
    def get_k_closest_docs(self, query: str, k: int):
        pass
    
    @abstractmethod
    def get_vectorstore(self):
        pass

class VectorDBLocal(VectorDB):
    def __init__(self, publisher):
        super().__init__(publisher)
        self.store = None
        dir_path = f"{LOCAL_DB_FOLDER}/{self.publisher.value}/"
        self.index_file_path = dir_path + 'docs.index'
        self.store_file_path = dir_path + 'faiss_store.pkl'
        if not os.path.isfile(self.index_file_path):
            os.makedirs(os.path.dirname(self.index_file_path))
            with open(self.index_file_path, 'w') as f:
                f.write('')
            with open(self.store_file_path, 'w') as f:
                f.write('')
            init_store = FAISS.from_texts(['test'], OpenAIEmbeddings(), metadatas=[{"source":'test'}])
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
        faiss.write_index(store_obj.index, self.index_file_path)
        store_copy = copy.deepcopy(store_obj)
        store_copy.index = None
        with open(self.store_file_path, 'wb') as f:
            pickle.dump(store_copy, f)

class VectorDBWeaviate(VectorDB, ABC):
    def __init__(self, publisher) -> None:
        super().__init__(publisher)
        # self.weaviate_service = WeaviatePythonClient(self.publisher)
        # self.weaviate_service = WeaviateCURL(self.publisher)
    
    @abstractmethod
    def get_vectorstore(self):
        pass

    def add_texts(self, texts: List[str], metadatas: List[Dict]):
        data = [md | {self.weaviate_service.TEXT_FIELD_NAME: txt}  for txt, md in zip(texts, metadatas)]
        new_ids = self.weaviate_service.upload_data(data)
        return new_ids
    
    def get_k_closest_docs(self, query: str, k: int):
        results = self.weaviate_service.fetch_top_k_matches(query, k)
        docs = []
        for r in results:
            page_content = r.pop(self.weaviate_service.TEXT_FIELD_NAME)
            metadata = r
            docs.append(Document(
                page_content=page_content,
                metadata=metadata
            ))
        return docs
    
class VectorDBWeaviatePythonClient(VectorDBWeaviate):
    def __init__(self, publisher) -> None:
        super().__init__(publisher)
        self.weaviate_service = WeaviatePythonClient(self.publisher)

    def get_vectorstore(self):
        return Weaviate(self.weaviate_service.client, self.weaviate_service.class_name, self.weaviate_service.TEXT_FIELD_NAME)
    
class VectorDBWeaviateCURL(VectorDBWeaviate):
    def __init__(self, publisher) -> None:
        super().__init__(publisher)
        self.weaviate_service = WeaviateCURL(self.publisher)

    def get_vectorstore(self):
        return WeaviateVectorStoreCURL(
            self,
            self.weaviate_service.class_name,
            self.weaviate_service.TEXT_FIELD_NAME
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
        return self._curl_client.get_k_closest_docs(query, k)

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
