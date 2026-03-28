import streamlit as st
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

    /* Section divider */
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
    "Netflix":               "https://www.netflix.com",
    "Disney Plus":           "https://www.disneyplus.com",
    "Hulu":                  "https://www.hulu.com",
    "Amazon Prime Video":    "https://www.amazon.com/primevideo",
    "Max":                   "https://www.max.com",
    "HBO Max":               "https://www.max.com",
    "Apple TV Plus":         "https://tv.apple.com",
    "Peacock":               "https://www.peacocktv.com",
    "Peacock Premium":       "https://www.peacocktv.com",
    "Paramount Plus":        "https://www.paramountplus.com",
    "Paramount+ Amazon Channel": "https://www.paramountplus.com",
    "Crunchyroll":           "https://www.crunchyroll.com",
    "Funimation Now":        "https://www.funimation.com",
    "HIDIVE":                "https://www.hidive.com",
    "Tubi TV":               "https://tubitv.com",
    "Pluto TV":              "https://pluto.tv",
    "Shudder":               "https://www.shudder.com",
    "Mubi":                  "https://mubi.com",
}

# Brand colors keyed to TMDB provider_name values
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


def get_tmdb_poster(poster_path):
    """Return full TMDB image URL or None."""
    if poster_path:
        return f"https://image.tmdb.org/t/p/w200{poster_path}"
    return None


def build_badges_html(providers):
    """Build HTML badge row from a list of provider dicts."""
    if not providers:
        return '<span class="badge-none">⚠️ Not currently available on any streaming platform</span>'

    badges = ""
    seen_names = set()
    for p in providers:
        name = PROVIDER_NAME_MAP.get(p.get("provider_name", ""), p.get("provider_name", "Unknown"))
        # After normalization two entries can collapse to the same name — skip duplicates
        if name in seen_names:
            continue
        seen_names.add(name)
        color = PROVIDER_COLORS.get(name, PROVIDER_COLORS["default"])
        url   = PROVIDER_URLS.get(name)

        if url:
            # target="_blank" + rel="noopener" is standard for external links
            badges += (
                f'<a href="{url}" target="_blank" rel="noopener" style="text-decoration:none;">'
                f'<span class="badge" style="background-color:{color};">{name}</span>'
                f'</a>'
            )
        else:
            badges += f'<span class="badge" style="background-color:{color};">{name}</span>'
    return badges


def render_card(poster_url, title, year, rating, type_label, streaming_html):
    """Return the HTML string for one result card."""
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
    # ── Movies & TV ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📺 Movies &amp; TV Shows</div>', unsafe_allow_html=True)

    with st.spinner("Searching movies and TV shows..."):
        tmdb_results = search_tmdb(query)

        enriched = []
        for item in tmdb_results[:6]:
            media_type     = item.get("media_type", "movie")
            providers_data = get_streaming(item["id"], media_type)

            all_providers = (
                providers_data.get("flatrate", []) +
                providers_data.get("ads", []) +
                providers_data.get("free", [])
            )

            # A provider can appear in multiple tiers — deduplicate by name
            seen, unique_providers = set(), []
            for p in all_providers:
                pname = p.get("provider_name")
                if pname and pname not in seen:
                    seen.add(pname)
                    unique_providers.append(p)

            enriched.append({"item": item, "providers": unique_providers})

        if not tmdb_results:
            st.markdown('<p style="color:#666;">No movies or TV shows found.</p>', unsafe_allow_html=True)
        else:
            sort_by = st.selectbox(
                "Sort by",
                options=["Relevance", "Rating (high to low)", "Release year (newest first)"],
                label_visibility="collapsed",
            )

            if sort_by == "Rating (high to low)":
                enriched.sort(key=lambda e: e["item"].get("vote_average") or 0, reverse=True)
            elif sort_by == "Release year (newest first)":
                def get_year(e):
                    date = e["item"].get("release_date") or e["item"].get("first_air_date") or ""
                    return date[:4] if date else "0"
                enriched.sort(key=get_year, reverse=True)
            # "Relevance" keeps TMDB's default order

            for entry in enriched:
                item       = entry["item"]
                providers  = entry["providers"]
                media_type = item.get("media_type", "movie")

                # movies → 'title' + 'release_date'; TV → 'name' + 'first_air_date'
                title    = item.get("title") or item.get("name") or "Unknown Title"
                date_str = item.get("release_date") or item.get("first_air_date") or ""
                year     = date_str[:4] if date_str else "—"

                vote       = item.get("vote_average")
                rating_str = f"⭐ {vote:.1f} / 10" if vote else "No rating yet"
                type_label = "Movie" if media_type == "movie" else "TV Show"
                poster_url = get_tmdb_poster(item.get("poster_path"))

                badges_html = build_badges_html(providers)
                st.markdown(render_card(poster_url, title, year, rating_str, type_label, badges_html), unsafe_allow_html=True)

    # ── Anime ─────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🍥 Anime</div>', unsafe_allow_html=True)

    with st.spinner("Searching anime..."):
        anime_results = search_anilist(query)

    if not anime_results:
        st.markdown('<p style="color:#666;">No anime found.</p>', unsafe_allow_html=True)
    else:
        for anime in anime_results:
            titles = anime.get("title", {})
            title  = titles.get("english") or titles.get("romaji") or "Unknown Title"
            year   = str(anime.get("startDate", {}).get("year") or "—")

            # AniList scores are /100; display as /10 to match TMDB
            score      = anime.get("averageScore")
            rating_str = f"⭐ {score / 10:.1f} / 10" if score else "No rating yet"

            genres     = anime.get("genres", [])
            genre_str  = ", ".join(genres[:3]) if genres else "—"
            # AniList episode counts are per-entry, not total series — omit from card but still show in expander
            eps        = anime.get("episodes")
            type_label = f"Anime · {genre_str}"

            poster_url  = (anime.get("coverImage") or {}).get("large")

            # AniList has no streaming data — point users to likely sources
            badges_html = '<span class="badge-none">Try Crunchyroll or HIDIVE</span>'

            st.markdown(render_card(poster_url, title, year, rating_str, type_label, badges_html), unsafe_allow_html=True)

            with st.expander("More details"):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"**Episodes:** {eps if eps else 'Unknown'}")
                    st.markdown(f"**Score:** {score}/100" if score else "**Score:** N/A")
                    status = anime.get("status", "").replace("_", " ").title()
                    st.markdown(f"**Status:** {status or 'Unknown'}")

                with col2:
                    st.markdown(f"**Genres:** {', '.join(genres) if genres else '—'}")

                # description is returned as plain text (asHtml: false in api.py)
                description = anime.get("description", "")
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
