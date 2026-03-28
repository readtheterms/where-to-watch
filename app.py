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

# Inject CSS for dark theme and card layout
st.markdown("""
<style>
    /* Global background & text */
    .stApp { background-color: #0d0d0d; }
    body, p, span, label { color: #e0e0e0 !important; }

    header[data-testid="stHeader"] { background: transparent; }

    /* Search input */
    input[type="text"] {
        background-color: #1e1e1e !important;
        color: #ffffff !important;
        border: 1px solid #444 !important;
        border-radius: 8px !important;
        font-size: 1rem !important;
    }

    /* Result card */
    .result-card {
        background-color: #161625;
        border: 1px solid #2a2a3d;
        border-radius: 12px 12px 0 0;
        padding: 16px;
        margin-bottom: 0;
        display: flex;
        gap: 18px;
        align-items: flex-start;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
        transition: border-color 0.2s;
    }
    .result-card:hover { border-color: #5555aa; }

    /* Expander directly below a card — flush bottom edge, add gap after */
    .result-card + div {
        margin-bottom: 16px;
    }

    /* Cards with no expander need their own bottom margin */
    .result-card-standalone {
        border-radius: 12px;
        margin-bottom: 16px;
    }

    /* Poster */
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

    /* Card text */
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

    /* Streaming badges */
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
</style>
""", unsafe_allow_html=True)


# TMDB sometimes returns verbose/internal names — normalize them before display or lookup
PROVIDER_NAME_MAP = {
    "Crunchyroll Amazon Channel": "Crunchyroll",
    "Paramount+ Amazon Channel":  "Paramount Plus",
    "Peacock Premium":            "Peacock",
    "HBO Max":                    "Max",
    "Funimation Now":             "Crunchyroll",  # Funimation merged into Crunchyroll
}

# Provider URLs — keyed to match TMDB provider_name values exactly
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

# Brand colors keyed to normalized provider names
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
    "default":            "#444466",
}


# ── Helper functions ──────────────────────────────────────────────────────────

def normalize_title(title):
    """Lowercase, strip punctuation and filler words for fuzzy title matching."""
    if not title:
        return ""
    title = title.lower()
    title = re.sub(r"[^\w\s]", "", title)
    title = re.sub(r"\b(the|a|an|season|part|cour)\b", "", title)
    return re.sub(r"\s+", " ", title).strip()


def get_tmdb_poster(poster_path):
    """Return full TMDB image URL or None."""
    if poster_path:
        return f"https://image.tmdb.org/t/p/w200{poster_path}"
    return None


def build_providers(providers_data):
    """Combine all free/paid streaming tiers and deduplicate by normalized name."""
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


def build_badges_html(providers, anilist_only=False):
    """Return HTML badge row. Falls back to a suggestion for AniList-only results."""
    if anilist_only:
        return '<span class="badge-none">Try Crunchyroll or HIDIVE</span>'
    if not providers:
        return '<span class="badge-none">⚠️ Not currently available on any streaming platform</span>'

    badges = ""
    for p in providers:
        name  = p.get("provider_name", "Unknown")
        color = PROVIDER_COLORS.get(name, PROVIDER_COLORS["default"])
        url   = PROVIDER_URLS.get(name)
        if url:
            badges += (
                f'<a href="{url}" target="_blank" rel="noopener" style="text-decoration:none;">'
                f'<span class="badge" style="background-color:{color};">{name}</span>'
                f'</a>'
            )
        else:
            badges += f'<span class="badge" style="background-color:{color};">{name}</span>'
    return badges


def render_card(poster_url, title, year, rating, type_label, streaming_html, has_expander=False):
    """Return HTML for one result card. Rounded bottom corners when no expander follows."""
    extra_class = "" if has_expander else "result-card-standalone"
    if poster_url:
        poster_html = f'<img class="card-poster" src="{poster_url}" alt="{title} poster">'
    else:
        poster_html = '<div class="card-poster-placeholder">No Image</div>'

    return f"""
    <div class="result-card {extra_class}">
        {poster_html}
        <div class="card-info">
            <div class="card-title">{title}</div>
            <div class="card-meta">{year} &nbsp;·&nbsp; {type_label}</div>
            <div class="card-rating">{rating}</div>
            <div class="badge-row">{streaming_html}</div>
        </div>
    </div>
    """


