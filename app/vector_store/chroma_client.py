import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from app.config import settings

def get_collection():
    client = chromadb.PersistentClient(path=settings.chroma_path)
    embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    return client.get_or_create_collection(
        name=settings.policy_collection,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"},
    )
