"""
Utility functions and API service layer
Handles TMDB API calls, error handling, logging
"""

import logging
import requests
import streamlit as st
from typing import Optional, Dict, Any
from config import TMDB_API_KEY, TMDB_BASE_URL, API_TIMEOUT, TMDB_IMAGE_BASE

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIError(Exception):
    """Custom exception for API errors"""
    pass


@st.cache_data(ttl=86400)
def _get_trailer_cached(movie_id: int, api_key: str) -> Optional[str]:
    """Cached trailer fetch (module-level for proper st.cache_data hashing)"""
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos"
        resp = requests.get(url, params={"api_key": api_key, "language": "en-US"}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        for video in data.get('results', []):
            if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                return f"https://www.youtube.com/watch?v={video['key']}"
        return None
    except Exception:
        return None


class TMDBService:
    """Service for TMDB API interactions with error handling"""
    
    def __init__(self, api_key: str = TMDB_API_KEY):
        self.api_key = api_key
        self.base_url = TMDB_BASE_URL
        self.timeout = API_TIMEOUT
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make API request with error handling
        
        Args:
            endpoint: API endpoint (e.g., "/movie/550")
            params: Query parameters
            
        Returns:
            JSON response data
            
        Raises:
            APIError: If request fails
        """
        if params is None:
            params = {}
        
        params["api_key"] = self.api_key
        
        try:
            response = requests.get(
                f"{self.base_url}{endpoint}",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"API timeout for {endpoint}")
            raise APIError(f"API request timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error for {endpoint}")
            raise APIError("Network error. Please check your connection.")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code} for {endpoint}")
            raise APIError(f"API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise APIError(f"An unexpected error occurred: {str(e)}")
    
    def fetch_poster(self, movie_id: int) -> str:
        """Fetch movie poster URL"""
        try:
            data = self._make_request(f"/movie/{movie_id}", {"language": "en-US"})
            poster_path = data.get('poster_path')
            if poster_path:
                return f"{TMDB_IMAGE_BASE}/w500{poster_path}"
            return "https://via.placeholder.com/500x750?text=Poster+Not+Found"
        except APIError:
            return "https://via.placeholder.com/500x750?text=Poster+Not+Found"
    
    def fetch_backdrop(self, movie_id: int) -> Optional[str]:
        """Fetch movie backdrop URL"""
        try:
            data = self._make_request(f"/movie/{movie_id}")
            backdrop_path = data.get('backdrop_path')
            if backdrop_path:
                return f"{TMDB_IMAGE_BASE}/original{backdrop_path}"
            return None
        except APIError:
            return None
    
    def get_movie_details(self, movie_id: int) -> Optional[Dict]:
        """Get detailed movie information"""
        try:
            return self._make_request(
                f"/movie/{movie_id}",
                {"language": "en-US", "append_to_response": "credits"}
            )
        except APIError as e:
            logger.error(f"Failed to fetch details for movie {movie_id}: {e}")
            return None
    
    def get_movie_trailer(self, movie_id: int) -> Optional[str]:
        """Get YouTube trailer URL for movie"""
        return _get_trailer_cached(movie_id, self.api_key)
    
    def search_movie(self, query: str) -> Optional[Dict]:
        """Search for movie by title"""
        try:
            data = self._make_request("/search/movie", {"query": query})
            if data.get('results'):
                movie = data['results'][0]
                return self.get_movie_details(movie['id'])
            return None
        except APIError as e:
            logger.error(f"Search failed for '{query}': {e}")
            return None
    
    def get_watch_providers(self, movie_id: int, country: str = "US") -> Dict:
        """Get streaming/rent/buy providers for a movie via TMDB"""
        try:
            data = self._make_request(f"/movie/{movie_id}/watch/providers")
            results = data.get('results', {})
            region = results.get(country, {})
            return {
                'stream': region.get('flatrate', []),
                'rent':   region.get('rent', []),
                'buy':    region.get('buy', []),
                'link':   region.get('link', ''),
            }
        except APIError:
            return {'stream': [], 'rent': [], 'buy': [], 'link': ''}

    def get_external_movie_tags(self, query: str) -> tuple[Optional[str], Optional[Dict]]:
        """
        Get movie tags from external search for content-based recommendations
        
        Returns:
            Tuple of (tags_string, movie_details)
        """
        try:
            details = self.search_movie(query)
            if not details:
                return None, None
            
            # Extract tags from movie metadata
            genres = [g['name'].replace(" ", "").lower() 
                     for g in details.get('genres', [])]
            cast = [c['name'].replace(" ", "").lower() 
                   for c in details.get('credits', {}).get('cast', [])[:3]]
            crew = [c['name'].replace(" ", "").lower() 
                   for c in details.get('credits', {}).get('crew', [])
                   if c['job'] == 'Director'][:1]
            
            overview = details.get('overview', '').lower().split()
            tags = overview + genres + cast + crew
            
            return " ".join(tags), details
        except Exception as e:
            logger.error(f"Failed to extract tags for '{query}': {e}")
            return None, None


# Initialize global service instance
tmdb_service = TMDBService()


def safe_divide(numerator, denominator, default=0):
    """Safely divide avoiding division by zero"""
    if denominator == 0:
        return default
    return numerator / denominator


def format_movie_title(title: str, max_length: int = 30) -> str:
    """Format movie title for display"""
    if len(title) > max_length:
        return title[:max_length - 3] + "..."
    return title
