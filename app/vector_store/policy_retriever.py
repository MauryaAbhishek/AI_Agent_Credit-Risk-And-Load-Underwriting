import logging
from app.vector_store.chroma_client import get_collection

logger = logging.getLogger(__name__)

def retrieve_policy(query: str, n_results: int = 3) -> list[dict]:
    try:
        collection = get_collection()
        count = collection.count()
        if count == 0:
            return [{"id": "policy-index-empty", "source": "system",
                     "text": "No policy documents indexed; human review required.", "distance": None}]
        result = collection.query(query_texts=[query], n_results=min(n_results, count))
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [
            {"id": ids[i], "source": (metas[i] or {}).get("source", "unknown"),
             "policy_version": (metas[i] or {}).get("policy_version", "unknown"),
             "text": docs[i], "distance": distances[i] if distances else None}
            for i in range(len(docs))
        ]
    except Exception:
        logger.exception("Policy retrieval failed")
        return [{"id": "retrieval-unavailable", "source": "system",
                 "text": "Policy retrieval unavailable; human review required.", "distance": None}]
