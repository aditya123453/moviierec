"""
CINEMAGIC — Hybrid Movie Recommendation System
Content-Based + Collaborative Filtering · Letterboxd-inspired UI
College ML Project
"""

import json, os, math, logging
import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional, Dict, List

from config import (
    APP_TITLE, APP_ICON, RECOMMENDATIONS_COUNT,
    TRENDING_COUNT, CHAT_HISTORY_DISPLAY, ENABLE_TRAILER,
)
from models import get_engine
from utils import tmdb_service, format_movie_title, APIError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Profiles directory ──────────────────────────────────────────────────────
PROFILES_DIR = "profiles"
os.makedirs(PROFILES_DIR, exist_ok=True)

def _profile_path(username: str) -> str:
    safe = username.strip().lower().replace(" ", "_") or "guest"
    return os.path.join(PROFILES_DIR, f"{safe}.json")

def load_profile(username: str) -> dict:
    path = _profile_path(username)
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {"watchlist": [], "ratings": {}, "diary": [], "taste": []}

def save_profile(username: str, data: dict):
    try:
        with open(_profile_path(username), "w") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Could not save profile: {e}")

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CineMagic",
    layout="wide",
    page_icon="🎬",
    initial_sidebar_state="expanded",
)

# ── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* Reset */
html,body,[class*="css"]{font-family:'Inter',sans-serif;background:#14181c;color:#99aabb;}
#MainMenu,footer{visibility:hidden;}

/* Sidebar */
section[data-testid="stSidebar"]{background:#0c0f12;border-right:1px solid #1e2830;}

/* All buttons base */
.stButton>button{
  border-radius:6px;font-weight:500;font-size:.82rem;
  border:1px solid #2a3540;background:#1a2230;color:#99aabb;
  transition:all .18s;padding:5px 10px;
}
.stButton>button:hover{background:#e50914!important;border-color:#e50914!important;color:#fff!important;}

/* Mood chips — bigger */
div[data-testid="column"] .stButton>button.mood-btn{font-size:.9rem;padding:8px 0;}

/* ── Film card ── */
.film-card{
  position:relative;border-radius:4px;overflow:hidden;
  aspect-ratio:2/3;background:#0c0f12;cursor:pointer;
  transition:transform .2s,box-shadow .2s;
}
.film-card:hover{transform:translateY(-4px);box-shadow:0 12px 36px rgba(0,0,0,.8);}
.film-card img{width:100%;height:100%;object-fit:cover;display:block;}
.film-card .overlay{
  position:absolute;bottom:0;left:0;right:0;
  background:linear-gradient(transparent,rgba(0,0,0,.92));
  padding:28px 8px 8px;
  opacity:0;transition:opacity .2s;
}
.film-card:hover .overlay{opacity:1;}
.fc-title{font-size:.72rem;font-weight:600;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:5px;}
.fc-meta{font-size:.66rem;color:#556677;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.fc-rating{
  position:absolute;top:6px;right:6px;
  background:rgba(0,0,0,.7);backdrop-filter:blur(4px);
  border-radius:3px;padding:2px 5px;font-size:.62rem;font-weight:700;color:#e9c46a;
}
.rank-badge{
  position:absolute;top:6px;left:6px;
  background:#e50914;color:#fff;font-size:.58rem;font-weight:800;
  padding:2px 6px;border-radius:3px;letter-spacing:.5px;
}
.seen-badge{
  position:absolute;top:6px;left:6px;
  background:#00c030;color:#fff;font-size:.55rem;font-weight:700;
  padding:2px 6px;border-radius:3px;
}

/* ── Score bars ── */
.score-wrap{margin-top:4px;}
.score-row{display:flex;align-items:center;gap:5px;margin-bottom:2px;}
.score-lbl{font-size:.58rem;color:#445;width:42px;flex-shrink:0;}
.score-bg{flex:1;background:#1e2830;border-radius:2px;height:3px;overflow:hidden;}
.bar-c{height:100%;background:#e50914;border-radius:2px;}
.bar-k{height:100%;background:#1a73e8;border-radius:2px;}
.bar-h{height:100%;background:linear-gradient(to right,#6a0dad,#e50914);border-radius:2px;}
.score-val{font-size:.58rem;color:#445;width:24px;text-align:right;}

/* ── Section headers ── */
.sec-hdr{
  display:flex;align-items:baseline;justify-content:space-between;
  border-bottom:1px solid #1e2830;padding-bottom:8px;margin-bottom:14px;
}
.sec-title{font-size:1rem;font-weight:700;color:#fff;letter-spacing:-.3px;}
.sec-count{font-size:.72rem;color:#445;}

/* ── Detail panel ── */
.dp-title{font-size:2rem;font-weight:900;color:#fff;line-height:1.1;margin-bottom:4px;}
.dp-tagline{font-size:.88rem;color:#556677;font-style:italic;margin-bottom:12px;}
.dp-meta{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;}
.badge{
  background:rgba(229,9,20,.12);border:1px solid rgba(229,9,20,.3);
  color:#e50914;border-radius:4px;padding:2px 9px;font-size:.72rem;font-weight:600;
}
.genre-pill{
  background:#1a2230;color:#778899;border-radius:20px;
  padding:2px 11px;font-size:.7rem;
}
.dp-overview{font-size:.88rem;color:#aabbcc;line-height:1.8;max-width:760px;}
.person-chip{
  display:inline-block;background:#1a2230;border:1px solid #1e2830;
  color:#ccd8e4;border-radius:5px;padding:3px 10px;font-size:.74rem;margin:2px 2px 2px 0;
}
.provider-logo{width:36px;height:36px;border-radius:6px;object-fit:cover;}
.provider-row{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-top:4px;}

/* ── Profile card ── */
.pf-avatar{
  width:52px;height:52px;border-radius:50%;
  background:linear-gradient(135deg,#e50914,#ff6b35);
  display:flex;align-items:center;justify-content:center;
  font-size:1.4rem;font-weight:800;color:#fff;flex-shrink:0;
}
.pf-name{font-size:.95rem;font-weight:700;color:#fff;}
.pf-stat-val{font-size:1.1rem;font-weight:800;color:#e50914;}
.pf-stat-lbl{font-size:.62rem;color:#445;text-transform:uppercase;letter-spacing:.5px;}

/* ── Star rating ── */
.star-row{display:flex;gap:2px;margin-top:2px;}
.star{font-size:.9rem;cursor:pointer;transition:transform .1s;}
.star:hover{transform:scale(1.3);}

/* ── Chat ── */
.chat-q{background:#1a2230;border-left:3px solid #e50914;padding:7px 11px;border-radius:0 6px 6px 0;font-size:.78rem;color:#dde8f0;margin-bottom:3px;}
.chat-a{background:#0c151d;border-left:3px solid #1a73e8;padding:7px 11px;border-radius:0 6px 6px 0;font-size:.78rem;color:#7799bb;margin-bottom:8px;}

/* ── How-it-works ── */
.how-card{background:#0c0f12;border:1px solid #1e2830;border-radius:8px;padding:18px;height:100%;}
.how-icon{font-size:1.6rem;margin-bottom:8px;}
.how-title{font-size:.88rem;font-weight:700;margin-bottom:6px;}
.how-body{font-size:.73rem;color:#556677;line-height:1.7;}

/* ── Watchlist item ── */
.wl-row{display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid #1a2230;}
.wl-poster{width:28px;height:42px;object-fit:cover;border-radius:3px;flex-shrink:0;}
.wl-title{font-size:.76rem;color:#aabbcc;flex:1;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;}

/* ── Taste bar ── */
.taste-bg{background:#1a2230;border-radius:3px;height:4px;overflow:hidden;margin-top:3px;}
.taste-fill{background:#e50914;height:100%;border-radius:3px;}

/* ── Load more ── */
div[data-testid="stButton"].load-more-btn>button{
  background:transparent!important;border:1px solid #2a3540!important;
  color:#556677!important;width:100%;font-size:.78rem;
}
div[data-testid="stButton"].load-more-btn>button:hover{
  border-color:#e50914!important;color:#e50914!important;background:transparent!important;
}
</style>
""", unsafe_allow_html=True)

# ── Session state defaults ──────────────────────────────────────────────────
_DEFAULTS = {
    "username":       "",
    "profile":        {},
    "chat_history":   [],
    "active_mood":    None,
    "selected_movie": None,
    "search_mode":    "db",
    "viewing":        None,
    "show_why":       False,
    # Load-more counters per section
    "lmt_trend":      12,
    "lmt_mood":       14,
    "lmt_recs":       12,
    "lmt_sf":         6,   # sci-fi
    "lmt_ac":         6,   # action
    "lmt_co":         6,   # comedy
    "lmt_ho":         6,   # horror
    "lmt_dr":         6,   # drama
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v if not isinstance(_v, (list, dict)) else type(_v)()

# ── Load engine ─────────────────────────────────────────────────────────────
try:
    engine = get_engine()
except Exception as e:
    st.error(f"🚨 Engine error: {e}")
    st.stop()

# ── Constants ───────────────────────────────────────────────────────────────
MOODS = {
    "😊 Happy":   ["Comedy", "Animation", "Family"],
    "😢 Drama":   ["Drama", "Romance"],
    "🔥 Action":  ["Action", "Adventure"],
    "🧠 Sci-Fi":  ["Science Fiction", "Fantasy"],
    "💖 Romance": ["Romance", "Comedy"],
    "👻 Horror":  ["Horror", "Thriller"],
}

SCOUT_MAP = [
    ({"happy","laugh","comedy","fun","funny","cheer","light","hilarious","entertai"},
     "😄 Perfect! Here are some feel-good picks for you.", "Comedy"),
    ({"scary","horror","ghost","dark","fear","spooky","creepy","haunt","terror"},
     "👻 Brace yourself — here are the spine-chillers!", "Horror"),
    ({"scifi","sci-fi","future","space","robot","alien","galaxy","tech","dystopia","cyber"},
     "🚀 Buckle up! Best Sci-Fi incoming.", "Science Fiction"),
    ({"love","romance","romantic","date","heart","couple","wedding","relationship"},
     "❤️ Love is in the air! Top romance picks:", "Romance"),
    ({"action","fight","war","battle","explosion","adventure","hero","superhero"},
     "💥 Adrenaline time! Top action picks:", "Action"),
    ({"animated","cartoon","pixar","disney","family","kids","anime"},
     "🎨 Family fun! Best animated movies:", "Animation"),
    ({"sad","cry","emotional","moving","touching","feel","tears","depressing"},
     "🎭 Sometimes you just need a good cry.", "Drama"),
    ({"mystery","detective","crime","whodunit","suspense","thriller","investigation"},
     "🔍 A mystery awaits! Top thrillers:", "Thriller"),
    ({"fantasy","magic","dragon","wizard","medieval","sword","kingdom","elf"},
     "🧙 Into another world! Best fantasy:", "Fantasy"),
]

GENRE_SECTIONS = [
    ("🚀 Sci-Fi & Fantasy",  ["Science Fiction","Fantasy"], "lmt_sf"),
    ("💥 Action & Adventure", ["Action","Adventure"],       "lmt_ac"),
    ("😂 Comedy",             ["Comedy"],                   "lmt_co"),
    ("💀 Horror & Thriller",  ["Horror","Thriller"],        "lmt_ho"),
    ("❤️ Drama & Romance",   ["Drama","Romance"],           "lmt_dr"),
]

# ── Helpers ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def _poster(movie_id: int) -> str:
    return tmdb_service.fetch_poster(int(movie_id))

def _genres_str(val, n=3) -> str:
    if isinstance(val, list):
        return ", ".join(str(g) for g in val[:n])
    return str(val).replace("|", ", ")

def _safe_poster(url: str) -> str:
    return url or "https://via.placeholder.com/300x450/14181c/223?text=🎬"

def set_backdrop(url: Optional[str]):
    if url:
        st.markdown(
            f'<style>.stApp{{background:linear-gradient(rgba(20,24,28,.9),rgba(20,24,28,1)),'
            f'url("{url}") center/cover fixed;}}</style>',
            unsafe_allow_html=True,
        )

def compute_hybrid(df: pd.DataFrame) -> pd.DataFrame:
    # Note: 'content' and 'collab' are display proxies (not independently computed vectors)
    # used as visual approximations for the score bars in the UI.
    d = df.copy()
    mp = max(d["popularity"].max(), 1)
    mw = max(d["weighted_score"].max(), 1)
    d["collab"]  = (d["weighted_score"] / mw * 100).round(1)
    d["content"] = (d["popularity"] / mp * 60 + 40).round(1)
    d["hybrid"]  = (d["collab"] * .55 + d["content"] * .45).round(1)
    return d

def _score_bars(c, k, h) -> str:
    c, k, h = min(float(c), 100), min(float(k), 100), min(float(h), 100)
    return (
        f'<div class="score-wrap">'
        f'<div class="score-row"><span class="score-lbl">Content</span>'
        f'<div class="score-bg"><div class="bar-c" style="width:{c:.0f}%"></div></div>'
        f'<span class="score-val">{c:.0f}%</span></div>'
        f'<div class="score-row"><span class="score-lbl">Collab</span>'
        f'<div class="score-bg"><div class="bar-k" style="width:{k:.0f}%"></div></div>'
        f'<span class="score-val">{k:.0f}%</span></div>'
        f'<div class="score-row"><span class="score-lbl">Hybrid</span>'
        f'<div class="score-bg"><div class="bar-h" style="width:{h:.0f}%"></div></div>'
        f'<span class="score-val">{h:.0f}%</span></div>'
        f'</div>'
    )

def _update_profile_taste(genres):
    p = st.session_state.profile
    taste = p.get("taste", [])
    if isinstance(genres, list):
        taste.extend(str(g) for g in genres)
    elif isinstance(genres, str):
        taste.append(genres)
    p["taste"] = taste[-200:]   # keep last 200 entries
    _save()

def _add_to_diary(title: str, poster: str):
    p = st.session_state.profile
    diary = p.get("diary", [])
    diary = [d for d in diary if d["title"] != title]
    diary.insert(0, {"title": title, "poster": poster})
    p["diary"] = diary[:60]
    _save()

def _save():
    if st.session_state.username:
        save_profile(st.session_state.username, st.session_state.profile)

def _in_watchlist(title: str) -> bool:
    return any(m["title"] == title for m in st.session_state.profile.get("watchlist", []))

def _toggle_watchlist(title: str, poster: str):
    wl = st.session_state.profile.get("watchlist", [])
    if _in_watchlist(title):
        st.session_state.profile["watchlist"] = [m for m in wl if m["title"] != title]
    else:
        wl.insert(0, {"title": title, "poster": poster})
        st.session_state.profile["watchlist"] = wl[:200]
    _save()

def _get_rating(title: str) -> int:
    return st.session_state.profile.get("ratings", {}).get(title, 0)

def _set_rating(title: str, stars: int):
    if "ratings" not in st.session_state.profile:
        st.session_state.profile["ratings"] = {}
    st.session_state.profile["ratings"][title] = stars
    _save()

def scout_reply(text: str):
    words = set(text.lower().split())
    for kws, reply, genre in SCOUT_MAP:
        if kws & words:
            return reply, genre
    return ("🤖 Try: 'something scary', 'funny movie', 'sci-fi', 'romantic', 'action'…", None)


# ── Film card HTML ───────────────────────────────────────────────────────────
def _film_card_html(title, poster, rating, rank=None, seen=False) -> str:
    rb = f'<div class="rank-badge">#{rank}</div>' if rank else (
         f'<div class="seen-badge">✓</div>' if seen else "")
    rr = f'<div class="fc-rating">⭐ {rating}</div>' if rating and str(rating) != "nan" else ""
    return (
        f'<div class="film-card">'
        f'{rb}{rr}'
        f'<img src="{_safe_poster(poster)}" alt="{title}" loading="lazy" '
        f'onerror="this.src=\'https://via.placeholder.com/300x450/14181c/223?text=🎬\'">'
        f'<div class="overlay"></div>'
        f'</div>'
        f'<div class="fc-title" title="{title}">{format_movie_title(title, 18)}</div>'
        f'<div class="fc-meta">⭐ {rating}</div>'
    )


# ── Render grid ─────────────────────────────────────────────────────────────
def render_grid(df, key_prefix, cols=7, show_rank=False, show_score=False, limit_key=None):
    """Render a Letterboxd-style poster grid with Load More."""
    if df.empty:
        st.info("No movies found.")
        return

    items = list(df.itertuples(index=False))
    total = len(items)
    limit = st.session_state.get(limit_key, len(items)) if limit_key else len(items)
    shown = items[:limit]

    for row_start in range(0, len(shown), cols):
        chunk = shown[row_start:row_start + cols]
        columns = st.columns(cols)
        for ci, row in enumerate(chunk):
            i = row_start + ci
            with columns[ci]:
                mid    = int(getattr(row, "movie_id", 0))
                title  = str(getattr(row, "title", ""))
                rating = getattr(row, "vote_average", "N/A")
                genres = getattr(row, "genres", [])
                poster = _poster(mid)
                seen   = any(d["title"] == title for d in st.session_state.profile.get("diary", []))

                rank = i + 1 if show_rank else None
                st.markdown(_film_card_html(title, poster, rating, rank, seen), unsafe_allow_html=True)

                if show_score:
                    st.markdown(_score_bars(
                        getattr(row, "content", 50),
                        getattr(row, "collab",  50),
                        getattr(row, "hybrid",  50),
                    ), unsafe_allow_html=True)

                # Three buttons: Details | Recs | Heart
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("📖", key=f"{key_prefix}_d{i}", help="Details", use_container_width=True):
                        st.session_state.viewing = {"title": title, "movie_id": mid}
                        st.session_state.selected_movie = None
                        st.rerun()
                with c2:
                    if st.button("🎬", key=f"{key_prefix}_r{i}", help="Recommendations", use_container_width=True):
                        st.session_state.selected_movie = title
                        st.session_state.viewing = None
                        st.session_state.search_mode = "db"
                        st.rerun()
                with c3:
                    in_wl = _in_watchlist(title)
                    if st.button("✓" if in_wl else "❤", key=f"{key_prefix}_w{i}", help="Watchlist", use_container_width=True):
                        _toggle_watchlist(title, poster)
                        st.rerun()

    # Load More
    if limit_key and limit < total:
        remaining = total - limit
        lm_col = st.columns([3, 2, 3])[1]
        with lm_col:
            if st.button(f"Load {min(remaining, cols*2)} more ↓", key=f"lm_{limit_key}", use_container_width=True):
                st.session_state[limit_key] = limit + cols * 2
                st.rerun()
        st.markdown(f'<div style="text-align:center;font-size:.68rem;color:#334;margin-top:4px;">{remaining} more movies</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# ── SIDEBAR ────────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # ── Profile ──────────────────────────────────────────────────────────
    st.markdown('<div style="font-size:.68rem;font-weight:600;color:#e50914;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;">Your Profile</div>', unsafe_allow_html=True)

    if not st.session_state.username:
        with st.form("login_form", clear_on_submit=False):
            uname = st.text_input("Username", placeholder="Enter your name…", label_visibility="collapsed")
            if st.form_submit_button("Sign In / Create Profile", use_container_width=True):
                if uname.strip():
                    st.session_state.username = uname.strip()
                    st.session_state.profile  = load_profile(uname.strip())
                    st.rerun()
        st.caption("Your watchlist, ratings & taste are saved under your profile.")
    else:
        uname = st.session_state.username
        initial = uname[0].upper()
        wl_count  = len(st.session_state.profile.get("watchlist", []))
        rat_count = len(st.session_state.profile.get("ratings", {}))
        diary_count = len(st.session_state.profile.get("diary", []))

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">'
            f'<div class="pf-avatar">{initial}</div>'
            f'<div><div class="pf-name">{uname}</div>'
            f'<div style="font-size:.7rem;color:#445;">Member</div></div>'
            f'</div>'
            f'<div style="display:flex;gap:0;text-align:center;margin-bottom:12px;">'
            f'<div style="flex:1;border-right:1px solid #1e2830;">'
            f'<div class="pf-stat-val">{diary_count}</div>'
            f'<div class="pf-stat-lbl">Seen</div></div>'
            f'<div style="flex:1;border-right:1px solid #1e2830;">'
            f'<div class="pf-stat-val">{rat_count}</div>'
            f'<div class="pf-stat-lbl">Rated</div></div>'
            f'<div style="flex:1;">'
            f'<div class="pf-stat-val">{wl_count}</div>'
            f'<div class="pf-stat-lbl">Saved</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Taste profile
        taste = st.session_state.profile.get("taste", [])
        if taste:
            counts = pd.Series(taste).value_counts().head(4)
            total  = counts.sum()
            for genre, cnt in counts.items():
                pct = int(cnt / total * 100)
                st.markdown(
                    f'<div style="margin-bottom:6px;">'
                    f'<div style="display:flex;justify-content:space-between;font-size:.68rem;color:#445;">'
                    f'<span>{genre}</span><span>{pct}%</span></div>'
                    f'<div class="taste-bg"><div class="taste-fill" style="width:{pct}%"></div></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        sc, sd = st.columns(2)
        with sc:
            if st.button("Switch User", use_container_width=True, key="sw_user"):
                st.session_state.username = ""
                st.session_state.profile  = {}
                st.rerun()
        with sd:
            if st.button("🎲 Random", use_container_width=True, key="rand_sb"):
                rnd = engine.movies_df.sample(1).iloc[0]
                st.session_state.viewing = {"title": rnd["title"], "movie_id": int(rnd["movie_id"])}
                st.session_state.selected_movie = None
                st.rerun()

    st.markdown("---")

    # ── Movie Scout ───────────────────────────────────────────────────────
    st.markdown('<div style="font-size:.68rem;font-weight:600;color:#e50914;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px;">🤖 Movie Scout</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:.73rem;color:#445;margin-bottom:8px;">Describe your mood — I\'ll find matching movies.</div>', unsafe_allow_html=True)

    scout_q = st.text_input("scout", label_visibility="collapsed",
                             placeholder="e.g. 'something scary'…", key="scout_in")
    if st.button("Find Movies", key="scout_go", use_container_width=True):
        if scout_q.strip():
            reply, genre = scout_reply(scout_q)
            st.session_state.chat_history.append({"q": scout_q, "a": reply, "genre": genre})
            if genre:
                st.session_state.active_mood   = genre
                st.session_state.selected_movie = None
                st.session_state.viewing        = None
                st.session_state["lmt_mood"]    = 14
            st.rerun()

    # Quick genre chips
    qcols = st.columns(3)
    for qi, (ql, qg) in enumerate([("🎭 Drama","Drama"),("🚀 Sci-Fi","Science Fiction"),("😂 Comedy","Comedy")]):
        with qcols[qi]:
            if st.button(ql, key=f"qp{qi}", use_container_width=True):
                st.session_state.active_mood = qg
                st.session_state.selected_movie = None
                st.session_state.viewing = None
                st.rerun()

    for item in st.session_state.chat_history[-2:]:
        st.markdown(f'<div class="chat-q">🧑 {item["q"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="chat-a">🤖 {item["a"]}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Watchlist ─────────────────────────────────────────────────────────
    wl = st.session_state.profile.get("watchlist", [])
    st.markdown(f'<div style="font-size:.68rem;font-weight:600;color:#e50914;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;">📌 Watchlist ({len(wl)})</div>', unsafe_allow_html=True)

    if not wl:
        st.markdown('<div style="font-size:.74rem;color:#334;">Save movies to watch later.</div>', unsafe_allow_html=True)
    else:
        for m in wl[:8]:
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(
                    f'<div class="wl-row">'
                    f'<img class="wl-poster" src="{_safe_poster(m.get("poster",""))}" '
                    f'onerror="this.src=\'https://via.placeholder.com/28x42/14181c/223\'">'
                    f'<span class="wl-title">{format_movie_title(m["title"], 18)}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with c2:
                if st.button("✕", key=f"rm_{m['title'][:6]}", help="Remove", use_container_width=True):
                    st.session_state.profile["watchlist"] = [x for x in wl if x["title"] != m["title"]]
                    _save()
                    st.rerun()

    st.markdown("---")

    # ── Film Diary (recently viewed) ──────────────────────────────────────
    diary = st.session_state.profile.get("diary", [])[:5]
    if diary:
        st.markdown('<div style="font-size:.68rem;font-weight:600;color:#e50914;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;">📖 Film Diary</div>', unsafe_allow_html=True)
        for d in diary:
            st.markdown(
                f'<div class="wl-row">'
                f'<img class="wl-poster" src="{_safe_poster(d.get("poster",""))}" '
                f'onerror="this.src=\'https://via.placeholder.com/28x42/14181c/223\'">'
                f'<span class="wl-title">{format_movie_title(d["title"], 18)}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown("---")

    # ── Stats + reset ─────────────────────────────────────────────────────
    stats = engine.get_stats()
    st.markdown(
        f'<div style="display:flex;gap:10px;justify-content:center;text-align:center;margin-bottom:10px;">'
        f'<div><div class="pf-stat-val">{stats.get("total_movies","N/A")}</div><div class="pf-stat-lbl">Movies</div></div>'
        f'<div><div class="pf-stat-val">{stats.get("avg_rating","N/A")}</div><div class="pf-stat-lbl">Avg ⭐</div></div>'
        f'<div><div class="pf-stat-val">{stats.get("genres_count","N/A")}</div><div class="pf-stat-lbl">Genres</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("🔄 Reset session", use_container_width=True, key="reset_sess"):
        for k, v in _DEFAULTS.items():
            st.session_state[k] = v if not isinstance(v, (list, dict)) else type(v)()
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# ── MAIN AREA ──────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
if st.session_state.profile.get("diary"):
    set_backdrop(None)

# ── Top header ──────────────────────────────────────────────────────────────
hL, hR = st.columns([5, 1])
with hL:
    st.markdown(
        '<div style="font-size:2.2rem;font-weight:900;color:#e50914;letter-spacing:-2px;line-height:1;">🎬 CINEMAGIC</div>'
        '<div style="font-size:.68rem;color:#334;letter-spacing:3px;text-transform:uppercase;">Hybrid AI Movie Recommendation System</div>',
        unsafe_allow_html=True,
    )
with hR:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🎲 Random Movie", key="rand_main", use_container_width=True):
        rnd = engine.movies_df.sample(1).iloc[0]
        st.session_state.viewing = {"title": rnd["title"], "movie_id": int(rnd["movie_id"])}
        st.session_state.selected_movie = None
        st.rerun()

st.markdown("---")

# ── Mood row ────────────────────────────────────────────────────────────────
st.markdown('<div style="font-size:.65rem;color:#334;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;">Browse by Mood</div>', unsafe_allow_html=True)
mcols = st.columns(len(MOODS))
for mi, (mood_name, mood_genres) in enumerate(MOODS.items()):
    with mcols[mi]:
        active = st.session_state.active_mood in mood_genres
        label  = f"✓ {mood_name}" if active else mood_name
        if st.button(label, key=f"mood_{mi}", use_container_width=True):
            if active:
                st.session_state.active_mood = None
            else:
                st.session_state.active_mood    = mood_genres[0]
                st.session_state.selected_movie = None
                st.session_state.viewing        = None
                st.session_state["lmt_mood"]    = 14
            st.rerun()

st.markdown("---")

# ── Search ──────────────────────────────────────────────────────────────────
tab_db, tab_tmdb = st.tabs(["🔍 Database Search (4,800+ movies)", "🌐 Global Search (TMDB)"])

selected_movie = st.session_state.get("selected_movie")
search_mode    = st.session_state.get("search_mode", "db")
_from_session  = bool(selected_movie)

with tab_db:
    if st.session_state.active_mood:
        mood_matches = engine.filter_by_genres([st.session_state.active_mood])
        if not mood_matches.empty:
            opts = ["— pick a movie —"] + list(mood_matches["title"].values)
            pick = st.selectbox(f"Movies tagged as **{st.session_state.active_mood}**:", opts, key="mood_sel")
            if pick != "— pick a movie —":
                selected_movie = pick
                search_mode = "db"
    else:
        q = st.text_input("db_search", label_visibility="collapsed",
                           placeholder="Type a movie title to search…", key="db_q")
        if q and q.strip():
            hits = [t for t in engine.movies_df["title"].tolist() if q.lower() in t.lower()][:80]
            if hits:
                pick = st.selectbox("Select:", hits, key="db_sel")
                selected_movie = pick
                search_mode = "db"
            else:
                st.caption("Not found in database — try Global Search.")

with tab_tmdb:
    tq = st.text_input("tmdb_search", label_visibility="collapsed",
                        placeholder="Search any movie worldwide…", key="tmdb_q")
    if st.button("Search →", key="tmdb_go"):
        if tq.strip():
            selected_movie = tq.strip()
            search_mode = "tmdb"

if _from_session:
    st.session_state.selected_movie = None

# ═══════════════════════════════════════════════════════════════════════════
# ── MOVIE DETAIL VIEW ──────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
if st.session_state.viewing:
    v      = st.session_state.viewing
    mid    = v.get("movie_id")
    vtitle = v.get("title", "")

    st.markdown("---")
    with st.spinner(f"Loading {vtitle}…"):
        details   = tmdb_service.get_movie_details(mid) if mid else None

    if details:
        pp = details.get("poster_path","")
        poster_url = f"https://image.tmdb.org/t/p/w500{pp}" if pp else _safe_poster("")
        bd = tmdb_service.fetch_backdrop(details["id"])
        if bd:
            set_backdrop(bd)

        # Add to diary
        _add_to_diary(vtitle, poster_url)
        genres_list = [g["name"] for g in details.get("genres", [])]
        _update_profile_taste(genres_list)

        credits   = details.get("credits", {})
        cast_list = credits.get("cast", [])[:8]
        crew_list = credits.get("crew", [])
        director  = next((c["name"] for c in crew_list if c.get("job") == "Director"), None)
        writers   = [c["name"] for c in crew_list if c.get("job") in ("Writer","Screenplay","Story")][:2]
        providers = tmdb_service.get_watch_providers(details["id"])
        trailer   = tmdb_service.get_movie_trailer(details["id"])

        year    = details.get("release_date","")[:4]
        rating  = details.get("vote_average", "N/A")
        runtime = details.get("runtime", "N/A")
        lang    = (details.get("original_language") or "").upper()
        votes   = details.get("vote_count", 0)
        tagline = details.get("tagline","")
        overview= details.get("overview","")

        # User's personal rating
        user_rating = _get_rating(vtitle)
        star_labels = ["★","★","★","★","★"]

        # Detail layout
        dl, dr = st.columns([1, 3], gap="large")
        with dl:
            st.image(poster_url, use_container_width=True)

        with dr:
            st.markdown(f'<div class="dp-title">{vtitle}</div>', unsafe_allow_html=True)
            if tagline:
                st.markdown(f'<div class="dp-tagline">"{tagline}"</div>', unsafe_allow_html=True)

            # Meta badges
            meta_html = (
                f'<div class="dp-meta">'
                f'<span class="badge">⭐ {rating}/10</span>'
                f'<span class="badge">🕐 {runtime} min</span>'
                f'<span class="badge">📅 {year}</span>'
                f'<span class="badge">🌐 {lang}</span>'
                f'<span style="font-size:.68rem;color:#334;margin-left:4px;">{votes:,} votes</span>'
                f'</div>'
            )
            genre_html = "".join(f'<span class="genre-pill">{g}</span>' for g in genres_list)
            st.markdown(meta_html + f'<div style="margin-bottom:12px;">{genre_html}</div>', unsafe_allow_html=True)

            if overview:
                st.markdown(f'<div class="dp-overview">{overview}</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Crew
            crew_html = ""
            if director:
                crew_html += f'<div style="margin-bottom:8px;"><div style="font-size:.65rem;color:#334;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:3px;">Director</div><span class="person-chip">🎬 {director}</span></div>'
            if writers:
                w_chips = "".join(f'<span class="person-chip">✍️ {w}</span>' for w in writers)
                crew_html += f'<div style="margin-bottom:8px;"><div style="font-size:.65rem;color:#334;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:3px;">Written By</div>{w_chips}</div>'
            if crew_html:
                st.markdown(crew_html, unsafe_allow_html=True)

            # Cast
            if cast_list:
                cast_chips = "".join(f'<span class="person-chip">🎭 {c["name"]}</span>' for c in cast_list)
                st.markdown(
                    f'<div style="margin-bottom:14px;">'
                    f'<div style="font-size:.65rem;color:#334;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:3px;">Cast</div>'
                    f'{cast_chips}</div>',
                    unsafe_allow_html=True,
                )

            # Where to watch
            stream_p = providers.get("stream", [])
            rent_p   = providers.get("rent",   [])
            if stream_p or rent_p:
                st.markdown('<div style="font-size:.65rem;color:#334;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;">Where to Watch</div>', unsafe_allow_html=True)
                if stream_p:
                    logos = "".join(f'<img class="provider-logo" src="https://image.tmdb.org/t/p/w92{p["logo_path"]}" title="{p["provider_name"]}" onerror="this.style.display=\'none\'">' for p in stream_p[:6])
                    st.markdown(f'<div style="margin-bottom:6px;"><span style="font-size:.68rem;color:#3a9;font-weight:600;">🟢 Stream </span><div class="provider-row">{logos}</div></div>', unsafe_allow_html=True)
                if rent_p:
                    logos = "".join(f'<img class="provider-logo" src="https://image.tmdb.org/t/p/w92{p["logo_path"]}" title="{p["provider_name"]}" onerror="this.style.display=\'none\'">' for p in rent_p[:4])
                    st.markdown(f'<div style="margin-bottom:10px;"><span style="font-size:.68rem;color:#a80;font-weight:600;">🟡 Rent/Buy </span><div class="provider-row">{logos}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="font-size:.73rem;color:#334;margin-bottom:10px;">Streaming info unavailable. Check <a href="https://www.justwatch.com" target="_blank" style="color:#e50914;">JustWatch ↗</a></div>', unsafe_allow_html=True)

            # Your rating
            st.markdown('<div style="font-size:.65rem;color:#334;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;">Your Rating</div>', unsafe_allow_html=True)
            r_cols = st.columns(7)
            for star_i in range(1, 6):
                with r_cols[star_i - 1]:
                    filled = "⭐" if star_i <= user_rating else "☆"
                    if st.button(filled, key=f"star_{star_i}", use_container_width=True):
                        _set_rating(vtitle, star_i)
                        st.rerun()
            with r_cols[5]:
                if user_rating:
                    st.markdown(f'<div style="font-size:.68rem;color:#e9c46a;padding-top:6px;">{user_rating}/5</div>', unsafe_allow_html=True)

            # Action buttons
            ba, bb, bc = st.columns(3)
            with ba:
                in_wl = _in_watchlist(vtitle)
                if st.button("✓ In Watchlist" if in_wl else "❤️ Watchlist", key="det_wl", use_container_width=True):
                    _toggle_watchlist(vtitle, poster_url)
                    st.rerun()
            with bb:
                if trailer:
                    with st.expander("▶ Trailer"):
                        st.video(trailer)
            with bc:
                if st.button("🎬 Similar Movies", key="det_recs", use_container_width=True):
                    st.session_state.selected_movie = vtitle
                    st.session_state.viewing        = None
                    st.session_state.search_mode    = "db"
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✕ Close Details", key="close_det"):
            st.session_state.viewing = None
            st.rerun()

    else:
        st.warning(f"Could not load details for '{vtitle}'. It may not be in TMDB.")
        if st.button("✕ Close", key="close_nodet"):
            st.session_state.viewing = None
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════
# ── RECOMMENDATION RESULTS ─────────────────────────────────────────════════
# ═══════════════════════════════════════════════════════════════════════════
elif selected_movie:
    with st.spinner("✨ Finding your matches…"):
        try:
            recs = None
            details = None
            poster_url = _safe_poster("")
            src_features = None

            if search_mode == "db":
                recs, src_features = engine.recommend(selected_movie, top_n=30)
                row = engine.movies_df[engine.movies_df["title"] == selected_movie]
                if not row.empty:
                    mid = int(row.iloc[0]["movie_id"])
                    details    = tmdb_service.get_movie_details(mid)
                    poster_url = _poster(mid)
                    if details:
                        genres_list = [g["name"] for g in details.get("genres", [])]
                        _update_profile_taste(genres_list)
                        _add_to_diary(selected_movie, poster_url)
            else:
                tags, details = tmdb_service.get_external_movie_tags(selected_movie)
                if tags and details:
                    recs = engine.recommend_from_tags(tags, top_n=30)
                    selected_movie = details.get("title", selected_movie)
                    pp = details.get("poster_path","")
                    poster_url = f"https://image.tmdb.org/t/p/w500{pp}" if pp else poster_url
                    genres_list = [g["name"] for g in details.get("genres", [])]
                    _update_profile_taste(genres_list)
                    _add_to_diary(selected_movie, poster_url)
                else:
                    st.error("❌ Movie not found. Check spelling or try Database Search.")
                    st.stop()

            if details:
                bd = tmdb_service.fetch_backdrop(details["id"])
                if bd:
                    set_backdrop(bd)

            st.markdown("---")

            # Hero section
            h1, h2 = st.columns([1, 3], gap="large")
            with h1:
                st.image(poster_url, use_container_width=True)
            with h2:
                year = details.get("release_date","")[:4] if details else ""
                st.markdown(f'<div class="dp-title">{selected_movie} <span style="font-size:1.2rem;color:#445;">{year}</span></div>', unsafe_allow_html=True)

                if details:
                    gd = " · ".join(g["name"] for g in details.get("genres",[])[:4])
                    st.markdown(
                        f'<div class="dp-meta">'
                        f'<span class="badge">⭐ {details.get("vote_average","N/A")}/10</span>'
                        f'<span class="badge">🕐 {details.get("runtime","N/A")} min</span>'
                        f'<span style="font-size:.75rem;color:#556677;">{gd}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    ov = details.get("overview","")
                    if ov:
                        st.markdown(f'<div class="dp-overview">{ov}</div>', unsafe_allow_html=True)
                elif src_features:
                    ov = src_features.get("overview","") if src_features else ""
                    if ov:
                        st.markdown(f'<div class="dp-overview">{ov}</div>', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                ba, bb, bc = st.columns(3)
                with ba:
                    in_wl = _in_watchlist(selected_movie)
                    if st.button("✓ Watchlist" if in_wl else "❤️ Watchlist", key="hero_wl", use_container_width=True):
                        _toggle_watchlist(selected_movie, poster_url)
                        st.rerun()
                with bb:
                    if details:
                        if st.button("📖 Full Details", key="hero_det", use_container_width=True):
                            st.session_state.viewing = {"title": selected_movie, "movie_id": details["id"]}
                            st.rerun()
                with bc:
                    if st.button("🔬 Why these?" if not st.session_state.show_why else "🔬 Hide", key="why_btn", use_container_width=True):
                        st.session_state.show_why = not st.session_state.show_why
                        st.rerun()

                if st.session_state.show_why:
                    st.markdown("""
                    <div style="background:#0c0f12;border:1px solid #1e2830;border-radius:8px;padding:14px;margin-top:10px;">
                    <div style="font-size:.82rem;font-weight:700;color:#fff;margin-bottom:8px;">🧠 How CineMagic works</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                    <div style="background:#111620;border-left:3px solid #e50914;padding:8px 12px;border-radius:0 6px 6px 0;">
                    <div style="font-size:.76rem;font-weight:700;color:#e50914;margin-bottom:3px;">📄 Content-Based</div>
                    <div style="font-size:.7rem;color:#445;line-height:1.6;">TF-IDF on genres, cast, crew & overview → cosine similarity via NearestNeighbors.</div></div>
                    <div style="background:#111620;border-left:3px solid #1a73e8;padding:8px 12px;border-radius:0 6px 6px 0;">
                    <div style="font-size:.76rem;font-weight:700;color:#1a73e8;margin-bottom:3px;">👥 Collaborative</div>
                    <div style="font-size:.7rem;color:#445;line-height:1.6;">Bayesian-weighted score: vote_count × vote_avg × popularity → crowd signal.</div></div>
                    </div>
                    <div style="font-size:.7rem;color:#334;margin-top:8px;">⚡ <b style="color:#666">Hybrid = 55% Collaborative + 45% Content</b> — better diversity, fewer cold-start gaps.</div>
                    </div>
                    """, unsafe_allow_html=True)

            # Recommendations grid
            if recs is not None and not recs.empty:
                recs = compute_hybrid(recs)
                st.markdown("---")
                st.markdown(
                    f'<div class="sec-hdr">'
                    f'<span class="sec-title">Because you liked <span style="color:#e50914">{format_movie_title(selected_movie, 26)}</span></span>'
                    f'<span class="sec-count">Hybrid Algorithm · 📖 Details · 🎬 More like this</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                render_grid(recs, key_prefix="rec", cols=6, show_rank=True, show_score=True, limit_key="lmt_recs")

        except ValueError as e:
            st.error(f"❌ {e}")
        except APIError as e:
            st.error(f"❌ API Error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            st.error(f"❌ Unexpected error: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# ── MOOD BROWSE ────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
elif st.session_state.active_mood and not st.session_state.viewing:
    genre = st.session_state.active_mood
    mood_label = next((k for k, v in MOODS.items() if genre in v), genre)

    st.markdown("---")
    try:
        mood_genres_all = MOODS.get(mood_label, [genre])
        mood_df = engine.filter_by_genres(mood_genres_all)

        st.markdown(
            f'<div class="sec-hdr">'
            f'<span class="sec-title">{mood_label}</span>'
            f'<span class="sec-count">{len(mood_df)} movies · 📖 Details · 🎬 Recommendations</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        render_grid(mood_df, key_prefix="mood", cols=7, show_rank=True, limit_key="lmt_mood")
    except Exception as e:
        st.error(f"Error: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# ── HOME PAGE ──────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
elif not st.session_state.viewing:

    # ── Trending ──────────────────────────────────────────────────────────
    st.markdown("---")
    try:
        trend_df = engine.get_trending(50)
        st.markdown(
            f'<div class="sec-hdr">'
            f'<span class="sec-title">🔥 Trending Now</span>'
            f'<span class="sec-count">Most popular · ranked by audience score</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        render_grid(trend_df, key_prefix="trend", cols=7, show_rank=True, limit_key="lmt_trend")
    except Exception as e:
        st.error(f"Trending error: {e}")

    # ── Genre sections ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div style="font-size:.8rem;font-weight:700;color:#fff;margin-bottom:14px;">Browse by Genre</div>', unsafe_allow_html=True)

    for sec_name, sec_genres, sec_lmt in GENRE_SECTIONS:
        try:
            gdf = engine.filter_by_genres(sec_genres)
            if gdf.empty:
                continue
            st.markdown(
                f'<div class="sec-hdr">'
                f'<span class="sec-title">{sec_name}</span>'
                f'<span class="sec-count">{len(gdf)} movies</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            render_grid(gdf, key_prefix=f"g{sec_lmt}", cols=7, limit_key=sec_lmt)
        except Exception as e:
            logger.error(f"Genre section error ({sec_name}): {e}")

    # ── How it works ──────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div style="font-size:.8rem;font-weight:700;color:#fff;margin-bottom:12px;">🔬 How the Hybrid Algorithm Works</div>', unsafe_allow_html=True)
    hw1, hw2, hw3 = st.columns(3)
    for col, icon, title, body, clr in [
        (hw1, "📄", "Content-Based Filtering", "TF-IDF vectorises genres, cast, crew, keywords & overview. Cosine similarity via scikit-learn NearestNeighbors finds the closest matches in feature space.", "#e50914"),
        (hw2, "👥", "Collaborative Filtering", "Bayesian-weighted rating: vote_count × vote_average × popularity — models what audiences collectively enjoy, similar to user-based CF.", "#1a73e8"),
        (hw3, "⚡", "Hybrid Score", "Final ranking = 55% Collaborative + 45% Content. Combining both signals reduces the cold-start problem and improves recommendation diversity.", "#a855f7"),
    ]:
        with col:
            st.markdown(
                f'<div class="how-card">'
                f'<div class="how-icon">{icon}</div>'
                f'<div class="how-title" style="color:{clr};">{title}</div>'
                f'<div class="how-body">{body}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ── Footer ──────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="text-align:center;color:#1e2830;font-size:.68rem;padding:20px 0 8px;border-top:1px solid #1e2830;margin-top:28px;">'
    f'🎬 CINEMAGIC · Hybrid Movie Recommendation System · '
    f'{engine.get_stats().get("total_movies","N/A")} movies · '
    f'Content-Based + Collaborative Filtering · scikit-learn · TMDB · Streamlit · College ML Project'
    f'</div>',
    unsafe_allow_html=True,
)
