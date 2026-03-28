import re
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
from api import search_tmdb, get_streaming, search_anilist

# Must be the first Streamlit call
st.set_page_config(
    page_title="WhereToWatch",
    page_icon="📺",
    layout="wide",
)

st.markdown("""
<style>
    /* ── Base ── */
    .stApp { background-color: #060d17; }
    body, p, span, label, div { color: #d9e8ed !important; }
    header[data-testid="stHeader"] { background: transparent; }

    /* ── Sticky search area ── */
    [data-testid="stTextInput"] {
        position: sticky;
        top: 0;
        z-index: 999;
        background-color: #060d17;
        padding-bottom: 8px;
    }

    /* ── Search input ── */
    input[type="text"] {
        background-color: #0d1a2e !important;
        color: #ffffff !important;
        border: 1px solid #1e2d45 !important;
        border-radius: 8px !important;
        font-size: 1rem !important;
    }
    input[type="text"]:focus {
        border-color: #fbc500 !important;
        box-shadow: 0 0 0 2px rgba(251,197,0,0.15) !important;
    }

    /* ── Sort radio pills ── */
    div[role="radiogroup"] { display: flex; gap: 8px; }
    div[role="radiogroup"] label {
        background-color: #0d1a2e;
        border: 1px solid #1e2d45;
        border-radius: 20px;
        padding: 4px 16px;
        cursor: pointer;
        font-size: 0.85rem;
        transition: border-color 0.2s, background 0.2s;
    }
    div[role="radiogroup"] label:hover { border-color: #fbc500; }

    /* ── Result card ── */
    .result-card {
        background-color: #0d1a2e;
        border: 1px solid #1e2d45;
        border-radius: 12px 12px 0 0;
        padding: 18px;
        margin-bottom: 0;
        display: flex;
        gap: 20px;
        align-items: flex-start;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
        transition: border-color 0.2s;
    }
    .result-card:hover { border-color: #fbc500; }
    .result-card-standalone {
        border-radius: 12px;
        margin-bottom: 16px;
    }

    /* ── Expander flush below card ── */
    .result-card + div { margin-bottom: 16px; }

    /* ── Poster ── */
    .card-poster {
        width: 120px;
        min-width: 120px;
        height: 180px;
        border-radius: 8px;
        object-fit: cover;
        background-color: #111d2e;
    }
    .card-poster-placeholder {
        width: 120px;
        min-width: 120px;
        height: 180px;
        border-radius: 8px;
        background-color: #111d2e;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #3a4a60;
        font-size: 0.7rem;
        text-align: center;
    }

    /* ── Card text ── */
    .card-info { flex: 1; min-width: 0; }
    .card-title {
        font-size: 1.1rem;
        font-weight: 800;
        color: #ffffff !important;
        margin: 0 0 4px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .card-meta {
        font-size: 0.82rem;
        color: #6b8caa !important;
        margin-bottom: 6px;
    }
    .card-rating {
        font-size: 0.9rem;
        font-weight: 600;
        color: #fbc500 !important;
        margin-bottom: 12px;
    }

    /* ── Provider logos ── */
    .provider-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: center;
    }
    .provider-logo-wrap {
        display: inline-block;
        border-radius: 8px;
        overflow: hidden;
        transition: transform 0.15s, box-shadow 0.15s;
    }
    .provider-logo-wrap:hover {
        transform: scale(1.1);
        box-shadow: 0 0 8px rgba(251,197,0,0.5);
    }
    .provider-logo {
        width: 42px;
        height: 42px;
        object-fit: cover;
        display: block;
    }

    /* ── Text fallback for providers without logos ── */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        color: #ffffff !important;
        white-space: nowrap;
    }
    .badge-none { color: #3a4a60 !important; font-size: 0.82rem; }
</style>
""", unsafe_allow_html=True)


# ── Provider data ─────────────────────────────────────────────────────────────

PROVIDER_NAME_MAP = {
    "Crunchyroll Amazon Channel": "Crunchyroll",
    "Paramount+ Amazon Channel":  "Paramount Plus",
    "Peacock Premium":            "Peacock",
    "HBO Max":                    "Max",
    "Funimation Now":             "Crunchyroll",
}

PROVIDER_URLS = {
    "Netflix":            "https://www.netflix.com",
    "Disney Plus":        "https://www.disneyplus.com",
    "Hulu":               "https://www.hulu.com",
    "Amazon Prime Video": "https://www.amazon.com/primevideo",
    "Max":                "https://www.max.com",
    "Apple TV Plus":      "https://tv.apple.com",
    "Peacock":            "https://www.peacocktv.com",
    "Paramount Plus":     "https://www.paramountplus.com",
    "Crunchyroll":        "https://www.crunchyroll.com",
    "HIDIVE":             "https://www.hidive.com",
    "Tubi TV":            "https://tubitv.com",
    "Pluto TV":           "https://pluto.tv",
    "Shudder":            "https://www.shudder.com",
    "Mubi":               "https://mubi.com",
}

