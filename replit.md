# CINEMAGIC - Hybrid Movie Recommendation System

## Project Topic
**Hybrid Movie Recommendation System using Collaborative and Content-Based Filtering using ML**

## Overview
A Netflix-inspired Streamlit web app that implements a hybrid ML recommendation engine:
- **Content-Based Filtering**: TF-IDF vectorization on movie metadata (genres, cast, crew, keywords, overview) + cosine similarity via NearestNeighbors
- **Collaborative Filtering**: Bayesian-weighted scoring (vote_count × vote_average × popularity) reflecting collective user preferences
- **Hybrid Score**: 55% Collaborative + 45% Content similarity for final ranking

## Architecture
- **app.py** — Main Streamlit UI (Netflix-style dark theme, complete redesign)
- **models.py** — RecommendationEngine class (NearestNeighbors, content-based + collaborative)
- **utils.py** — TMDB API service layer (posters, details, trailers, global search)
- **config.py** — Configuration and environment variables
- **recommender.py** — Additional recommender utilities
- **movies_list.pkl** — Pre-trained movie dataset (4,806 movies)
- **vectorizer.pkl** — Pre-trained TF-IDF vectorizer

## Features
- 🎬 Netflix/Letterboxd-inspired dark UI with real movie posters
- 🔍 Database search (4,800+ movies with autocomplete dropdown)
- 🌐 Global TMDB search (any movie worldwide)
- 🎭 Mood/genre filter buttons (Happy, Drama, Action, Sci-Fi, Romance, Horror)
- 🔥 Trending Now section (ranked by audience score)
- 📂 5 genre browsing rows (Sci-Fi, Action, Comedy, Horror, Drama)
- 🧠 Hybrid score visualization on every recommendation card (Content + Collab + Hybrid bars)
- 📊 Hybrid Algorithm explanation panel ("Why Recommended?")
- 🤖 AI Movie Scout chatbot (mood-to-genre matching)
- ❤️ Watchlist with poster thumbnails
- 📈 User Taste Profile with genre preference bars
- 📺 Movie trailers (YouTube embed)
- 🔬 "How It Works" section on homepage

## Setup
- Python 3.12
- Dependencies: `requirements.txt` (pip install)
- Streamlit config: `.streamlit/config.toml` (port 5000, host 0.0.0.0)
- TMDB API key in `config.py` (default key included)

## Running
Workflow "Start application": `streamlit run app.py`
- Port: 5000 | Host: 0.0.0.0

## Deployment
- Target: autoscale
- Run: `streamlit run app.py --server.port=5000 --server.address=0.0.0.0`
