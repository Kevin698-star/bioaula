import os

from .chunking import split_text
from .embeddings import EmbeddingService
from .vector_store import VectorStore

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PERSIST_DIR = os.path.join(PROJECT_ROOT, 'data', 'chroma')

embedding_service = EmbeddingService()
vector_store = None


def _ensure_store():
    global vector_store
    if vector_store is None:
        vector_store = VectorStore(PERSIST_DIR)
    return vector_store


def index_document(document_id, text):
    store = _ensure_store()
    chunks = split_text(text)
    if not chunks:
        return 0
    embeddings = embedding_service.embed(chunks)
    ids = ['%s_%d' % (document_id, i) for i in range(len(chunks))]
    metadatas = [{'document_id': document_id, 'chunk_id': cid} for cid in ids]
    store.index_chunks(chunks, embeddings, ids, metadatas)
    return len(chunks)


def search_document(query, n_results=10, document_id=None):
    store = _ensure_store()
    query_embedding = embedding_service.embed(query)
    where_filter = {'document_id': document_id} if document_id else None
    results = store.search(query_embedding, n_results, where_filter)

    if not results or not results.get('documents') or not results['documents'][0]:
        return ''

    return '\n\n'.join(results['documents'][0])
