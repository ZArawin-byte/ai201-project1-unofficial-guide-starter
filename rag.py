"""
RAG core — Milestones 4 & 5.

  build_store()        embed every chunk with all-MiniLM-L6-v2 and persist to ChromaDB
  retrieve(query, k)   semantic search -> top-k chunks with source metadata + distance
  answer(query, k)     grounded generation via Groq, returns {answer, sources, chunks}

CLI:
  python rag.py build                 # (re)build the vector store
  python rag.py retrieve "question"   # inspect retrieval only (no LLM, no API key)
  python rag.py ask "question"        # full grounded answer (needs GROQ_API_KEY)
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from ingest import build_chunks

load_dotenv()

CHROMA_DIR = str(Path(__file__).parent / "chroma_db")
COLLECTION_NAME = "unofficial_guide"
EMBED_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL = "llama-3.3-70b-versatile"   # Groq free tier
TOP_K = 4

# Grounding is enforced here, not suggested. The model is told to use ONLY the
# numbered context, to cite the [source] tags it actually used, and to refuse
# when the context is insufficient rather than fall back on training knowledge.
SYSTEM_PROMPT = """You are The Unofficial Lakemont Guide. You answer student questions \
using ONLY the numbered context passages provided in the user's message. The context \
is drawn from real student reviews, forum threads, and guides.

Rules:
1. Use ONLY information stated in the context passages. Do NOT use any outside or general knowledge.
2. If the context does not contain enough information to answer, reply exactly: \
"I don't have enough information on that in the Unofficial Guide." Do not guess.
3. After your answer, add a line beginning "Sources:" listing the [source] filenames \
of the passages you actually used.
4. Be concise and practical, like a student giving another student real advice."""


# --- lazy singletons ------------------------------------------------------

_model = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def _get_collection(create: bool = False):
    """Return the Chroma collection. If create=True, drop and rebuild it empty."""
    global _collection
    import chromadb

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    if create:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        _collection = client.create_collection(
            COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
    elif _collection is None:
        _collection = client.get_collection(COLLECTION_NAME)
    return _collection


# --- Milestone 4: embed + store + retrieve --------------------------------

def build_store():
    """Embed all chunks and (re)load them into ChromaDB with source metadata."""
    chunks = build_chunks()
    model = _get_model()
    embeddings = model.encode(
        [c["text"] for c in chunks], show_progress_bar=False
    ).tolist()

    collection = _get_collection(create=True)
    collection.add(
        ids=[f"{c['source']}::{c['chunk_index']}" for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=embeddings,
        metadatas=[
            {"source": c["source"], "chunk_index": c["chunk_index"]} for c in chunks
        ],
    )
    print(f"Built '{COLLECTION_NAME}': {len(chunks)} chunks embedded with {EMBED_MODEL}.")
    return len(chunks)


def retrieve(query: str, k: int = TOP_K):
    """Return the top-k chunks for a query: [{text, source, chunk_index, distance}]."""
    model = _get_model()
    q_emb = model.encode([query]).tolist()
    collection = _get_collection()
    res = collection.query(query_embeddings=q_emb, n_results=k)

    out = []
    for text, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        out.append(
            {
                "text": text,
                "source": meta["source"],
                "chunk_index": meta["chunk_index"],
                "distance": dist,
            }
        )
    return out


# --- Milestone 5: grounded generation -------------------------------------

def _format_context(chunks):
    blocks = []
    for i, c in enumerate(chunks, 1):
        blocks.append(f"[{i}] (source: {c['source']})\n{c['text']}")
    return "\n\n".join(blocks)


def answer(query: str, k: int = TOP_K):
    """Retrieve, then generate a grounded answer. Returns {answer, sources, chunks}.

    `sources` is built programmatically from the retrieved chunks, so attribution is
    guaranteed even if the model forgets to cite.
    """
    from groq import Groq

    chunks = retrieve(query, k)
    sources = sorted({c["source"] for c in chunks})

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise RuntimeError(
            "GROQ_API_KEY not set. Copy .env.example to .env and add your key "
            "from https://console.groq.com (retrieval works without it; generation needs it)."
        )

    client = Groq(api_key=api_key)
    user_msg = (
        f"Context passages:\n\n{_format_context(chunks)}\n\n"
        f"Question: {query}"
    )
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    return {
        "answer": resp.choices[0].message.content.strip(),
        "sources": sources,
        "chunks": chunks,
    }


# --- CLI ------------------------------------------------------------------

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"

    if cmd == "build":
        build_store()

    elif cmd == "retrieve":
        query = sys.argv[2]
        print(f"Query: {query}\n")
        for i, c in enumerate(retrieve(query), 1):
            print(f"[{i}] {c['source']} (chunk {c['chunk_index']}) · distance={c['distance']:.3f}")
            print(f"    {c['text'][:200]}{'...' if len(c['text']) > 200 else ''}\n")

    elif cmd == "ask":
        result = answer(sys.argv[2])
        print(result["answer"])
        print("\nRetrieved from:", ", ".join(result["sources"]))

    else:
        print(__doc__)
