"""
Recommendation Engine Models
Hybrid approach: Content-Based + Popularity scoring
"""

import pickle
import pandas as pd
import numpy as np
import logging
from sklearn.neighbors import NearestNeighbors
from typing import Optional, List, Tuple
from config import MODEL_PATHS

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Hybrid Recommendation Engine
    Combines content-based filtering (similarity) with popularity metrics
    """
    
    def __init__(self):
        self.movies_df = None
        self.vectorizer = None
        self.nn_model = None
        self.vectors = None
        self._load_models()
    
    def _load_models(self):
        """Load pre-trained models and data"""
        try:
            self.movies_df = pickle.load(open(MODEL_PATHS["movies_list"], 'rb'))
            self.vectorizer = pickle.load(open(MODEL_PATHS["vectorizer"], 'rb'))
            
            # Build vectors and NearestNeighbors model
            self.vectors = self.vectorizer.transform(self.movies_df['tags_string']).toarray().astype('float32')
            
            # Normalize vectors for cosine similarity
            norms = np.linalg.norm(self.vectors, axis=1, keepdims=True)
            self.vectors = self.vectors / (norms + 1e-8)
            
            # Build and fit NearestNeighbors model dynamically
            self.nn_model = NearestNeighbors(
                metric="cosine",
                algorithm="brute",
                n_neighbors=31
            )
            self.nn_model.fit(self.vectors)
            
            logger.info("✅ Models loaded successfully")
        except FileNotFoundError as e:
            logger.error(f"Model files not found: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            raise
    
    def is_loaded(self) -> bool:
        """Check if models are loaded"""
        return self.movies_df is not None and self.nn_model is not None
    
    def get_features(self, movie_title: str) -> Optional[dict]:
        """
        Get feature explanation for a movie
        Shows why a movie is recommended
        """
        try:
            movie = self.movies_df[self.movies_df['title'] == movie_title]
            if movie.empty:
                return None
            
            row = movie.iloc[0]
            ov = row.get('overview', '')
            if isinstance(ov, list):
                ov = ' '.join(str(w) for w in ov)
            return {
                'title': row['title'],
                'genres': row.get('genres', []),
                'rating': row.get('vote_average', 0),
                'weighted_score': row.get('weighted_score', 0),
                'popularity': row.get('popularity', 0),
                'overview': str(ov)[:300] + ('...' if len(str(ov)) > 300 else ''),
            }
        except Exception as e:
            logger.error(f"Error getting features for {movie_title}: {e}")
            return None
    
    def recommend(self, movie_title: str, top_n: int = 6) -> Tuple[pd.DataFrame, dict]:
        """
        Get recommendations based on a movie
        
        Returns:
            Tuple of (recommendations_df, source_movie_features)
        """
        try:
            idx = self.movies_df[self.movies_df['title'] == movie_title].index[0]
            query_vec = self.vectors[idx:idx+1]
            
            # Find nearest neighbors
            n_neighbors = max(top_n + 1, 31)
            distances, indices = self.nn_model.kneighbors(query_vec, n_neighbors=n_neighbors)
            movie_indices = indices[0][1:]  # Exclude self
            
            # Get recommendations and sort by weighted score
            recommendations = self.movies_df.iloc[movie_indices].copy()
            recommendations = recommendations.sort_values('weighted_score', ascending=False)
            
            # Get source movie features for explainability
            source_features = self.get_features(movie_title)
            
            return recommendations.head(top_n), source_features
        except IndexError:
            logger.error(f"Movie not found: {movie_title}")
            raise ValueError(f"Movie '{movie_title}' not found in database")
        except Exception as e:
            logger.error(f"Recommendation error: {e}")
            raise
    
    def recommend_from_tags(self, tags_string: str, top_n: int = 6) -> pd.DataFrame:
        """
        Get recommendations from an external movie (via TMDB search)
        Uses the same vectorizer to transform new tags
        """
        try:
            new_vec = self.vectorizer.transform([tags_string]).toarray().astype('float32')
            norms = np.linalg.norm(new_vec, axis=1, keepdims=True)
            new_vec = new_vec / (norms + 1e-8)
            
            n_neighbors = max(top_n, 30)
            distances, indices = self.nn_model.kneighbors(new_vec, n_neighbors=n_neighbors)
            movie_indices = indices[0]
            
            recommendations = self.movies_df.iloc[movie_indices].copy()
            recommendations = recommendations.sort_values('weighted_score', ascending=False)
            
            return recommendations.head(top_n)
        except Exception as e:
            logger.error(f"Error recommending from tags: {e}")
            raise ValueError("Could not generate recommendations from this movie")
    
    def get_trending(self, top_n: int = 12) -> pd.DataFrame:
        """Get trending movies sorted by popularity and rating"""
        try:
            return self.movies_df.nlargest(top_n, 'popularity')[
                ['title', 'movie_id', 'vote_average', 'popularity', 'genres']
            ]
        except Exception as e:
            logger.error(f"Error getting trending: {e}")
            return pd.DataFrame()
    
    def filter_by_genres(self, genres_list: List[str]) -> pd.DataFrame:
        """Filter movies by genres"""
        try:
            mask = self.movies_df['genres'].apply(
                lambda x: isinstance(x, list) and any(g in x for g in genres_list)
            )
            return self.movies_df[mask].sort_values('weighted_score', ascending=False)
        except Exception as e:
            logger.error(f"Error filtering by genres: {e}")
            return pd.DataFrame()
    
    def get_movie_by_title(self, title: str) -> Optional[dict]:
        """Get a specific movie's data"""
        try:
            movie = self.movies_df[self.movies_df['title'] == title]
            if not movie.empty:
                return movie.iloc[0].to_dict()
            return None
        except Exception as e:
            logger.error(f"Error getting movie {title}: {e}")
            return None
    
    def search_movies(self, query: str, limit: int = 10) -> List[str]:
        """Search for movies by title (case-insensitive)"""
        try:
            query_lower = query.lower()
            matches = self.movies_df[
                self.movies_df['title'].str.lower().str.contains(query_lower, na=False)
            ]['title'].head(limit).tolist()
            return matches
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def get_stats(self) -> dict:
        """Get recommendation engine statistics"""
        try:
            avg_rating = float(self.movies_df['vote_average'].mean())
            return {
                'total_movies': len(self.movies_df),
                'avg_rating': round(avg_rating, 1),
                'genres_count': len(set(self._flatten_list(self.movies_df['genres'])))
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'total_movies': 'N/A', 'avg_rating': 0, 'genres_count': 'N/A'}
    
    @staticmethod
    def _flatten_list(list_of_lists):
        """Flatten list of lists"""
        return [item for sublist in list_of_lists for item in (sublist if isinstance(sublist, list) else [sublist])]


# Global engine instance
recommendation_engine = None


def get_engine() -> RecommendationEngine:
    """Get or initialize recommendation engine"""
    global recommendation_engine
    if recommendation_engine is None:
        recommendation_engine = RecommendationEngine()
    return recommendation_engine
