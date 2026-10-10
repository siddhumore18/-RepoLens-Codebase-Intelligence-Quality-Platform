"""
Embedding Engine Module
Dense vector embeddings with subword vectorizer fallback.
"""

import numpy as np
from typing import List, Dict, Any, Optional

class CodeEmbeddingEngine:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name
        self.model = None
        self.use_fallback = True
        self.dimensions = 256
        
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(
            analyzer='word',
            ngram_range=(1, 2),
            max_features=256,
            token_pattern=r'(?u)\b[a-zA-Z_$][a-zA-Z0-9_$]*\b'
        )
        
        if model_name:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(model_name)
                self.dimensions = self.model.get_sentence_embedding_dimension()
                self.use_fallback = False
            except Exception:
                self.use_fallback = True

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimensions))

        if not self.use_fallback and self.model is not None:
            try:
                embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
                return embeddings
            except Exception:
                pass

        if self.vectorizer is not None:
            if not hasattr(self.vectorizer, 'vocabulary_') or self.vectorizer.vocabulary_ is None:
                matrix = self.vectorizer.fit_transform(texts).toarray()
            else:
                try:
                    matrix = self.vectorizer.transform(texts).toarray()
                except Exception:
                    matrix = self.vectorizer.fit_transform(texts).toarray()
            
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            return matrix / norms

        return np.zeros((len(texts), self.dimensions))

    def compute_similarity(self, query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
        if doc_vecs.shape[0] == 0:
            return np.array([])
        if query_vec.ndim == 1:
            query_vec = query_vec.reshape(1, -1)
        sims = np.dot(doc_vecs, query_vec.T).flatten()
        return sims
