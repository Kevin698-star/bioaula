import os
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self._model = None
        self._ollama_available = False
        self._init_model()

    def _init_model(self):
        try:
            import ollama
            model_list = ollama.list()
            # Verificar si tiene el modelo nomic-embed-text
            models = [m.get('model', '') for m in model_list.get('models', [])]
            if any('nomic-embed-text' in m for m in models):
                self._ollama_available = True
                return
        except Exception:
            pass

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"SentenceTransformer not available: {e}")
            self._model = None

    def embed(self, texts):
        if not texts:
            return []
        single = isinstance(texts, str)
        inputs = [texts] if single else texts

        if self._ollama_available:
            try:
                import ollama
                results = []
                for t in inputs:
                    r = ollama.embeddings(model='nomic-embed-text', prompt=t)
                    results.append(r['embedding'])
                return results[0] if single else results
            except Exception:
                pass

        if self._model is not None:
            result = self._model.encode(inputs).tolist()
            return result[0] if single else result

        # Fallback simple de dimensionalidad fija (384) para no romper RAG si faltan pesos locales
        import hashlib
        def text_to_pseudo_vec(txt, dim=384):
            vec = []
            for i in range(dim):
                h = int(hashlib.md5(f"{txt}_{i}".encode('utf-8')).hexdigest()[:8], 16)
                vec.append((h / 0xFFFFFFFF) * 2.0 - 1.0)
            return vec

        fallback_results = [text_to_pseudo_vec(t) for t in inputs]
        return fallback_results[0] if single else fallback_results

    @property
    def dimension(self):
        if self._ollama_available:
            return 768
        return 384

    @property
    def available(self):
        return True
