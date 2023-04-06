#TODO: Add uuid to weaviate class

import os
import uuid
import json
import weaviate

from publisher_enum import PublisherEnum

class WeaviateClient(object):
    API_KEY = os.getenv('WEAVIATE_KEY', 'not the token')
    CLUSTER_URL = "https://dejour-cluster-11g1ktu8.weaviate.network"
    BATCH_SIZE = 100
    TEXT_FIELD_NAME = "snippet"

    def __init__(self, publisher: PublisherEnum) -> None:
        self.publisher = publisher
        self.class_name = f"ArticleSnippet_{self.publisher.value}"
        auth_config = weaviate.auth.AuthApiKey(api_key=self.API_KEY)
        self.client = weaviate.Client(
            url = self.CLUSTER_URL,
            auth_client_secret=auth_config,
            additional_headers={
                "X-OpenAI-Api-Key": os.getenv('OAI_TK', 'not the token')
            }
        )
        self.try_create_weaviate_class()
        

    def try_create_weaviate_class(self):
        try:
            self.client.schema.create_class(self.get_class_obj())
        except Exception as e:
            # hopefully they don't change this message
            if e.message and 'already used as a name for an Object class' in e.message:
                pass
            else:
                raise e

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

    def upload_data(self, data):
        ids = []
        with self.client.batch as batch:
            batch.batch_size=100
            # Batch import all Questions
            for i, d in enumerate(data):
                print(f"importing {self.TEXT_FIELD_NAME}: {i+1}")

                properties = {name: d[name] for name in self.get_property_names()}
                id = str(uuid.uuid4())
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