from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore  # ✅ new import
from src.openai.client import get_embedder
from src.pinecone.client import get_pinecone_index_name


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
