import os
from src.openai.client import get_embedder, get_llm
from src.pinecone.client import get_pinecone_index_name
from pinecone import Pinecone
import dateparser.search
from datetime import datetime, timedelta
import hashlib


def store_documents_openai(docs, namespace="default"):
    """Store documents in Pinecone using OpenAI embeddings."""
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(get_pinecone_index_name())
    embedder = get_embedder()

    for doc in docs:
        content = doc.get("content", "")
        metadata = doc.get("metadata", {})
        if not content:
            continue

        # Generate unique ID using task_id, doc type, and content hash
        doc_id = f"{metadata.get('task_id', 'unknown')}_{metadata.get('document_type', 'unknown')}_{metadata.get('created_at_ms', '0')}"

        
        embedding = embedder(content)
        index.upsert(
            vectors=[{
                "id": doc_id,
                "values": embedding,
                "metadata": metadata,
            }],
            namespace=namespace
        )

def extract_date_range(question: str):
    """Extracts the earliest and latest dates from a user's question."""
    parsed = dateparser.search.search_dates(question, settings={'PREFER_DATES_FROM': 'past'})
    if not parsed:
        return None
    dates = [dt for _, dt in parsed]
    start = min(dates).date()
    end = max(dates).date()
    return start, end

def get_relevant_docs(question, namespace="default", metadata_filter=None):
    """Retrieve relevant documents from Pinecone."""
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index_name = get_pinecone_index_name()
    index = pc.Index(index_name)

    embedder = get_embedder()
    embedding = embedder(question)
    results = index.query(
        vector=embedding,
        top_k=5,
        namespace=namespace,
        filter=metadata_filter if metadata_filter else {}
    )
    return [match["id"] for match in results["matches"]]

def run_rag_pipeline(question: str, namespace="default") -> str:
    """RAG pipeline using Open AI SDK."""
    metadata_filter = None

    date_range = extract_date_range(question)
    if date_range:
        start_date, end_date = date_range
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.min.time())
        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)
        if start_date == end_date:
            metadata_filter = {"created_at_ms": {"$eq": start_ms}}
        else:
            metadata_filter = {"created_at_ms": {"$gte": start_ms, "$lte": end_ms}}

    relevant_docs = get_relevant_docs(question, namespace, metadata_filter)
    context = "\n".join([f"Doc ID: {doc_id}" for doc_id in relevant_docs])

    llm = get_llm()
    response = llm([{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": f"Based on this context: {context}\n\nQuestion: {question}"}])
    return response