import sys
import os
import asyncio

# Ensure backend directory is in sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Fix for Windows + Python 3.8+ asyncio event loop issues
if sys.platform.startswith("win"):
   asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Query
from typing import Optional
from backend.scrapers.rss_scraper import ingest_from_feeds
from backend.elasticsearch.es_client import get_es
from backend.config import ES_INDEX

app = FastAPI(title="News Analyser API")

# backend/app.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.get("/debug/mapping")
def get_mapping():
    """Debug endpoint to check Elasticsearch mapping"""
    es = get_es()
    try:
        mapping = es.indices.get_mapping(index=ES_INDEX)
        return mapping
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/sample")
def get_sample_doc():
    """Debug endpoint to get a raw sample document"""
    es = get_es()
    try:
        res = es.search(index=ES_INDEX, body={"query": {"match_all": {}}}, size=1)
        if res["hits"]["hits"]:
            return {
                "raw_document": res["hits"]["hits"][0],
                "_source_keys": list(res["hits"]["hits"][0]["_source"].keys())
            }
        return {"message": "No documents found"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/ingest/run")
def run_ingest(limit_per_feed: int = 20):
    try:
        print(f"DEBUG - Starting ingestion with limit_per_feed={limit_per_feed}")
        result = ingest_from_feeds(limit_per_feed=limit_per_feed)
        print(f"DEBUG - Ingestion result: {result}")
        return result
    except Exception as e:
        import traceback
        print(f"DEBUG - Ingestion error: {str(e)}")
        traceback.print_exc()
        return {"error": str(e)}

@app.get("/articles/search")
def search_articles(
    q: Optional[str] = Query(None, description="query string"),
    language: Optional[str] = None,
    sentiment: Optional[str] = None,
    bias: Optional[str] = None,
    size: int = 20
):
    print(f"DEBUG - Search request: q={q}, language={language}, sentiment={sentiment}, bias={bias}, size={size}")
    
    es = get_es()
    
    # Check if index exists
    if not es.indices.exists(index=ES_INDEX):
        print(f"DEBUG - Index {ES_INDEX} does not exist!")
        return {"count": 0, "results": []}
    
    must = []
    if q:
        must.append({"multi_match": {"query": q, "fields": ["title^2", "original_text", "summary"]}})
    if language:
        must.append({"term": {"language": language}})
    if sentiment:
        must.append({"term": {"sentiment_overall": sentiment}})
    if bias:
        must.append({"term": {"bias_overall": bias}})

    body = {"query": {"bool": {"must": must}}} if must else {"query": {"match_all": {}}}
    
    print(f"DEBUG - Elasticsearch query: {body}")
    
    try:
        res = es.search(index=ES_INDEX, body=body, size=size)
        print(f"DEBUG - Elasticsearch response: total hits = {res['hits']['total']['value'] if 'total' in res['hits'] else 'unknown'}")
        
        # ENHANCED DEBUGGING - Check raw Elasticsearch response
        if res["hits"]["hits"]:
            first_hit = res["hits"]["hits"][0]
            print("DEBUG - First raw hit from Elasticsearch:")
            print(f"  - _source keys: {list(first_hit['_source'].keys())}")
            print(f"  - title in _source: {'title' in first_hit['_source']}")
            print(f"  - title value: {first_hit['_source'].get('title', 'NOT_FOUND')}")
            print(f"  - Raw _source title: {repr(first_hit['_source'].get('title'))}")
    
        hits = []
        for h in res["hits"]["hits"]:
            article = {
                "id": h["_id"],
                "score": h["_score"],
            }
            
            # Explicitly extract each field to debug
            source = h["_source"]
            
            # CRITICAL: Make sure title is properly extracted
            title = source.get('title')
            if title is None:
                print(f"WARNING - Article {h['_id']} has no title field!")
            elif not title.strip():
                print(f"WARNING - Article {h['_id']} has empty title!")
            else:
                print(f"DEBUG - Article {h['_id']} has title: '{title[:50]}...'")
            
            article.update({
                "title": title,
                "url": source.get("url"),
                "source_name": source.get("source_name"),
                "published_date": source.get("published_date"),
                "language": source.get("language"),
                "original_text": source.get("original_text"),
                "translated_text": source.get("translated_text"),
                "summary": source.get("summary"),
                "sentiment_overall": source.get("sentiment_overall"),
                "sentiment_score": source.get("sentiment_score"),
                "bias_overall": source.get("bias_overall"),
                "bias_score": source.get("bias_score"),
                "entities": source.get("entities", []),
                "scraped_at": source.get("scraped_at"),
                "tags": source.get("tags", [])
            })
            
            hits.append(article)
    
        # DEBUG: Print first article to see what fields are actually stored/retrieved
        if hits:
            print(f"DEBUG - First article fields: {list(hits[0].keys())}")
            print(f"DEBUG - First article sample data:")
            print(f"  - Title: {hits[0].get('title', 'MISSING')}")
            print(f"  - Has summary: {bool(hits[0].get('summary'))}")
            summary_val = hits[0].get('summary')
            print(f"  - Summary length: {len(summary_val) if summary_val else 0}")
            print(f"  - Summary preview: {(summary_val or 'NONE')[:100]}...")
            print(f"  - Sentiment: {hits[0].get('sentiment_overall', 'MISSING')} ({hits[0].get('sentiment_score', 'MISSING')})")
            print(f"  - Bias: {hits[0].get('bias_overall', 'MISSING')} ({hits[0].get('bias_score', 'MISSING')})")
            print(f"  - Language: {hits[0].get('language', 'MISSING')}")
            print(f"  - Source: {hits[0].get('source_name', 'MISSING')}")
            print(f"  - URL: {hits[0].get('url', 'MISSING')}")
        else:
            print("DEBUG - No articles found in search results")
        
        result = {"count": len(hits), "results": hits}
        print(f"DEBUG - Returning {len(hits)} articles")
        
        return result
        
    except Exception as e:
        print(f"DEBUG - Search error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"count": 0, "results": [], "error": str(e)}

# Run with: uvicorn backend.app:app --reload --port 8000