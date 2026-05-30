import streamlit as st
import pickle
import pandas as pd
import requests
import numpy as np
import random
from sklearn.neighbors import NearestNeighbors

# Set Page Config early
st.set_page_config(
    page_title="Cinemagic | Hybrid AI Hub", 
    layout="wide", 
    page_icon="🎬",
    initial_sidebar_state="expanded"
)

# --- Optimized API Tools (with Caching) ---
@st.cache_data(ttl=86400) # Cache for 24 hours
def fetch_poster(movie_id):
    api_key = "8265bd1679663a7ea12ac168da84d2e8"
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&language=en-US"
        data = requests.get(url, timeout=5).json()
        poster_path = data.get('poster_path')
        if poster_path:
            return "https://image.tmdb.org/t/p/w500/" + poster_path
        return "https://via.placeholder.com/500x750?text=Poster+Not+Found"
    except:
        return "https://via.placeholder.com/500x750?text=Poster+Not+Found"

@st.cache_data(ttl=86400)
def fetch_backdrop(movie_id):
    api_key = "8265bd1679663a7ea12ac168da84d2e8"
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}"
        data = requests.get(url, timeout=5).json()
        path = data.get('backdrop_path')
        if path:
            return f"https://image.tmdb.org/t/p/original/{path}"
        return None
    except:
        return None

def set_backdrop(url):
    if url:
        st.markdown(f"""
        <style>
        .stApp {{
            background: linear-gradient(rgba(10, 16, 23, 0.8), rgba(10, 16, 23, 0.95)), 
                        url("{url}");
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        }}
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        .stApp {
            background-color: #060d17;
        }
        </style>
        """, unsafe_allow_html=True)

@st.cache_data(ttl=86400)
def get_movie_trailer(movie_id):
    api_key = "8265bd1679663a7ea12ac168da84d2e8"
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={api_key}&language=en-US"
        data = requests.get(url, timeout=5).json()
        for video in data.get('results', []):
            if video['type'] == 'Trailer' and video['site'] == 'YouTube':
                return f"https://www.youtube.com/watch?v={video['key']}"
        return None
    except:
        return None

@st.cache_data(ttl=3600)
def get_movie_details(movie_id):
    api_key = "8265bd1679663a7ea12ac168da84d2e8"
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&language=en-US"
        return requests.get(url, timeout=5).json()
    except:
        return None

def get_external_movie_tags(query):
    api_key = "8265bd1679663a7ea12ac168da84d2e8"
    try:
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={query}"
        res = requests.get(search_url).json()
        if not res['results']: 
            return None, None
        
        movie = res['results'][0]
        movie_id = movie['id']
        
        details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&append_to_response=credits"
        details = requests.get(details_url).json()
        
        genres = [g['name'].replace(" ", "").lower() for g in details.get('genres', [])]
        cast = [c['name'].replace(" ", "").lower() for c in details.get('credits', {}).get('cast', [])[:3]]
        crew = [c['name'].replace(" ", "").lower() for c in details.get('credits', {}).get('crew', []) if c['job'] == 'Director'][:1]
        
        tags = details.get('overview', '').lower().split() + genres + cast + crew
        return " ".join(tags), details
    except:
        return None, None

# --- Optimized Loading Tools ---
@st.cache_resource
def load_data():
    try:
        movies_df = pickle.load(open('movies_list.pkl', 'rb'))
        movies = pd.DataFrame(movies_df)
        vectorizer = pickle.load(open('vectorizer.pkl', 'rb'))
        # Build vector matrix from tags and fit a NearestNeighbors model (no FAISS needed)
        vectors = vectorizer.transform(movies['tags_string'])
        nn_model = NearestNeighbors(n_neighbors=31, metric='cosine', algorithm='brute')
        nn_model.fit(vectors)
        return movies, nn_model, vectorizer, vectors
    except Exception as e:
        st.error(f"Load error: {e}")
        return None, None, None, None

