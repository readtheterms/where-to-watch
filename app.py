import streamlit as st
from api import search_tmdb, get_streaming, search_anilist

# ─────────────────────────────────────────────
# PAGE CONFIG
# Must be the first Streamlit call in the file.
# layout="wide" uses the full browser width.
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="WhereToWatch",
    page_icon="🎬",
    layout="wide",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# Streamlit lets you inject raw CSS via st.markdown with unsafe_allow_html=True.
# We use this to build a dark theme and card-style result layout that plain
# Streamlit widgets can't produce on their own.
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Global background & text ── */
    .stApp { background-color: #0d0d0d; }
    body, p, span, label { color: #e0e0e0 !important; }

    /* ── Hide the default Streamlit top header bar ── */
    header[data-testid="stHeader"] { background: transparent; }

    /* ── Search input styling ── */
    input[type="text"] {
        background-color: #1e1e1e !important;
        color: #ffffff !important;
        border: 1px solid #444 !important;
        border-radius: 8px !important;
        font-size: 1rem !important;
    }

    /* ── Filter radio buttons: make them look like toggle pills ── */
    div[role="radiogroup"] {
        display: flex;
        gap: 8px;
    }
    div[role="radiogroup"] label {
        background-color: #1e1e1e;
        border: 1px solid #444;
        border-radius: 20px;
        padding: 4px 16px;
        cursor: pointer;
        font-size: 0.9rem;
        transition: background 0.2s;
    }
    div[role="radiogroup"] label:hover {
        background-color: #2a2a2a;
    }

    /* ── Result card container ── */
    .result-card {
        background-color: #161625;
        border: 1px solid #2a2a3d;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        display: flex;
        gap: 18px;
        align-items: flex-start;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
        transition: border-color 0.2s;
    }
    .result-card:hover { border-color: #5555aa; }

    /* ── Poster image inside the card ── */
    .card-poster {
        width: 90px;
        min-width: 90px;
        height: 135px;
        border-radius: 8px;
        object-fit: cover;
        background-color: #222;
    }
    .card-poster-placeholder {
        width: 90px;
        min-width: 90px;
        height: 135px;
        border-radius: 8px;
        background-color: #222;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #555;
        font-size: 0.7rem;
        text-align: center;
    }

    /* ── Text inside the card ── */
    .card-info { flex: 1; min-width: 0; }
    .card-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #ffffff;
        margin: 0 0 4px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .card-meta {
        font-size: 0.82rem;
        color: #888;
        margin-bottom: 6px;
    }
    .card-rating {
        font-size: 0.88rem;
        color: #f0c040;
        margin-bottom: 10px;
    }

    /* ── Streaming platform badges ── */
    .badge-row {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        align-items: center;
    }
    .badge {
        display: inline-block;
        padding: 3px 11px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        color: #ffffff;
        white-space: nowrap;
    }
    .badge-none { color: #666; font-size: 0.8rem; }

    /* ── Section divider ── */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #aaaacc;
        border-bottom: 1px solid #2a2a3d;
        padding-bottom: 6px;
        margin: 20px 0 12px 0;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PROVIDER COLOR MAP
# Each streaming service gets a brand-accurate color.
# Any provider not listed falls back to a neutral gray.
# ─────────────────────────────────────────────
PROVIDER_COLORS = {
    "Netflix":               "#E50914",
    "Disney Plus":           "#113CCF",
    "Hulu":                  "#1CE783",
    "Amazon Prime Video":    "#00A8E0",
    "Max":                   "#002BE7",
    "HBO Max":               "#8B00FF",
    "Apple TV Plus":         "#555555",
    "Peacock":               "#E8A020",
    "Peacock Premium":       "#E8A020",
    "Paramount Plus":        "#0064FF",
    "Paramount+ Amazon Channel": "#0064FF",
    "Crunchyroll":           "#F47521",
    "Funimation Now":        "#5B0BB5",
    "HIDIVE":                "#00AACC",
    "Tubi TV":               "#FA4B05",
    "Pluto TV":              "#FFC619",
    "Shudder":               "#2D2D2D",
    "Mubi":                  "#1B1B1B",
    "default":               "#444466",
}


# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# Small, focused functions that each do one thing.
# Breaking logic into helpers keeps the main UI code readable.
# ─────────────────────────────────────────────

def get_tmdb_poster(poster_path):
    """Convert a TMDB poster_path like '/abc123.jpg' into a full CDN URL."""
    if poster_path:
        return f"https://image.tmdb.org/t/p/w200{poster_path}"
    return None


def build_badges_html(providers):
    """
    Takes a list of provider dicts (each has 'provider_name') and returns
    an HTML string of colored badge spans.
    """
    if not providers:
        return '<span class="badge-none">Not streaming in the US</span>'

    badges = ""
    for p in providers:
        name = p.get("provider_name", "Unknown")
        color = PROVIDER_COLORS.get(name, PROVIDER_COLORS["default"])
        badges += f'<span class="badge" style="background-color:{color};">{name}</span>'
    return badges


def render_card(poster_url, title, year, rating, type_label, streaming_html):
    """
    Returns a full HTML string for one result card.
    All card data is passed in — this function only deals with presentation.
    """
    if poster_url:
        poster_html = f'<img class="card-poster" src="{poster_url}" alt="{title} poster">'
    else:
        poster_html = '<div class="card-poster-placeholder">No Image</div>'

    return f"""
    <div class="result-card">
        {poster_html}
        <div class="card-info">
            <div class="card-title">{title}</div>
            <div class="card-meta">{year} &nbsp;·&nbsp; {type_label}</div>
            <div class="card-rating">{rating}</div>
            <div class="badge-row">{streaming_html}</div>
        </div>
    </div>
    """


# ─────────────────────────────────────────────
# APP HEADER
# ─────────────────────────────────────────────
st.markdown("""
    <h1 style="color:#ffffff; margin-bottom:0;">🎬 WhereToWatch</h1>
    <p style="color:#888; margin-top:4px; margin-bottom:24px;">
        Search any movie, TV show, or anime to find where it streams.
    </p>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SEARCH BAR
# st.text_input returns whatever the user typed (empty string if nothing yet).
# ─────────────────────────────────────────────
query = st.text_input(
    label="search",
    placeholder="e.g.  Interstellar,  Attack on Titan,  The Bear ...",
    label_visibility="collapsed",
)


# ─────────────────────────────────────────────
# FILTER BUTTONS
# st.radio with horizontal=True renders as a row of options.
# We store the choice and use it to decide which APIs to call.
# ─────────────────────────────────────────────
filter_choice = st.radio(
    label="filter",
    options=["All", "Movies & TV", "Anime Only"],
    horizontal=True,
    label_visibility="collapsed",
)


# ─────────────────────────────────────────────
# RESULTS
# Only run API calls when the user has typed something.
# st.spinner shows a loading indicator while we wait for the APIs.
# ─────────────────────────────────────────────
if query:
    show_tmdb  = filter_choice in ("All", "Movies & TV")
    show_anime = filter_choice in ("All", "Anime Only")

    # ── MOVIES & TV ──────────────────────────
    if show_tmdb:
        st.markdown('<div class="section-header">📺 Movies &amp; TV Shows</div>', unsafe_allow_html=True)

        with st.spinner("Searching movies and TV shows..."):
            tmdb_results = search_tmdb(query)

        if not tmdb_results:
            st.markdown('<p style="color:#666;">No movies or TV shows found.</p>', unsafe_allow_html=True)
        else:
            # Show up to 6 results
            for item in tmdb_results[:6]:
                media_type = item.get("media_type", "movie")  # "movie" or "tv"

                # Title: movies use 'title', TV shows use 'name'
                title = item.get("title") or item.get("name") or "Unknown Title"

                # Year: movies use 'release_date', TV shows use 'first_air_date'
                date_str = item.get("release_date") or item.get("first_air_date") or ""
                year = date_str[:4] if date_str else "—"

                # Rating is out of 10 from TMDB
                vote = item.get("vote_average")
                rating_str = f"⭐ {vote:.1f} / 10" if vote else "No rating yet"

                # Type label shown in the card meta line
                type_label = "Movie" if media_type == "movie" else "TV Show"

                poster_url = get_tmdb_poster(item.get("poster_path"))

                # Fetch streaming providers for this specific title
                providers_data = get_streaming(item["id"], media_type)

                # Combine subscription streaming + free with ads + free
                all_providers = (
                    providers_data.get("flatrate", []) +
                    providers_data.get("ads", []) +
                    providers_data.get("free", [])
                )

                # Deduplicate by provider name (a service can appear in multiple tiers)
                seen = set()
                unique_providers = []
                for p in all_providers:
                    name = p.get("provider_name")
                    if name and name not in seen:
                        seen.add(name)
                        unique_providers.append(p)

                badges_html = build_badges_html(unique_providers)
                card_html   = render_card(poster_url, title, year, rating_str, type_label, badges_html)
                st.markdown(card_html, unsafe_allow_html=True)

    # ── ANIME ─────────────────────────────────
    if show_anime:
        st.markdown('<div class="section-header">🍥 Anime</div>', unsafe_allow_html=True)

        with st.spinner("Searching anime..."):
            anime_results = search_anilist(query)

        if not anime_results:
            st.markdown('<p style="color:#666;">No anime found.</p>', unsafe_allow_html=True)
        else:
            for anime in anime_results:
                # Prefer English title; fall back to romaji (Japanese romanized)
                titles = anime.get("title", {})
                title = titles.get("english") or titles.get("romaji") or "Unknown Title"

                year = str(anime.get("startDate", {}).get("year") or "—")

                # AniList scores are out of 100; convert to a /10 display
                score = anime.get("averageScore")
                if score:
                    rating_str = f"⭐ {score / 10:.1f} / 10"
                else:
                    rating_str = "No rating yet"

                # Genres as a comma-separated string
                genres = anime.get("genres", [])
                genre_str = ", ".join(genres[:3]) if genres else "—"

                # Episodes count
                eps = anime.get("episodes")
                type_label = f"Anime · {eps} eps" if eps else "Anime"
                type_label += f" · {genre_str}"

                poster_url = (anime.get("coverImage") or {}).get("large")

                # AniList doesn't have streaming data, so we note that
                badges_html = (
                    '<span class="badge-none">'
                    'Try Crunchyroll, Funimation, or HIDIVE'
                    '</span>'
                )

                card_html = render_card(poster_url, title, year, rating_str, type_label, badges_html)
                st.markdown(card_html, unsafe_allow_html=True)

else:
    # ── EMPTY STATE (no search query yet) ──
    st.markdown("""
        <div style="
            text-align: center;
            padding: 60px 20px;
            color: #444;
            font-size: 1rem;
        ">
            Start typing above to search for something to watch.
        </div>
    """, unsafe_allow_html=True)