# Fallback colors for providers where TMDB has no logo
PROVIDER_COLORS = {
    "Netflix":            "#E50914",
    "Disney Plus":        "#113CCF",
    "Hulu":               "#1CE783",
    "Amazon Prime Video": "#00A8E0",
    "Max":                "#002BE7",
    "Apple TV Plus":      "#555555",
    "Peacock":            "#E8A020",
    "Paramount Plus":     "#0064FF",
    "Crunchyroll":        "#F47521",
    "HIDIVE":             "#00AACC",
    "Tubi TV":            "#FA4B05",
    "Pluto TV":           "#FFC619",
    "Shudder":            "#2D2D2D",
    "Mubi":               "#1B1B1B",
    "default":            "#1e2d45",
}

TMDB_LOGO_BASE = "https://image.tmdb.org/t/p/w45"


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalize_title(title):
    """Lowercase and strip punctuation/filler words for fuzzy title matching."""
    if not title:
        return ""
    title = title.lower()
    title = re.sub(r"[^\w\s]", "", title)
    title = re.sub(r"\b(the|a|an|season|part|cour)\b", "", title)
    return re.sub(r"\s+", " ", title).strip()


def get_tmdb_poster(poster_path):
    """Return full TMDB poster URL or None."""
    return f"https://image.tmdb.org/t/p/w200{poster_path}" if poster_path else None


def build_providers(providers_data):
    """Combine all streaming tiers, normalize names, deduplicate."""
    all_providers = (
        providers_data.get("flatrate", []) +
        providers_data.get("ads", []) +
        providers_data.get("free", [])
    )
    seen, unique = set(), []
    for p in all_providers:
        name = PROVIDER_NAME_MAP.get(p.get("provider_name", ""), p.get("provider_name", ""))
        if name and name not in seen:
            seen.add(name)
            unique.append({**p, "provider_name": name})
    return unique


def build_providers_html(providers, anilist_only=False):
    """
    Render provider logos from TMDB's logo_path where available.
    Falls back to a colored text badge if no logo exists.
    """
    if anilist_only:
        return '<span class="badge-none">Try Crunchyroll or HIDIVE</span>'
    if not providers:
        return '<span class="badge-none">⚠️ Not available on any streaming platform</span>'

    html = ""
    for p in providers:
        name      = p.get("provider_name", "Unknown")
        logo_path = p.get("logo_path")
        url       = PROVIDER_URLS.get(name, "#")
        link_open = f'<a href="{url}" target="_blank" rel="noopener" style="text-decoration:none;" title="{name}">'
        link_close = "</a>"

        if logo_path:
            html += (
                f'{link_open}'
                f'<span class="provider-logo-wrap">'
                f'<img class="provider-logo" src="{TMDB_LOGO_BASE}{logo_path}" alt="{name}">'
                f'</span>'
                f'{link_close}'
            )
        else:
            color = PROVIDER_COLORS.get(name, PROVIDER_COLORS["default"])
            html += (
                f'{link_open}'
                f'<span class="badge" style="background-color:{color};">{name}</span>'
                f'{link_close}'
            )
    return html


def render_card(poster_url, title, year, rating, type_label, providers_html, has_expander=False):
    """Return the HTML string for one result card."""
    extra_class = "" if has_expander else "result-card-standalone"
    poster_html = (
        f'<img class="card-poster" src="{poster_url}" alt="{title} poster">'
        if poster_url else
        '<div class="card-poster-placeholder">No Image</div>'
    )
    return f"""
    <div class="result-card {extra_class}">
        {poster_html}
        <div class="card-info">
            <div class="card-title">{title}</div>
            <div class="card-meta">{year} &nbsp;·&nbsp; {type_label}</div>
            <div class="card-rating">{rating}</div>
            <div class="provider-row">{providers_html}</div>
        </div>
    </div>
    """


