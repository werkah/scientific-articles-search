import numpy as np
import logging
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
import warnings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class AdaptiveClusteringOptimizer:

    
    def __init__(self):
        self.scores_history = {}
        self.best_params = {}
        warnings.filterwarnings("ignore", category=UserWarning)
        
    def optimize_pca_dimensions(self, X, variance_threshold=0.9, max_dims=100):

        n_samples, n_features = X.shape
        max_possible_dims = min(n_samples, n_features, max_dims)
        
        if n_features <= 50:

            return n_features, X

        pca = PCA(n_components=max_possible_dims)
        pca.fit(X)
        

        cumulative_variance = np.cumsum(pca.explained_variance_ratio_)
        optimal_dims = np.argmax(cumulative_variance >= variance_threshold) + 1
        

        optimal_dims = max(optimal_dims, 2)
        

        if optimal_dims < n_features:
            pca = PCA(n_components=optimal_dims)
            X_reduced = pca.fit_transform(X)

            return optimal_dims, X_reduced
        else:

            return n_features, X
            
    def optimize_n_clusters(self, X, min_clusters=2, max_clusters=20, method="kmeans"):

        max_clusters = min(max_clusters, X.shape[0] // 5, 20)
        min_clusters = min(min_clusters, max_clusters - 1)
        
        if min_clusters >= max_clusters:
            min_clusters = 2
            max_clusters = max(3, min(X.shape[0] // 5, 20))
            

        silhouette_scores = []
        ch_scores = []
        db_scores = []
        labels_list = []
        

        for n_clusters in range(min_clusters, max_clusters + 1):
            try:
                if method == "kmeans":

                    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=20, max_iter=500)
                elif method == "hierarchical":

                    linkage_methods = ["ward", "complete", "average"]
                    sub_silhouette_scores = []
                    sub_labels_list = []
                    
                    for linkage in linkage_methods:
                        try:
                            sub_model = AgglomerativeClustering(n_clusters=n_clusters, linkage=linkage)
                            sub_labels = sub_model.fit_predict(X)
                            
                            if len(np.unique(sub_labels)) > 1:
                                sub_score = silhouette_score(X, sub_labels)
                                sub_silhouette_scores.append(sub_score)
                                sub_labels_list.append(sub_labels)
                            else:
                                sub_silhouette_scores.append(-1)
                                sub_labels_list.append(sub_labels)
                        except Exception:
                            sub_silhouette_scores.append(-1)
                            sub_labels_list.append(np.zeros(X.shape[0]))
                    

                    if sub_silhouette_scores:
                        best_linkage_idx = np.argmax(sub_silhouette_scores)
                        model = None 
                        labels = sub_labels_list[best_linkage_idx]
                        best_linkage = linkage_methods[best_linkage_idx]
                    else:

                        model = AgglomerativeClustering(n_clusters=n_clusters)
                else:

                    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                    

                if model is not None:
                    labels = model.fit_predict(X)
                labels_list.append(labels)
                

                if len(np.unique(labels)) > 1:  
                    silhouette = silhouette_score(X, labels)
                    ch_score = calinski_harabasz_score(X, labels)
                    db_score = davies_bouldin_score(X, labels)
                    
                    silhouette_scores.append(silhouette)
                    ch_scores.append(ch_score)
                    db_scores.append(db_score)
                    
                    logger.info(f"  For {n_clusters} clusters: silhouette={silhouette:.4f}, " +
                               f"CH={ch_score:.1f}, DB={db_score:.4f}")
                else:
                    silhouette_scores.append(-1)
                    ch_scores.append(0)
                    db_scores.append(float('inf'))
            except Exception as e:
                logger.warning(f"Błąd dla {n_clusters} klastrów: {e}")
                silhouette_scores.append(-1)
                ch_scores.append(0)
                db_scores.append(float('inf'))
                labels_list.append(np.zeros(X.shape[0]))

        if max(silhouette_scores) > min(silhouette_scores):
            norm_silhouette = [(s - min(silhouette_scores)) / (max(silhouette_scores) - min(silhouette_scores)) 
                               if s > -1 else 0 for s in silhouette_scores]
        else:
            norm_silhouette = [1 if s > -1 else 0 for s in silhouette_scores]
            
        if max(ch_scores) > 0:
            norm_ch = [c / max(ch_scores) if max(ch_scores) > 0 else 0 for c in ch_scores]
        else:
            norm_ch = [0] * len(ch_scores)
            
        if min(db_scores) < float('inf'):
            norm_db = [1 - (d - min(db_scores)) / (max(db_scores) - min(db_scores)) 
                      if d < float('inf') and max(db_scores) > min(db_scores) else 0 
                      for d in db_scores]
        else:
            norm_db = [0] * len(db_scores)
        

        silhouette_weight = 0.6
        ch_weight = 0.25
        db_weight = 0.15
        
        composite_scores = [
            (silhouette_weight * ns + ch_weight * nc + db_weight * nd) 
            for ns, nc, nd in zip(norm_silhouette, norm_ch, norm_db)
        ]

        penalty_factor = 0.01  
        adjusted_scores = [
            score - penalty_factor * (i + min_clusters) 
            for i, score in enumerate(composite_scores)
        ]

        if max(silhouette_scores) < 0.1:
            logger.warning("All clustering configurations have very low silhouette scores (<0.1). "
                          "Data may not have a strong cluster structure.")
        

        best_idx = np.argmax(adjusted_scores)
        optimal_n_clusters = min_clusters + best_idx
        optimal_labels = labels_list[best_idx]
        

        self.scores_history = {
            'n_clusters_range': list(range(min_clusters, max_clusters + 1)),
            'silhouette': silhouette_scores,
            'calinski_harabasz': ch_scores,
            'davies_bouldin': db_scores,
            'composite': composite_scores,
            'adjusted_scores': adjusted_scores
        }
        
        self.best_params['n_clusters'] = optimal_n_clusters
        
        logger.info(f"Optimal number of clusters: {optimal_n_clusters} " +
                   f"(silhouette={silhouette_scores[best_idx]:.4f}, " +
                   f"composite={composite_scores[best_idx]:.4f})")
        
        return optimal_n_clusters, optimal_labels
        
    def get_optimal_parameters(self, X, method="kmeans", 
                               variance_threshold=0.9, max_pca_dims=100,
                               min_clusters=2, max_clusters=20):

        n_dims, X_reduced = self.optimize_pca_dimensions(X, variance_threshold, max_pca_dims)
        

        n_clusters, labels = self.optimize_n_clusters(X_reduced, min_clusters, max_clusters, method)

        self.best_params = {
            'method': method,
            'pca_dimensions': n_dims,
            'n_clusters': n_clusters,
            'variance_threshold': variance_threshold
        }

        if 'silhouette' in self.scores_history and self.scores_history['silhouette']:
            best_idx = self.scores_history['n_clusters_range'].index(n_clusters) if n_clusters in self.scores_history['n_clusters_range'] else 0
            if 0 <= best_idx < len(self.scores_history['silhouette']):
                self.best_params['silhouette_score'] = self.scores_history['silhouette'][best_idx]
        
        return self.best_params, labels
        
    def get_parameter_history(self):

        return self.scores_history
        
