import os
import chromadb
from chromadb.config import Settings


class VectorStore:
    def __init__(self, persist_dir):
        os.makedirs(persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name='bioaula_materials',
            metadata={'hnsw:space': 'cosine'},
        )

    def index_chunks(self, chunks, embeddings, ids, metadatas):
        # Utilizar upsert para evitar errores de IDs duplicados al reindexar
        self.collection.upsert(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids,
        )

    def search(self, query_embedding, n_results=10, where_filter=None):
        kwargs = {
            'query_embeddings': [query_embedding],
            'n_results': n_results,
        }
        if where_filter:
            kwargs['where'] = where_filter

        return self.collection.query(**kwargs)
