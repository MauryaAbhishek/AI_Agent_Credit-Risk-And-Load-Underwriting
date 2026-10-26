from pathlib import Path
from app.vector_store.chroma_client import get_collection
from app.config import settings

def main():
    root = Path(__file__).resolve().parents[2] / "policy_documents"
    collection = get_collection()
    docs, ids, metadata = [], [], []
    for path in sorted(root.glob("*.md")):
        docs.append(path.read_text(encoding="utf-8"))
        ids.append(path.stem)
        metadata.append({"source": path.name, "policy_version": settings.policy_version})
    if not docs:
        raise SystemExit(f"No policy documents found under {root}")
    collection.upsert(ids=ids, documents=docs, metadatas=metadata)
    print(f"Indexed {len(docs)} documents into '{collection.name}' (version {settings.policy_version}).")

if __name__ == "__main__":
    main()
