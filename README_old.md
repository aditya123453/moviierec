# 🎬 CINEMAGIC | Hybrid Movie Recommender

A premium, AI-powered movie recommendation engine that blends content-based filtering with global popularity metrics to give you the perfect "What to watch next" suggestion.

## ✨ Features
- **Hybrid Recommendation Engine**: Combines metadata similarity (genres, keywords, cast, crew) with community-driven weighted ratings.
- **Premium Dark UI**: A sleek, Netflix-inspired interface built with Streamlit and custom CSS.
- **Real-time Metadata**: Fetches movie overviews, release dates, and high-quality posters via TMDB API.
- **Data Caching**: Optimized performance using Streamlit's resource caching for heavy model files.
- **Discovery Mode**: Exploration tab for top-rated hits across the database.

## 🛠️ Tech Stack
- **Core**: Python, Pandas, Scikit-learn
- **Frontend**: Streamlit, HTML/CSS (Glassmorphism design)
- **Data**: TMDB 5k Dataset, TMDB API

## 📂 Project Structure
- `recommender.py`: Data preprocessing, Weighted Rating calculation, and Similarity Matrix generation.
- `app.py`: The interactive web application with premium aesthetics.
- `movies_list.pkl`: Processed movie database (includes pre-calculated scores).
- `similarity.pkl`: Compressed Cosine Similarity matrix (180MB+).

## 🎮 Getting Started
1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Generate Models** (Run once):
    ```bash
    python recommender.py
    ```
3.  **Launch Cinemagic**:
    ```bash
    streamlit run app.py
    ```

---
*Developed as a Premium ML Portfolio Piece.*
