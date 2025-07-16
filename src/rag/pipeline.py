from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore 
from src.openai.client import get_embedder
from src.pinecone.client import get_pinecone_index_name
from langchain_core.vectorstores import VectorStoreRetriever
from src.openai.client import get_llm  
from langchain.chains import RetrievalQA
import dateparser.search
from datetime import datetime, timedelta



def store_documents(docs,namespace="default"):
    langchain_docs = []

    for doc in docs:
        content = doc.get("content", "")
        metadata = doc.get("metadata", {})

        flat_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, (dict, list)):
                flat_metadata[key] = str(value)
            else:
                flat_metadata[key] = value

        langchain_docs.append(Document(
            page_content=content,
            metadata=flat_metadata
        ))

    embedder = get_embedder()
    index_name = get_pinecone_index_name()

    # ✅ use new PineconeVectorStore
    PineconeVectorStore.from_documents(
        documents=langchain_docs,
        embedding=embedder,
        index_name=index_name,
        namespace=namespace
    )


def extract_date_range(question: str):
    """
    Extracts the earliest and latest dates from a user's question using natural language parsing.
    """
    parsed = dateparser.search.search_dates(question, settings={'PREFER_DATES_FROM': 'past'})
    if not parsed:
        return None

    dates = [dt for _, dt in parsed]
    start = min(dates).date()
    end = max(dates).date()
    return start, end


def get_retriever(namespace="default", metadata_filter=None) ->  VectorStoreRetriever:
    """
    Returns a Pinecone retriever with an optional metadata filter.
    """
    embedder = get_embedder()
    index_name = get_pinecone_index_name()

    vectorstore = PineconeVectorStore(
        embedding=embedder,
        index_name=index_name,
        namespace=namespace
    )

    return vectorstore.as_retriever(
        search_kwargs={"filter": metadata_filter} if metadata_filter else {}
    )


def run_rag_pipeline(question: str, namespace="default") -> str:
    """
    RAG pipeline that runs a user's query through a retriever + LLM, with support for date-based filtering.
    """
    metadata_filter = None

    # Try to extract a date range from the question
    date_range = extract_date_range(question)
    if date_range:
        start_date, end_date = date_range
        # Convert to datetime objects
                 # Convert to datetime objects
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.min.time())

    # Convert to milliseconds since epoch
        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)
        print("start_ms", start_ms)
        print("end_ms", end_ms)
        if start_date == end_date:
            metadata_filter = {"created_at_ms": {"$eq": start_ms}}
        else:
            metadata_filter = {
                "created_at_ms:": {
                    "$gte": start_ms,
                    "$lte": end_ms
                }
            }

    retriever = get_retriever(namespace, metadata_filter)
    llm = get_llm()

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=False
    )

    return qa_chain.run(question)