def recommend(movie_title, movies, nn_model, vectors):
    idx = movies[movies['title'] == movie_title].index[0]
    query_vec = vectors[idx]
    distances, indices = nn_model.kneighbors(query_vec, n_neighbors=31)
    movie_indices = indices[0][1:]  # skip self
    recommend_pool = movies.iloc[movie_indices].copy()
    recommend_pool = recommend_pool.sort_values('weighted_score', ascending=False)
    return recommend_pool.head(6)

def recommend_external(tags_string, movies, nn_model, vectorizer):
    new_vec = vectorizer.transform([tags_string])
    distances, indices = nn_model.kneighbors(new_vec, n_neighbors=30)
    movie_indices = indices[0]
    recommend_pool = movies.iloc[movie_indices].copy()
    recommend_pool = recommend_pool.sort_values('weighted_score', ascending=False)
    return recommend_pool.head(6)

# --- Recommendation Logic Extensions ---
MOODS = {
    "😊 Happy": ["Comedy", "Animation", "Family"],
    "😢 Sad": ["Drama", "Romance"],
    "🔥 Action": ["Action", "Adventure", "Thriller"],
    "🧠 Mind-Blowing": ["Sci-Fi", "Mystery", "Fantasy"],
    "💖 Romantic": ["Romance", "Comedy"]
}

def get_bot_response(user_input):
    user_input = user_input.lower()
    if any(word in user_input for word in ["happy", "laugh", "comedy", "fun", "funny", "cheer", "light"]):
        return "😄 Great choice! Here are some feel-good picks for you!", "Comedy"
    elif any(word in user_input for word in ["scary", "horror", "creep", "ghost", "dark", "thriller", "afraid", "fear"]):
        return "👻 Feeling brave? Try some spine-chillers!", "Horror"
    elif any(word in user_input for word in ["future", "space", "sci-fi", "scifi", "science", "robot", "alien", "mind", "galaxy", "technology"]):
        return "🚀 Prepare to have your mind warped!", "Sci-Fi"
    elif any(word in user_input for word in ["love", "romance", "romantic", "date", "heart", "relationship", "couple"]):
        return "❤️ Love is in the air! Here's some romance for you.", "Romance"
    elif any(word in user_input for word in ["action", "fight", "war", "battle", "explode", "adventure", "hero", "superhero"]):
        return "💥 Let's get the adrenaline pumping!", "Action"
    elif any(word in user_input for word in ["animated", "cartoon", "pixar", "disney", "family", "kids", "children"]):
        return "🎨 Fun for everyone! Here are some animated gems.", "Animation"
    elif any(word in user_input for word in ["sad", "cry", "emotional", "drama", "moving", "touch", "feel"]):
        return "🎭 Sometimes a good cry is what we need.", "Drama"
    elif any(word in user_input for word in ["mystery", "detective", "crime", "whodunit", "clue", "suspense"]):
        return "🔍 Let's solve a mystery together!", "Mystery"
    elif any(word in user_input for word in ["bored", "nothing", "anything", "random", "suggest", "recommend", "what"]):
        return "🎲 Let me surprise you with something great!", "Action"
    return "🤖 I'm your AI Movie Scout! Try: 'scary movie', 'something funny', 'romantic film', 'sci-fi', 'action', etc.", None

