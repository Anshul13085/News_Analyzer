from elasticsearch import Elasticsearch
from backend.config import ES_HOST

def get_es():
    es = Elasticsearch(ES_HOST)
    if not es.ping():
        raise RuntimeError("Elasticsearch is not reachable at %s" % ES_HOST)
    return es
