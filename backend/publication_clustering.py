import logging
from collections import Counter, defaultdict
from typing import Dict, List, Any

import numpy as np
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

from backend.config import ELASTICSEARCH_URL


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class PublicationClustering:

    def __init__(self, embedding_dim: int = 384, es_url=ELASTICSEARCH_URL):
        self.dim = embedding_dim
        self.es_url = es_url.rstrip("/")
        self._vector_cache: Dict[str, np.ndarray] = {}
        from backend.adaptive_clustering import AdaptiveClusteringOptimizer
        self.optimizer = AdaptiveClusteringOptimizer()


    def _get_publication_vector(self, pub: Dict[str, Any]) -> np.ndarray:

        pid = pub.get("id")
        if pid and pid in self._vector_cache:
            return self._vector_cache[pid]

        raw_vec = pub.get("combined_embedding")
        if raw_vec is None:
            vec = np.zeros(self.dim, dtype="float32")
        else:
            vec = np.asarray(raw_vec, dtype="float32")
            if vec.shape[0] != self.dim or np.isnan(vec).any():
                vec = np.zeros(self.dim, dtype="float32")
            else:
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm

        if pid:
            self._vector_cache[pid] = vec
        return vec


    def cluster_publications(
        self,
        publications: List[Dict[str, Any]],
        method: str = "auto",
        k_max: int = 10,
        min_cluster_size: int = 3,
        adaptive: bool = True,
        dim_reduction_method: str = "auto"
    ) -> Dict[str, Any]:

        pub_vectors: Dict[str, np.ndarray] = {}
        for pub in publications:
            pid = pub.get("id")
            if not pid:
                continue
            v = self._get_publication_vector(pub)
            if v.any():
                pub_vectors[pid] = v

        if len(pub_vectors) < 3:
            return {"error": "Too few publications with valid combined_embedding"}

        ids = list(pub_vectors.keys())
        X = np.vstack([pub_vectors[i] for i in ids])

        n_samples = X.shape[0]
        logger.info(f"Clustering {n_samples} publications – method={method}")

        X2 = self._perform_dimensionality_reduction(X, dim_reduction_method)

        if method == "auto":
            method = self._auto_method_choice(n_samples)

        X_high = X

        labels, n_clusters, method_used = self._run_clustering(
            method, X_high, k_max, min_cluster_size, n_dims=50, adaptive=adaptive
        )

        quality = self._quality_stats(X_high, labels)

        clusters: Dict[int, Dict[str, Any]] = defaultdict(lambda: {"publications": [], "points": []})
        for i, lab in enumerate(labels):
            if lab < 0:
                continue  
            pid = ids[i]
            clusters[lab]["publications"].append(pid)
            clusters[lab]["points"].append(X2[i].tolist())

        for cid, data in clusters.items():
            pubs = [p for p in publications if p.get("id") in data["publications"]]
            kw_counter = Counter()
            years = []
            for p in pubs:
                kw_counter.update(p.get("keywords", []) if isinstance(p.get("keywords"), list) else [])
                if p.get("publication_year"):
                    years.append(p["publication_year"])
            data["keywords"] = kw_counter.most_common(10)
            data["size"] = len(data["publications"])
            data["years"] = {"min": min(years) if years else None, "max": max(years) if years else None}
            data["sample_titles"] = [p.get("title", "") for p in pubs][:5]

        result = sorted([
            {"id": cid, **info} for cid, info in clusters.items()
        ], key=lambda d: d["size"], reverse=True)

        if hasattr(self, 'metrics_history') and self.metrics_history:
            quality['parameter_metrics'] = self.metrics_history


        quality['visualization_method'] = dim_reduction_method

        return {
            "clusters": result,
            "n_clusters": n_clusters,
            "method": method_used,
            "num_publications": n_samples,
            "quality": quality,
            "publication_to_cluster": {pid: lab for pid, lab in zip(ids, labels)},
        }

    def _perform_dimensionality_reduction(self, X, method="auto"):

        n_samples = X.shape[0]
        target_dims = 2

        if n_samples < 5:
            return X[:, :target_dims] if X.shape[1] >= target_dims else np.hstack([X, np.zeros((n_samples, target_dims - X.shape[1]))])

        if method == "auto":
            if n_samples < 50:
                method = "pca"  
            elif n_samples < 5000:
                method = "umap"  
            else:
                method = "pca"  
        

        try:
            if method == "umap":
                try:
                    import umap
                    reducer = umap.UMAP(
                        n_components=target_dims,
                        random_state=42,
                        n_neighbors=min(15, max(5, n_samples // 10)),
                        min_dist=0.1
                    )
                    return reducer.fit_transform(X)
                except ImportError:
                    logger.warning("UMAP not installed, falling back to PCA")
                    return PCA(n_components=target_dims, random_state=42).fit_transform(X)
                
                
            else:  
                return PCA(n_components=target_dims, random_state=42).fit_transform(X)
                
        except Exception as e:
            logger.warning(f"Error in dimensionality reduction with {method}: {e}. Falling back to PCA")
            return PCA(n_components=target_dims, random_state=42).fit_transform(X)

    @staticmethod
    def _auto_method_choice(n: int) -> str:
        if n < 15:
            return "hierarchical"
        elif n < 150:
            try:
                import hdbscan  
                return "hdbscan"
            except ImportError:
                return "kmeans"
        else:
            return "kmeans"

    def _run_clustering(self, method: str, X: np.ndarray, k_max: int, min_cluster_size: int, n_dims=50, adaptive=True):

        if method == "adaptive" or (adaptive and method in ["kmeans", "hierarchical", "auto"]):

            actual_method = "kmeans" if method == "adaptive" else method

            variance_threshold = 0.9 
            opt_dims, X_reduced = self.optimizer.optimize_pca_dimensions(X, variance_threshold)

            min_k = max(2, min(k_max - 1, 3))
            max_k = min(k_max, int(np.sqrt(X_reduced.shape[0])))
            

            if min_k >= max_k:
                min_k = 2
                max_k = max(3, min_k)
            
            opt_k, labels = self.optimizer.optimize_n_clusters(
                X_reduced, 
                min_clusters=min_k, 
                max_clusters=max_k, 
                method=actual_method
            )
            

            metrics_history = self.optimizer.get_parameter_history()

            self.metrics_history = metrics_history
            
            method_name = f"{actual_method}_adaptive"
            if opt_dims < X.shape[1]:
                method_name += f" (PCA={opt_dims}, variance={variance_threshold:.1%})"
                
            return labels, opt_k, method_name
            

        elif method.startswith("kmeans"):

            if X.shape[1] > n_dims:
                X_reduced = PCA(n_components=n_dims, random_state=42).fit_transform(X)
            else:
                X_reduced = X
                

            k = min(k_max, max(2, int(np.sqrt(X_reduced.shape[0] / 2))))
            labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(X_reduced)
            return labels, k, f"kmeans (PCA={X_reduced.shape[1]})"
        
        elif method == "hierarchical":
            k = min(k_max, max(2, int(np.sqrt(X.shape[0] / 2))))
            labels = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(X)
            return labels, k, "hierarchical"

        elif method == "hdbscan":
            try:
                import hdbscan
                clusterer = hdbscan.HDBSCAN(min_cluster_size=max(min_cluster_size, 3))
                labels = clusterer.fit_predict(X)
                n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
                return labels, n_clusters, "hdbscan"
            except ImportError:
                logger.warning("hdbscan not installed – falling back to k‑means")
                return self._run_clustering("kmeans", X, k_max, min_cluster_size, n_dims)


        logger.warning(f"Unknown clustering method: {method}. Falling back to kmeans.")
        return self._run_clustering("kmeans", X, k_max, min_cluster_size, n_dims)

    @staticmethod
    def _quality_stats(X: np.ndarray, labels: np.ndarray):
        mask = labels >= 0
        if mask.sum() < 3 or len(set(labels[mask])) < 2:
            return {"silhouette": float("nan"), "share_noise": 1.0 - mask.mean()}
        try:
            sil = silhouette_score(X[mask], labels[mask])
        except Exception:
            sil = float("nan")
        return {
            "silhouette": float(np.round(sil, 3)),
            "share_noise": float(np.round(1.0 - mask.mean(), 3)),
        }