# --- Premium Aesthetics (CSS) ---
st.markdown("""
<style>
    /* Typography */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;800&family=Outfit:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        color: #ffffff !important;
        font-family: 'Outfit', sans-serif;
    }

    .premium-title {
        font-family: 'Montserrat', sans-serif;
        font-size: 5.5rem;
        font-weight: 800;
        background: linear-gradient(to right, #e50914, #ff4b2b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: -10px;
        letter-spacing: -3px;
    }
    
    .premium-subtitle {
        text-align: center;
        color: #ddd;
        font-size: 1rem;
        margin-bottom: 40px;
        letter-spacing: 4px;
        text-transform: uppercase;
    }

    /* Fix labels visibility */
    label, .stMarkdown, p, span {
        color: #ffffff !important;
    }

    /* Card Styling */
    .movie-card {
        background: rgba(22, 28, 36, 0.7);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        overflow: hidden;
        margin-bottom: 25px;
    }
    
    .movie-card:hover {
        transform: translateY(-10px);
        border-color: #e50914;
        box-shadow: 0 15px 30px rgba(0,0,0,0.8);
    }
    
    /* Taste Profile Section */
    .taste-label {
        font-size: 0.8rem;
        color: #aaa;
        display: flex;
        justify-content: space-between;
        margin-bottom: 5px;
    }
    .taste-bar-bg {
        background: #1a212a;
        height: 6px;
        border-radius: 3px;
        overflow: hidden;
        margin-bottom: 12px;
    }
    .taste-bar-fill {
        background: #e50914;
        height: 100%;
    }

    /* Mood Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        background: rgba(255,255,255,0.05);
        color: white !important;
        font-weight: 500;
        border: 1px solid rgba(255,255,255,0.1);
        padding: 12px;
        transition: 0.2s;
    }
    
    .stButton>button:hover {
        background: #e50914 !important;
        border-color: #e50914;
        color: white !important;
    }

    /* Chatbot Bubble */
    .chat-bubble {
        background: #1a212a;
        padding: 15px;
        border-radius: 15px 15px 15px 0px;
        border: 1px solid #303741;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if 'watchlist' not in st.session_state: st.session_state.watchlist = []
if 'taste_history' not in st.session_state: st.session_state.taste_history = []
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'current_backdrop' not in st.session_state: st.session_state.current_backdrop = None
if 'active_mood_genres' not in st.session_state: st.session_state.active_mood_genres = None
if 'active_mood_name' not in st.session_state: st.session_state.active_mood_name = None

def update_taste_profile(genres_list):
    if genres_list and isinstance(genres_list, list):
        st.session_state.taste_history.extend(genres_list)

# --- Main App Logic ---
movies, nn_model, vectorizer, vectors = load_data()

if movies is None:
    st.error("🚨 **Model files not found!**")
    st.info("Please run `python recommender.py` to generate the engine.")
    st.stop()

# Dynamic Backdrop
set_backdrop(st.session_state.current_backdrop)

# Sidebar - AI & Profile
with st.sidebar:
    st.markdown('<h1 style="color:#e50914; font-family:Montserrat; font-weight:800; font-size:2rem; margin-bottom:0;">CINEMAGIC</h1>', unsafe_allow_html=True)
    st.caption("AI-Powered Discovery Engine")
    
    st.markdown("---")
    st.subheader("🤖 AI Movie Scout")
    user_msg = st.text_input("Ask me for a mood or genre:", placeholder="e.g. scary movie, something funny, sci-fi...", key="chat_input")
    if st.button("Ask 🎬", key="chat_submit"):
        if user_msg:
            resp, genre_filter = get_bot_response(user_msg)
            st.session_state.chat_history.append({"msg": user_msg, "resp": resp, "genre": genre_filter})
            st.rerun()
    
    if st.session_state.chat_history:
        for item in st.session_state.chat_history[-3:]:
            st.markdown(f'<div class="chat-bubble">🧑 {item["msg"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="chat-bubble">🤖 {item["resp"]}</div>', unsafe_allow_html=True)
            if item["genre"]:
                genre_display = item['genre'].replace(" ", "_").lower()
                if st.button(f"🔍 Show {item['genre']} movies", key=f"genre_btn_{genre_display}_{len(st.session_state.chat_history)}"):
                    st.session_state.active_mood_genres = [item['genre']]
                    st.session_state.active_mood_name = item['genre']
                    st.rerun()
    
    st.markdown("---")
    st.subheader("📊 Your Taste Profile")
    if not st.session_state.taste_history:
        st.caption("Start browsing to build your profile!")
    else:
        counts = pd.Series(st.session_state.taste_history).value_counts().head(5)
        total = counts.sum()
        for genre, count in counts.items():
            perc = int((count / total) * 100)
            st.markdown(f'<div class="taste-label"><span>{genre}</span><span>{perc}%</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="taste-bar-bg"><div class="taste-bar-fill" style="width:{perc}%"></div></div>', unsafe_allow_html=True)

    st.markdown("---")
    if st.session_state.watchlist:
        st.subheader("📌 Watchlist")
        for m in st.session_state.watchlist[:3]:
            st.caption(f"✅ {m['title']}")
    if st.button("🗑️ Reset Profile"):
        st.session_state.watchlist = []
        st.session_state.taste_history = []
        st.session_state.current_backdrop = None
        st.session_state.active_mood_genres = None
        st.session_state.chat_history = []
        st.rerun()

# Header
st.markdown('<h1 class="premium-title">CINEMAGIC</h1>', unsafe_allow_html=True)
st.markdown('<p class="premium-subtitle">Expert AI Recommendations • Modern Discovery • Cinematic UI</p>', unsafe_allow_html=True)

# 1. Mood Selection Grid
st.markdown("### 🎭 Choose Your Vibe")
m_cols = st.columns(len(MOODS))
for i, (mood, genres) in enumerate(MOODS.items()):
    with m_cols[i]:
        is_active = st.session_state.active_mood_genres == genres
        label = f"✅ {mood}" if is_active else mood
        if st.button(label, key=f"mood_{i}"):
            if is_active:
                st.session_state.active_mood_genres = None
                st.session_state.active_mood_name = None
            else:
                st.session_state.active_mood_genres = genres
                st.session_state.active_mood_name = mood
            st.rerun()
selected_vibe_genres = st.session_state.active_mood_genres

# 2. Hero Search Bar
st.markdown("---")
c_input, c_btn = st.columns([3, 1])
with c_input:
    mode = st.radio("Search Mode:", ["Database Search", "Global Search (TMDB)"], horizontal=True)
    if mode == "Database Search":
        if selected_vibe_genres:
            st.success("Mood filter active!")
            matches = movies[movies['genres'].apply(lambda x: any(g in x for g in selected_vibe_genres))]
            selected_movie = st.selectbox('Pick a recommendation:', matches['title'].values, key="vibe_sel")
        else:
            default_val = 0
            if 'surprise_movie' in st.session_state:
                try: default_val = list(movies['title'].values).index(st.session_state.surprise_movie); del st.session_state.surprise_movie
                except: pass
            selected_movie = st.selectbox('Start with a movie you like:', movies['title'].values, index=default_val)
    else:
        selected_movie = st.text_input("Enter any movie name globally:", placeholder="e.g. Interstellar")

with c_btn:
    st.write("") # Spacer
    st.write("") # Spacer
    st.write("") # Spacer
    magic_btn = st.button('🚀 Magic Recommend')
    if st.button('🎲 Surprise Me!'):
        st.session_state.surprise_movie = movies['title'].sample(1).iloc[0]
        st.rerun()

# 3. Results Engine
if (magic_btn or selected_vibe_genres) and selected_movie:
    with st.spinner('✨ Consulting the AI oracle...'):
        if mode == "Database Search":
            recs = recommend(selected_movie, movies, nn_model, vectors)
            searched_id = movies[movies['title'] == selected_movie]['movie_id'].iloc[0]
            details = get_movie_details(searched_id)
            row = movies[movies['title'] == selected_movie].iloc[0]
            update_taste_profile(row['genres'])
        else:
            tags, details = get_external_movie_tags(selected_movie)
            if tags:
                recs = recommend_external(tags, movies, nn_model, vectorizer)
                selected_movie = details['title']
                update_taste_profile([g['name'] for g in details.get('genres', [])])
            else:
                st.error("Global movie search failed. Try a different spelling.")
                st.stop()
        
        if details:
            st.session_state.current_backdrop = fetch_backdrop(details['id'])
            set_backdrop(st.session_state.current_backdrop)

        if details:
            rc1, rc2 = st.columns([1, 4])
            with rc1:
                p_path = details.get('poster_path')
                p_url = f"https://image.tmdb.org/t/p/w500/{p_path}" if p_path else "https://via.placeholder.com/500x750"
                st.image(p_url)
                wl_cols = st.columns([1, 1])
                with wl_cols[0]:
                    if st.button("❤️ Add to WL", key="wl_main"):
                        if selected_movie not in [m['title'] for m in st.session_state.watchlist]:
                            st.session_state.watchlist.append({'title': selected_movie, 'poster': p_url})
                            st.success(f"Added to watchlist!")
                with wl_cols[1]:
                    if st.button("📊 More Info", key="info_main"):
                        st.info(f"⭐ {details.get('vote_average', 'N/A')} | ⏱️ {details.get('runtime', 'N/A')} min")
            with rc2:
                st.markdown(f"## {selected_movie}")
                st.markdown(f"**{details.get('vote_average', 'N/A')} ⭐** | {details.get('runtime', 'N/A')} min | {details.get('release_date', 'N/A')[:4]}")
                st.write(details.get('overview', 'No summary available.'))
                tr = get_movie_trailer(details['id'])
                if tr:
                    with st.expander("📺 Watch Official Trailer"): st.video(tr)

        st.markdown("---")
        st.subheader(f"Because you liked **{selected_movie}**...")
        res_cols = st.columns(6)
        for i, (ridx, rrow) in enumerate(recs.iterrows()):
            with res_cols[i]:
                rp = fetch_poster(rrow['movie_id'])
                st.markdown(f'<div class="movie-card"><img src="{rp}" style="width:100%; cursor:pointer;"><div style="padding:10px;"><div style="font-size:0.8rem; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{rrow["title"]}</div><div style="color:#e50914; font-size:0.8rem;">{rrow["vote_average"]} ⭐</div></div></div>', unsafe_allow_html=True)
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button(f"🎬", key=f"rec_{ridx}", help="Get recommendations"):
                        st.session_state.surprise_movie = rrow['title']
                        st.session_state.active_mood_genres = None
                        st.rerun()
                with col2:
                    if st.button(f"❤️", key=f"wl_{ridx}", help="Add to watchlist"):
                        if rrow['title'] not in [m['title'] for m in st.session_state.watchlist]:
                            st.session_state.watchlist.append({'title': rrow['title'], 'poster': rp})
                            st.success(f"Added {rrow['title']}!")

else:
    st.markdown("---")
    st.subheader("🔥 Trending Content")
    trend_df = movies.sort_values('popularity', ascending=False).head(12)
    t_cols = st.columns(6)
    for i, (tidx, trow) in enumerate(trend_df.iterrows()):
        with t_cols[i % 6]:
            tp = fetch_poster(trow['movie_id'])
            st.markdown(f'<div class="movie-card"><img src="{tp}" style="width:100%; cursor:pointer;"><div style="padding:10px;"><div style="font-size:0.8rem; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{trow["title"]}</div><div style="color:#e50914; font-size:0.8rem;">{trow["vote_average"]} ⭐</div></div></div>', unsafe_allow_html=True)
            tcol1, tcol2 = st.columns([1, 1])
            with tcol1:
                if st.button(f"🎬", key=f"trend_{tidx}", help="Get recommendations"):
                    st.session_state.surprise_movie = trow['title']
                    st.rerun()
            with tcol2:
                if st.button(f"❤️", key=f"twl_{tidx}", help="Add to watchlist"):
                    if trow['title'] not in [m['title'] for m in st.session_state.watchlist]:
                        st.session_state.watchlist.append({'title': trow['title'], 'poster': tp})
                        st.success(f"Added {trow['title']}!")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #888;'>Premium AI Recommendation Engine | Built for Professional Portfolio</p>", unsafe_allow_html=True)
