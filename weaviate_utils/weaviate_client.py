import hashlib
import os
import uuid
import weaviate
from weaviate.util import get_valid_uuid
import requests
from abc import ABC, abstractmethod

from publisher_enum import PublisherEnum

class WeaviateService(ABC):
    API_KEY = os.getenv('WEAVIATE_KEY', 'not the token')
    CLUSTER_URL = "https://dejour-cluster-11g1ktu8.weaviate.network"
    BATCH_SIZE = 100
    TEXT_FIELD_NAME = "snippet"

    def __init__(self, publisher: PublisherEnum) -> None:
        self.publisher = publisher
        self.class_name = f"ArticleSnippet_{self.publisher.value}"

    def get_id(self, url, idx):
        # return get_valid_uuid(uuid.uuid4())
        # return f"{url}::INDEX::{idx}"
        return hashlib.md5(f"{url}::INDEX::{idx}".encode('utf-8')).hexdigest()

    @abstractmethod
    def try_create_weaviate_class(self):
        pass

    @abstractmethod
    def upload_data(self, data):
        pass
    
    @abstractmethod
    def fetch_top_k_matches(self, query_text, k):
        pass

    @abstractmethod
    def delete_class(self):
        pass

    def get_class_obj(self):
        return {
            "class": self.class_name,
            "description": "Snippet of text spliced from an article",
            "vectorizer": "text2vec-openai",
            "properties": [
                {
                    "name": "title",
                    "description": "The title",
                    "dataType": ["text"],
                },
                {
                    "name": "source",
                    "description": "URL of article",
                    "dataType": ["text"],
                },
                {
                    "name": "fetch_timestamp",
                    "description": "Timestamp of when the article was fetched",
                    "dataType": ["date"],
                },
                {
                    "name": "publish_timestamp",
                    "description": "Timestamp of when the article was published",
                    "dataType": ["date"],
                },
                {
                    "name": "top_image_url",
                    "description": "URL of the top image from the article",
                    "dataType": ["text"],
                },
                {
                    "name": self.TEXT_FIELD_NAME,
                    "description": "The actual snippet",
                    "dataType": ["text"],
                },
            ]
        }

    def get_property_names(self):
        property_names = []
        for property in self.get_class_obj()['properties']:
            property_names.append(property['name'])
        return property_names

class WeaviatePythonClient(WeaviateService):
    def __init__(self, publisher: PublisherEnum) -> None:
        super().__init__(publisher)
        auth_config = weaviate.auth.AuthApiKey(api_key=self.API_KEY)
        self.client = weaviate.Client(
            url = self.CLUSTER_URL,
            auth_client_secret=auth_config,
            additional_headers={
                "X-OpenAI-Api-Key": os.getenv('OPENAI_API_KEY', 'not the token')
            }
        )

    def try_create_weaviate_class(self):
        try:
            self.client.schema.create_class(self.get_class_obj())
        except Exception as e:
            # hopefully they don't change this message
            if e.message and 'already used as a name for an Object class' in e.message:
                pass
            else:
                raise e
    
    def upload_data(self, data):
        ids = []
        with self.client.batch as batch:
            batch.batch_size=self.BATCH_SIZE
            # Batch import all Questions
            for i, d in enumerate(data):
                print(f"importing {self.TEXT_FIELD_NAME}: {i+1}")
                properties = {name: d[name] for name in self.get_property_names()}
                # id = get_valid_uuid(uuid.uuid4())
                id = self.get_id(d['source'], d['idx'])
                ids.append(id)
                self.client.batch.add_data_object(
                    data_object=properties,
                    class_name=self.class_name,
                    uuid=id)
        return ids

    def fetch_top_k_matches(self, query_text, k):
        query_dict = {"concepts": [query_text]}

        result = (
            self.client.query
                .get(self.class_name, self.get_property_names())
                .with_near_text(query_dict)
                .with_limit(k)
                .do()
            )

        return result['data']['Get'][self.class_name]

    def delete_class(self):
        print(f"deleting {self.class_name}...")
        self.client.schema.delete_class(self.class_name)
        print(f"deleted {self.class_name}!")

#TODO: check status code and do error handling
# This class exists so as to avoid setup latency incurred by python client
class WeaviateCURL(WeaviateService):
    def try_create_weaviate_class(self):
        data = self.get_class_obj()
        r = requests.post(
            self.CLUSTER_URL+'/v1/schema',
            headers=self.get_headers(),
            json=data)
        if r.status_code != 200:
            raise Exception('Failed!')

    def get_headers(self):
        return {
            "Content-Type": "application/json",
            "X-OpenAI-Api-Key": os.getenv('OPENAI_API_KEY', 'not the token'),
            "Authorization": f"Bearer {self.API_KEY}"
        }

    def upload_data(self, data):
        ids = []
        batch_data = []
        for i, d in enumerate(data):
            print(f"importing {self.TEXT_FIELD_NAME}: {i+1}")
            properties = {name: d[name] for name in self.get_property_names()}
            # id = get_valid_uuid(uuid.uuid4())
            id = self.get_id(d['source'], d['idx'])
            ids.append(id)
            batch_data.append({
                "class":  self.class_name,
                "properties": properties,
                "id": id
            })
            if len(batch_data) >= self.BATCH_SIZE:
                self.upload_batch(batch_data)
                batch_data = []
        if batch_data:
            self.upload_batch(batch_data)
        return ids

    #TODO: this isn't working
    def upload_batch(self, batch_data):
        print(f"uploading batch of size {len(batch_data)}")
        r = requests.post(
            self.CLUSTER_URL+'/v1/batch/objects',
            headers=self.get_headers(),
            json=batch_data
        )
        if r.status_code != 200:
            raise Exception('Failed!')

    def fetch_top_k_matches(self, query_text, k):
        formatted_fields = '\n'.join(self.get_property_names())
        graphql = """
        {
            Get{
                %(class_name)s(
                    nearText: {
                        concepts: ["%(query_text)s"]
                    },
                    limit: %(k)s
                ){
                    %(formatted_fields)s
                    _additional {
                        certainty
                    }
                }
            }
        }
        """ % {
            "class_name": self.class_name,
            "query_text": query_text,
            "k": k,
            "formatted_fields": formatted_fields
        }
        data = {
            "query": graphql
        }
        r = requests.post(self.CLUSTER_URL+'/v1/graphql',
                      headers=self.get_headers(),
                      json=data)
        if r.status_code != 200:
            raise Exception('Failed!')
        else:
            return r.json()['data']['Get'][self.class_name]

    def delete_class(self):
        r = requests.delete(self.CLUSTER_URL+'/v1/schema/'+self.class_name, headers=self.get_headers())
        if r.status_code != 200:
            raise Exception('Failed!')
