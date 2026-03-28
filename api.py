import requests
import os
from dotenv import load_dotenv

load_dotenv()
TMDB_KEY = os.getenv('TMDB_API_KEY')
TMDB_BASE = 'https://api.themoviedb.org/3'


def search_tmdb(query):
    """Search TMDB for movies and TV shows. Returns a list of result dicts."""
    url = f'{TMDB_BASE}/search/multi'
    params = {'api_key': TMDB_KEY, 'query': query, 'include_adult': False}
    response = requests.get(url, params=params)
    results = response.json().get('results', [])
    # Filter out 'person' results — we only want movies and TV shows
    return [r for r in results if r.get('media_type') in ('movie', 'tv')]


def get_streaming(tmdb_id, media_type):
    """
    Get US streaming providers for a title.
    Returns a dict with keys like 'flatrate', 'ads', 'free', 'rent', 'buy'.
    We focus on 'flatrate' (subscription) and 'ads' (free with ads).
    """
    url = f'{TMDB_BASE}/{media_type}/{tmdb_id}/watch/providers'
    params = {'api_key': TMDB_KEY}
    response = requests.get(url, params=params)
    data = response.json().get('results', {})
    return data.get('US', {})


def search_anilist(query):
    """
    Search AniList for anime. Returns a list of up to 6 results.

    Changes from original:
    - Uses Page query instead of Media query so we get multiple results
    - Added startDate { year } so we can show the release year
    - Added id field for uniqueness tracking
    """
    gql_query = '''
    query ($search: String) {
      Page(perPage: 6) {
        media(search: $search, type: ANIME, sort: SEARCH_MATCH) {
          id
          title { romaji english }
          averageScore
          genres
          episodes
          startDate { year }
          coverImage { large }
          status
          description(asHtml: false)
        }
      }
    }
    '''
    response = requests.post(
        'https://graphql.anilist.co',
        json={'query': gql_query, 'variables': {'search': query}}
    )
    return response.json().get('data', {}).get('Page', {}).get('media', [])
