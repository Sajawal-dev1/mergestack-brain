import os
from src.openai.client import extract_filters_from_question, get_embedder, get_llm
from src.pinecone.client import get_pinecone_index_name
from pinecone import Pinecone
import dateparser.search
from datetime import datetime, timedelta
import hashlib
from datetime import datetime
from src.utils.helpers  import date_to_milliseconds



def store_documents_openai(docs, namespace="default"):
    """Store documents in Pinecone using OpenAI embeddings."""
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(get_pinecone_index_name())
    embedder = get_embedder()

    for doc in docs:
        content = doc.get("content", "")
        metadata = doc.get("metadata", {})
        if not content:
            continue  # Skip docs without content

        # Collect stable fields to create a reproducible unique ID
        task_id = metadata.get('task_id', 'unknown')
        doc_type = metadata.get('document_type', 'unknown')
        created_at_ms = metadata.get('created_at_ms', '0')

        # Combine stable fields + content snippet (first 200 chars)
        id_source = f"{task_id}_{doc_type}_{created_at_ms}_{content[:200]}"
        
        # Create a SHA256 hash of the id_source for fixed-length unique ID
        doc_id = hashlib.sha256(id_source.encode('utf-8')).hexdigest()

        embedding = embedder(content)
        index.upsert(
            vectors=[{
                "id": doc_id,
                "values": embedding,
                "metadata": metadata,
            }],
            namespace=namespace
        )


def build_pinecone_filter(question: str) -> dict:
    extracted = extract_filters_from_question(question)
    filter_conditions = []

    # Assignees
    if "assignees" in extracted:
        assignees = [a.lower() for a in extracted["assignees"] if isinstance(a, str)]
        filter_conditions.append({
            "assignees": {"$in": assignees}
        })


    # Project
    if "project" in extracted:
        project = extracted["project"]
        if isinstance(project, str):
            project = project.lower()
        filter_conditions.append({
            "project": {"$eq": project}
        })

    # Status
    if "status" in extracted:
        status = extracted["status"]
        if isinstance(status, str):
            status = status.lower()
        filter_conditions.append({
            "status": {"$eq": status}
        })


    # Date range
    if "date_range" in extracted:
        dr = extracted["date_range"]
        start = dr.get("start")
        end = dr.get("end")

        if start and end:
            filter_conditions.append({
                "$and": [
                    {"updated_at_ms": {"$gte": date_to_milliseconds(start)}},
                    {"updated_at_ms": {"$lte": date_to_milliseconds(end)}}
                ]
            })
        elif start:
            filter_conditions.append({
                "updated_at_ms": {"$gte": date_to_milliseconds(start)}
            })
        elif end:
            filter_conditions.append({
                "updated_at_ms": {"$lte": date_to_milliseconds(end)}
            })

    # Final output: wrap in $or if multiple filters exist
    if len(filter_conditions) > 1:
        return {"$and": filter_conditions}
    elif filter_conditions:
        return filter_conditions[0]
    else:
        return {}



def get_relevant_docs(question, namespace="default"):
    """Retrieve relevant documents from Pinecone with content based on dynamic filters."""
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index_name = get_pinecone_index_name()
    index = pc.Index(index_name)

    embedder = get_embedder()
    embedding = embedder(question)

    # 🔥 NEW: Dynamically extract metadata filter
    metadata_filter = build_pinecone_filter(question)

    results = index.query(
        vector=embedding,
        top_k=10,
        namespace=namespace,
        filter=metadata_filter if metadata_filter else {},
        include_metadata=True
    )
    # Return list of documents with id and content (assuming content is in metadata or payload)
    print(len(results["matches"]))
    docs = []
    for match in results["matches"]:
        doc_id = match["id"]
        content = match.get("metadata", {}).get("content") or match.get("payload", {}).get("content")
        if content is None:
            content = "<no content available>"
        docs.append({"id": doc_id, "content": content})
    return docs



def run_rag_pipeline(question: str, namespace="default") -> str:
    """RAG pipeline using OpenAI SDK with enhanced prompting for quality responses."""
    relevant_docs = get_relevant_docs(question, namespace)
    today_str = datetime.now().strftime("%Y-%m-%d")


    context = "\n\n".join(
        [f"Document {i+1}:\n{doc['content']}" for i, doc in enumerate(relevant_docs)]
        if relevant_docs else ["No relevant documents found."]
    )

    prompt = f"""You are an expert assistant helping answer questions based on the following context.

Today's date: {today_str}

Context:
{context}

Instructions:
- Answer the question based only on the context above.
- If the most recent document appears up to date or contains a recent timestamp, respond accordingly.
- If no context is provided, say "I don't know based on the provided context."
- Be concise, accurate, and well-structured.

Question: {question}
"""

    llm = get_llm()
    response = llm([
        {"role": "system", "content": "You are a helpful assistant trained to answer questions using provided documents."},
        {"role": "user", "content": prompt}
    ])

    return response