def fetch_results(query):
    """
    Fetch TMDB and AniList results in parallel, then build one unified list.

    - TMDB results come first (they have real streaming data).
    - If a TMDB result title matches an AniList entry, the AniList data
      (synopsis, score, genres) is attached to it and it's labelled "Anime".
    - AniList entries with no TMDB match are appended at the end so niche
      titles aren't silently dropped.
    """
    # Step 1: search both APIs at the same time
    with ThreadPoolExecutor() as executor:
        tmdb_future    = executor.submit(search_tmdb, query)
        anilist_future = executor.submit(search_anilist, query)
        tmdb_raw    = tmdb_future.result()
        anilist_raw = anilist_future.result()

    tmdb_items = tmdb_raw[:6]

    # Step 2: fetch streaming providers for all TMDB results in parallel
    with ThreadPoolExecutor() as executor:
        provider_futures = {
            executor.submit(get_streaming, item["id"], item.get("media_type", "movie")): i
            for i, item in enumerate(tmdb_items)
        }
        providers_map = {i: f.result() for f, i in provider_futures.items()}

    # Step 3: build a normalized title index of AniList results for matching
    anilist_index = {}
    for anime in anilist_raw:
        titles = anime.get("title", {})
        for t in [titles.get("english"), titles.get("romaji")]:
            key = normalize_title(t)
            if key:
                anilist_index[key] = anime

    # Step 4: build unified list — TMDB results first, enriched where possible
    results      = []
    matched_ids  = set()

    for i, item in enumerate(tmdb_items):
        media_type = item.get("media_type", "movie")
        title      = item.get("title") or item.get("name") or "Unknown Title"
        date_str   = item.get("release_date") or item.get("first_air_date") or ""

        anilist_match = anilist_index.get(normalize_title(title))
        if anilist_match:
            matched_ids.add(id(anilist_match))

        vote       = item.get("vote_average")
        providers  = build_providers(providers_map.get(i, {}))

        results.append({
            "title":      title,
            "year":       date_str[:4] if date_str else "—",
            "rating":     vote,
            "poster_url": get_tmdb_poster(item.get("poster_path")),
            "type_label": "Anime" if anilist_match else ("Movie" if media_type == "movie" else "TV Show"),
            "providers":  providers,
            "anilist":    anilist_match,
            "source":     "tmdb",
        })

    # Step 5: append AniList-only results (no matching TMDB entry found)
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
    <h1 style="color:#ffffff; margin-bottom:0;">🎬 WhereToWatch</h1>
    <p style="color:#888; margin-top:4px; margin-bottom:24px;">
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
    # Cache by query — sort/filter changes don't re-hit the APIs
    if st.session_state.get("cached_query") != query:
        with st.spinner("Searching..."):
            st.session_state.cached_query   = query
            st.session_state.cached_results = fetch_results(query)

    results = st.session_state.cached_results

    if not results:
        st.markdown('<p style="color:#666;">No results found.</p>', unsafe_allow_html=True)
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

            rating_str  = f"⭐ {rating:.1f} / 10" if rating else "No rating yet"
            badges_html = build_badges_html(providers, anilist_only=(result["source"] == "anilist"))
            has_expander = anilist is not None

            st.markdown(
                render_card(poster_url, title, year, rating_str, type_label, badges_html, has_expander),
                unsafe_allow_html=True,
            )

            # Show AniList details (synopsis, score, genres) if available
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
        <div style="text-align:center; padding:60px 20px; color:#444; font-size:1rem;">
            Start typing above to search for something to watch.
        </div>
    """, unsafe_allow_html=True)