def fetch_results(query):
    """
    Query TMDB and AniList in parallel, merge into one deduplicated list.
    TMDB results (with streaming data) come first; AniList enriches them
    with anime metadata. Unmatched AniList titles are appended at the end.
    """
    with ThreadPoolExecutor() as executor:
        tmdb_future    = executor.submit(search_tmdb, query)
        anilist_future = executor.submit(search_anilist, query)
        tmdb_raw    = tmdb_future.result()
        anilist_raw = anilist_future.result()

    tmdb_items = tmdb_raw[:6]

    with ThreadPoolExecutor() as executor:
        provider_futures = {
            executor.submit(get_streaming, item["id"], item.get("media_type", "movie")): i
            for i, item in enumerate(tmdb_items)
        }
        providers_map = {i: f.result() for f, i in provider_futures.items()}

    anilist_index = {}
    for anime in anilist_raw:
        titles = anime.get("title", {})
        for t in [titles.get("english"), titles.get("romaji")]:
            key = normalize_title(t)
            if key:
                anilist_index[key] = anime

    results     = []
    matched_ids = set()

    for i, item in enumerate(tmdb_items):
        media_type    = item.get("media_type", "movie")
        title         = item.get("title") or item.get("name") or "Unknown Title"
        date_str      = item.get("release_date") or item.get("first_air_date") or ""
        anilist_match = anilist_index.get(normalize_title(title))

        if anilist_match:
            matched_ids.add(id(anilist_match))

        results.append({
            "title":      title,
            "year":       date_str[:4] if date_str else "—",
            "rating":     item.get("vote_average"),
            "poster_url": get_tmdb_poster(item.get("poster_path")),
            "type_label": "Anime" if anilist_match else ("Movie" if media_type == "movie" else "TV Show"),
            "providers":  build_providers(providers_map.get(i, {})),
            "anilist":    anilist_match,
            "source":     "tmdb",
        })

    for anime in anilist_raw:
        if id(anime) in matched_ids:
            continue
        titles = anime.get("title", {})
        title  = titles.get("english") or titles.get("romaji") or "Unknown Title"
        score  = anime.get("averageScore")
        results.append({
            "title":      title,
            "year":       str(anime.get("startDate", {}).get("year") or "—"),
            "rating":     score / 10 if score else None,
            "poster_url": (anime.get("coverImage") or {}).get("large"),
            "type_label": "Anime",
            "providers":  [],
            "anilist":    anime,
            "source":     "anilist",
        })

    return results


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
    <h1 style="color:#ffffff; font-weight:900; margin-bottom:0; letter-spacing:-0.5px;">
        📺 WhereToWatch
    </h1>
    <p style="color:#6b8caa; margin-top:4px; margin-bottom:20px; font-size:0.95rem;">
        Search any movie, TV show, or anime to find where it streams.
    </p>
""", unsafe_allow_html=True)

# ── Search bar ────────────────────────────────────────────────────────────────
query = st.text_input(
    label="search",
    placeholder="e.g.  Interstellar,  Attack on Titan,  The Bear ...",
    label_visibility="collapsed",
)

# ── Results ───────────────────────────────────────────────────────────────────
if query:
    if st.session_state.get("cached_query") != query:
        with st.spinner("Searching..."):
            st.session_state.cached_query   = query
            st.session_state.cached_results = fetch_results(query)

    results = st.session_state.cached_results

    if not results:
        st.markdown('<p style="color:#3a4a60;">No results found.</p>', unsafe_allow_html=True)
    else:
        sort_by = st.radio(
            "Sort by",
            options=["Relevance", "Rating (high to low)", "Release year (newest first)"],
            horizontal=True,
            label_visibility="collapsed",
        )

        sorted_results = list(results)
        if sort_by == "Rating (high to low)":
            sorted_results.sort(key=lambda r: r["rating"] or 0, reverse=True)
        elif sort_by == "Release year (newest first)":
            sorted_results.sort(key=lambda r: r["year"], reverse=True)

        for result in sorted_results:
            title      = result["title"]
            year       = result["year"]
            type_label = result["type_label"]
            poster_url = result["poster_url"]
            providers  = result["providers"]
            anilist    = result["anilist"]
            rating     = result["rating"]

            rating_str    = f"⭐ {rating:.1f} / 10" if rating else "No rating yet"
            providers_html = build_providers_html(providers, anilist_only=(result["source"] == "anilist"))
            has_expander  = anilist is not None

            st.markdown(
                render_card(poster_url, title, year, rating_str, type_label, providers_html, has_expander),
                unsafe_allow_html=True,
            )

            if has_expander:
                genres      = anilist.get("genres", [])
                eps         = anilist.get("episodes")
                score       = anilist.get("averageScore")
                status      = anilist.get("status", "").replace("_", " ").title()
                description = anilist.get("description", "")

                with st.expander("More details"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Episodes:** {eps if eps else 'Unknown'}")
                        st.markdown(f"**Score:** {score}/100" if score else "**Score:** N/A")
                        st.markdown(f"**Status:** {status or 'Unknown'}")
                    with col2:
                        st.markdown(f"**Genres:** {', '.join(genres) if genres else '—'}")

                    if description:
                        if len(description) > 500:
                            description = description[:500].rstrip() + "…"
                        st.markdown(f"**Synopsis:** {description}")
                    else:
                        st.markdown("*No synopsis available.*")

else:
    st.markdown("""
        <div style="text-align:center; padding:80px 20px; color:#1e2d45; font-size:1rem;">
            Start typing above to search for something to watch.
        </div>
    """, unsafe_allow_html=True)
