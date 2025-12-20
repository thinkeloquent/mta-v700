"""
FastAPI example demonstrating db_connection_elasticsearch usage.

Run with: uvicorn main:app --reload
"""

import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from db_connection_elasticsearch import (
    ElasticsearchConfig,
    get_elasticsearch_client,
    check_connection,
)


class SearchRequest(BaseModel):
    query: str
    index: Optional[str] = None
    size: int = 10


class DocumentRequest(BaseModel):
    index: str
    document: Dict[str, Any]
    id: Optional[str] = None


class SearchResult(BaseModel):
    total: int
    hits: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    elasticsearch: Dict[str, Any]


# Global client reference
es_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage Elasticsearch client lifecycle."""
    global es_client

    # Initialize client on startup
    config = ElasticsearchConfig(
        host=os.getenv("ELASTIC_DB_HOST", "localhost"),
        port=int(os.getenv("ELASTIC_DB_PORT", "9200")),
        scheme=os.getenv("ELASTIC_DB_SCHEME", "https"),
        username=os.getenv("ELASTIC_DB_USERNAME"),
        password=os.getenv("ELASTIC_DB_PASSWORD"),
        api_key=os.getenv("ELASTIC_DB_API_KEY"),
        verify_certs=os.getenv("ELASTIC_DB_VERIFY_CERTS", "false").lower() == "true",
    )

    try:
        es_client = await get_elasticsearch_client(config)
        print("Elasticsearch client initialized")
    except Exception as e:
        print(f"Warning: Could not connect to Elasticsearch: {e}")
        es_client = None

    yield

    # Cleanup on shutdown
    if es_client:
        await es_client.close()
        print("Elasticsearch client closed")


app = FastAPI(
    title="Elasticsearch FastAPI Example",
    description="Example API demonstrating db_connection_elasticsearch usage",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API and Elasticsearch health."""
    if not es_client:
        return HealthResponse(
            status="degraded",
            elasticsearch={"connected": False, "error": "Client not initialized"},
        )

    try:
        info = await es_client.info()
        return HealthResponse(
            status="healthy",
            elasticsearch={
                "connected": True,
                "cluster_name": info.get("cluster_name"),
                "version": info.get("version", {}).get("number"),
            },
        )
    except Exception as e:
        return HealthResponse(
            status="degraded",
            elasticsearch={"connected": False, "error": str(e)},
        )


@app.get("/connection/check")
async def connection_check():
    """Check Elasticsearch connection using library function."""
    result = await check_connection()
    return result


@app.get("/indices")
async def list_indices():
    """List all Elasticsearch indices."""
    if not es_client:
        raise HTTPException(status_code=503, detail="Elasticsearch not connected")

    try:
        indices = await es_client.cat.indices(format="json")
        return {"indices": indices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=SearchResult)
async def search_documents(request: SearchRequest):
    """Search documents in Elasticsearch."""
    if not es_client:
        raise HTTPException(status_code=503, detail="Elasticsearch not connected")

    try:
        body = {
            "query": {
                "multi_match": {
                    "query": request.query,
                    "fields": ["*"],
                }
            },
            "size": request.size,
        }

        index = request.index or "_all"
        response = await es_client.search(index=index, body=body)

        hits = response.get("hits", {})
        return SearchResult(
            total=hits.get("total", {}).get("value", 0),
            hits=[
                {
                    "_id": hit.get("_id"),
                    "_index": hit.get("_index"),
                    "_score": hit.get("_score"),
                    "_source": hit.get("_source"),
                }
                for hit in hits.get("hits", [])
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents")
async def index_document(request: DocumentRequest):
    """Index a document into Elasticsearch."""
    if not es_client:
        raise HTTPException(status_code=503, detail="Elasticsearch not connected")

    try:
        if request.id:
            response = await es_client.index(
                index=request.index,
                id=request.id,
                document=request.document,
            )
        else:
            response = await es_client.index(
                index=request.index,
                document=request.document,
            )

        return {
            "_id": response.get("_id"),
            "_index": response.get("_index"),
            "result": response.get("result"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{index}/{doc_id}")
async def get_document(index: str, doc_id: str):
    """Get a document by ID."""
    if not es_client:
        raise HTTPException(status_code=503, detail="Elasticsearch not connected")

    try:
        response = await es_client.get(index=index, id=doc_id)
        return {
            "_id": response.get("_id"),
            "_index": response.get("_index"),
            "_source": response.get("_source"),
        }
    except Exception as e:
        if "NotFoundError" in str(type(e)):
            raise HTTPException(status_code=404, detail="Document not found")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{index}/{doc_id}")
async def delete_document(index: str, doc_id: str):
    """Delete a document by ID."""
    if not es_client:
        raise HTTPException(status_code=503, detail="Elasticsearch not connected")

    try:
        response = await es_client.delete(index=index, id=doc_id)
        return {
            "_id": response.get("_id"),
            "_index": response.get("_index"),
            "result": response.get("result"),
        }
    except Exception as e:
        if "NotFoundError" in str(type(e)):
            raise HTTPException(status_code=404, detail="Document not found")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
