# WhereToWatch

A Streamlit web app that lets you search for any movie, TV show, or anime and instantly see which streaming platforms it's available on in the US.

**Live demo:** https://where-to-watch.streamlit.app

---

## Features

- Search across movies, TV shows, and anime in one unified results list
- Streaming platform badges with clickable links to each service
- Anime results enriched with synopsis, episode count, genres, and score via AniList
- Sort results by relevance, rating, or release year
- Dark theme, card-based UI

## Tech stack

- **Python / Streamlit** — frontend and app logic
- **TMDB API** — movie and TV show data, streaming provider info
- **AniList GraphQL API** — anime catalog and metadata

## Running locally

1. Clone the repo
   ```bash
   git clone https://github.com/readtheterms/where-to-watch.git
   cd where-to-watch
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your TMDB API key
   ```
   TMDB_API_KEY=your_key_here
   ```

4. Run the app
   ```bash
   streamlit run app.py
   ```

A free TMDB API key can be obtained at [themoviedb.org](https://www.themoviedb.org/settings/api). The AniList API requires no key.
