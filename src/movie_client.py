"""
Movie & TV client — uses TMDB and OMDb APIs for movie/TV search, details, and ratings.
"""

from __future__ import annotations

import logging
import requests

from config import TMDB_API_KEY, OMDB_API_KEY, OPENROUTER_API_KEY

logger = logging.getLogger("kinoman.movie")

TMDB_BASE = "https://api.themoviedb.org/3"
OMDB_BASE = "https://www.omdbapi.com"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def search_multi(query: str) -> list[dict]:
    """
    Search for movies and TV shows by name using TMDB's multi search.

    Returns list of dicts with keys: id, title, original_title, year, media_type.
    """
    try:
        resp = requests.get(
            f"{TMDB_BASE}/search/multi",
            params={
                "api_key": TMDB_API_KEY,
                "query": query,
                "language": "he",
                "include_adult": "false",
            },
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("TMDB search error: %s", e)
        return []

    results = resp.json().get("results", [])
    out = []
    for r in results:
        media_type = r.get("media_type")
        if media_type not in ("movie", "tv"):
            continue
        if media_type == "movie":
            out.append({
                "id": r["id"],
                "title": r.get("title", ""),
                "original_title": r.get("original_title", ""),
                "year": (r.get("release_date") or "")[:4],
                "media_type": "movie",
            })
        else:
            out.append({
                "id": r["id"],
                "title": r.get("name", ""),
                "original_title": r.get("original_name", ""),
                "year": (r.get("first_air_date") or "")[:4],
                "media_type": "tv",
            })
        if len(out) >= 5:
            break
    return out


# Keep old name as alias for backward compatibility with guess flow
def search_movie(query: str) -> list[dict]:
    """Search using multi endpoint (backward-compatible wrapper)."""
    return search_multi(query)


def get_movie_details(tmdb_id: int) -> dict | None:
    """
    Get full movie details from TMDB + ratings from OMDb.

    Returns a dict with all info needed for formatting, or None on error.
    """
    try:
        # Fetch details in Hebrew
        details_resp = requests.get(
            f"{TMDB_BASE}/movie/{tmdb_id}",
            params={"api_key": TMDB_API_KEY, "language": "he"},
            timeout=10,
        )
        details_resp.raise_for_status()
        details = details_resp.json()

        # Fetch credits
        credits_resp = requests.get(
            f"{TMDB_BASE}/movie/{tmdb_id}/credits",
            params={"api_key": TMDB_API_KEY, "language": "he"},
            timeout=10,
        )
        credits_resp.raise_for_status()
        credits = credits_resp.json()

        # Fetch similar movies (in Hebrew)
        similar_resp = requests.get(
            f"{TMDB_BASE}/movie/{tmdb_id}/similar",
            params={"api_key": TMDB_API_KEY, "language": "he"},
            timeout=10,
        )
        similar_resp.raise_for_status()
        similar = similar_resp.json().get("results", [])[:3]

    except requests.RequestException as e:
        logger.error("TMDB details error: %s", e)
        return None

    # Get IMDb ID for OMDb lookup
    imdb_id = details.get("imdb_id")
    omdb_data = {}
    if imdb_id and OMDB_API_KEY:
        try:
            omdb_resp = requests.get(
                OMDB_BASE,
                params={"apikey": OMDB_API_KEY, "i": imdb_id},
                timeout=10,
            )
            omdb_resp.raise_for_status()
            omdb_data = omdb_resp.json()
        except requests.RequestException as e:
            logger.error("OMDb error: %s", e)

    # Extract cast (top 5)
    cast = credits.get("cast", [])[:5]
    cast_list = [
        {"name": c.get("name", ""), "character": c.get("character", "")}
        for c in cast
    ]

    # Extract director and writers from crew
    crew = credits.get("crew", [])
    directors = [c["name"] for c in crew if c.get("job") == "Director"]
    writers = [
        c["name"]
        for c in crew
        if c.get("job") in ("Screenplay", "Writer", "Story")
    ]

    # Extract genres
    genres = [g["name"] for g in details.get("genres", [])]

    # Extract countries and languages
    countries = [c["name"] for c in details.get("production_countries", [])]
    languages = [l["name"] for l in details.get("spoken_languages", [])]

    # Extract ratings from OMDb
    imdb_rating = omdb_data.get("imdbRating", "N/A")
    rt_rating = "N/A"
    metacritic = omdb_data.get("Metascore", "N/A")
    for rating in omdb_data.get("Ratings", []):
        if rating["Source"] == "Rotten Tomatoes":
            rt_rating = rating["Value"]
    awards = omdb_data.get("Awards", "")
    if awards in ("N/A", ""):
        awards = None

    # Similar movies
    similar_names = []
    for s in similar:
        name = s.get("title") or s.get("original_title", "")
        if name:
            similar_names.append(name)

    # Get original (non-Hebrew) details for original title
    original_title = details.get("original_title", "")
    hebrew_title = details.get("title", "")

    return {
        "hebrew_title": hebrew_title,
        "original_title": original_title,
        "year": (details.get("release_date") or "")[:4],
        "genres": ", ".join(genres) if genres else "N/A",
        "runtime": details.get("runtime") or "N/A",
        "countries": ", ".join(countries) if countries else "N/A",
        "languages": ", ".join(languages) if languages else "N/A",
        "imdb_rating": imdb_rating,
        "rt_rating": rt_rating,
        "metacritic": metacritic,
        "cast": cast_list,
        "directors": ", ".join(directors) if directors else "N/A",
        "writers": ", ".join(writers) if writers else "N/A",
        "overview": details.get("overview") or "אין תקציר זמין",
        "awards": awards,
        "similar": similar_names,
    }


def get_tv_details(tmdb_id: int) -> dict | None:
    """
    Get full TV show details from TMDB + ratings from OMDb.

    Returns a dict with all info needed for formatting, or None on error.
    """
    try:
        details_resp = requests.get(
            f"{TMDB_BASE}/tv/{tmdb_id}",
            params={"api_key": TMDB_API_KEY, "language": "he"},
            timeout=10,
        )
        details_resp.raise_for_status()
        details = details_resp.json()

        credits_resp = requests.get(
            f"{TMDB_BASE}/tv/{tmdb_id}/credits",
            params={"api_key": TMDB_API_KEY, "language": "he"},
            timeout=10,
        )
        credits_resp.raise_for_status()
        credits = credits_resp.json()

        similar_resp = requests.get(
            f"{TMDB_BASE}/tv/{tmdb_id}/similar",
            params={"api_key": TMDB_API_KEY, "language": "he"},
            timeout=10,
        )
        similar_resp.raise_for_status()
        similar = similar_resp.json().get("results", [])[:3]

        # Get IMDb ID via external_ids
        ext_resp = requests.get(
            f"{TMDB_BASE}/tv/{tmdb_id}/external_ids",
            params={"api_key": TMDB_API_KEY},
            timeout=10,
        )
        ext_resp.raise_for_status()
        imdb_id = ext_resp.json().get("imdb_id")

    except requests.RequestException as e:
        logger.error("TMDB TV details error: %s", e)
        return None

    omdb_data = {}
    if imdb_id and OMDB_API_KEY:
        try:
            omdb_resp = requests.get(
                OMDB_BASE,
                params={"apikey": OMDB_API_KEY, "i": imdb_id},
                timeout=10,
            )
            omdb_resp.raise_for_status()
            omdb_data = omdb_resp.json()
        except requests.RequestException as e:
            logger.error("OMDb error: %s", e)

    cast = credits.get("cast", [])[:5]
    cast_list = [
        {"name": c.get("name", ""), "character": c.get("character", "")}
        for c in cast
    ]

    genres = [g["name"] for g in details.get("genres", [])]
    countries = [c["name"] for c in details.get("production_countries", [])]
    languages = [l["name"] for l in details.get("spoken_languages", [])]

    creators = [c["name"] for c in details.get("created_by", [])]

    imdb_rating = omdb_data.get("imdbRating", "N/A")
    rt_rating = "N/A"
    metacritic = omdb_data.get("Metascore", "N/A")
    for rating in omdb_data.get("Ratings", []):
        if rating["Source"] == "Rotten Tomatoes":
            rt_rating = rating["Value"]
    awards = omdb_data.get("Awards", "")
    if awards in ("N/A", ""):
        awards = None

    similar_names = []
    for s in similar:
        name = s.get("name") or s.get("original_name", "")
        if name:
            similar_names.append(name)

    status_map = {
        "Returning Series": "בשידור",
        "Ended": "הסתיים",
        "Canceled": "בוטל",
        "In Production": "בהפקה",
    }
    raw_status = details.get("status", "")
    status = status_map.get(raw_status, raw_status)

    return {
        "hebrew_title": details.get("name", ""),
        "original_title": details.get("original_name", ""),
        "year": (details.get("first_air_date") or "")[:4],
        "genres": ", ".join(genres) if genres else "N/A",
        "seasons": details.get("number_of_seasons", "N/A"),
        "episodes": details.get("number_of_episodes", "N/A"),
        "status": status,
        "countries": ", ".join(countries) if countries else "N/A",
        "languages": ", ".join(languages) if languages else "N/A",
        "imdb_rating": imdb_rating,
        "rt_rating": rt_rating,
        "metacritic": metacritic,
        "cast": cast_list,
        "creators": ", ".join(creators) if creators else "N/A",
        "overview": details.get("overview") or "אין תקציר זמין",
        "awards": awards,
        "similar": similar_names,
    }


def format_tv_response(d: dict) -> str:
    """Format TV show details into the Hebrew response template."""
    cast_lines = []
    for c in d["cast"]:
        if c["character"]:
            cast_lines.append(f"• {c['name']} — בתפקיד {c['character']}")
        else:
            cast_lines.append(f"• {c['name']}")
    cast_str = "\n".join(cast_lines) if cast_lines else "N/A"

    similar_str = ", ".join(d["similar"]) if d["similar"] else "N/A"

    verdict = _get_verdict(d)

    lines = [
        f"📺 {d['hebrew_title']} / {d['original_title']} ({d['year']})",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"⭐  IMDb:  {d['imdb_rating']}/10",
        f"🍅  Rotten Tomatoes:  {d['rt_rating']}",
        f"Ⓜ️  Metacritic:  {d['metacritic']}/100",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if verdict:
        lines.append(f"      {verdict}")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    lines += [
        "",
        f"🎭 ז'אנר: {d['genres']}",
        f"📺 עונות: {d['seasons']} | פרקים: {d['episodes']}",
        f"📡 סטטוס: {d['status']}",
        f"🌍 מדינה / שפה: {d['countries']} / {d['languages']}",
        "",
        "🎭 שחקנים ראשיים:",
        cast_str,
        "",
        f"🎬 יוצר: {d['creators']}",
        "",
        "📝 תקציר:",
        d["overview"],
    ]

    if d["awards"]:
        lines.append("")
        lines.append(f"🏆 פרסים בולטים: {d['awards']}")

    lines.append("")
    lines.append(f"🍿 אם אהבת את זה: {similar_str}")

    return "\n".join(lines)


def is_description(text: str) -> bool:
    """Heuristic: if the text is long or has multiple words, it's likely a description."""
    words = text.split()
    return len(words) >= 4


def guess_movie_from_description(description: str) -> list[str]:
    """
    Use a free LLM via OpenRouter to guess movie names from a plot description.

    Returns a list of up to 3 movie title guesses (in English).
    """
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY not set")
        return []

    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "google/gemini-2.0-flash-001",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a movie and TV show identification assistant. "
                            "The user will describe a movie or TV show plot, characters, actors, or scenes. "
                            "Reply ONLY with the most likely movie or TV show title(s) in English, one per line. "
                            "Maximum 3 guesses, most likely first. "
                            "No explanations, no numbering, just the titles."
                        ),
                    },
                    {"role": "user", "content": description},
                ],
                "max_tokens": 100,
            },
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("OpenRouter error: %s", e)
        return []

    data = resp.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    # Parse lines into movie titles
    titles = [line.strip().strip("-•*123.") .strip() for line in content.strip().split("\n")]
    return [t for t in titles if t][:3]


# ── Genre-based rating thresholds ──────────────────────────────────
# Maps genre categories to the IMDb threshold for "good"
_LIGHT_GENRES = {"קומדיה", "רומנטי", "אנימציה", "משפחה", "מוזיקה",
                 "Comedy", "Romance", "Animation", "Family", "Music"}
_MEDIUM_GENRES = {"אקשן", "הרפתקאות", "פנטזיה", "מדע בדיוני", "מותחן",
                  "מסתורין", "אימה",
                  "Action", "Adventure", "Fantasy", "Science Fiction",
                  "Thriller", "Mystery", "Horror"}
_HEAVY_GENRES = {"דרמה", "פשע", "מלחמה", "היסטוריה", "דוקומנטרי",
                 "Drama", "Crime", "War", "History", "Documentary"}

_THRESHOLD_LIGHT = 6.3
_THRESHOLD_MEDIUM = 6.8
_THRESHOLD_HEAVY = 7.2


def _get_genre_threshold(genres_str: str) -> float:
    """Determine the IMDb threshold based on the movie's genres."""
    genres = {g.strip() for g in genres_str.split(",")}
    if genres & _HEAVY_GENRES:
        return _THRESHOLD_HEAVY
    if genres & _MEDIUM_GENRES:
        return _THRESHOLD_MEDIUM
    if genres & _LIGHT_GENRES:
        return _THRESHOLD_LIGHT
    return _THRESHOLD_MEDIUM  # default


def _get_verdict(d: dict) -> str:
    """Generate a fun Hebrew verdict about whether the movie is worth watching."""
    imdb = d["imdb_rating"]
    if imdb == "N/A":
        return ""

    try:
        score = float(imdb)
    except ValueError:
        return ""

    threshold = _get_genre_threshold(d["genres"])
    diff = score - threshold

    # Also factor in RT if available
    rt_boost = 0
    rt = d["rt_rating"]
    if rt != "N/A":
        try:
            rt_num = int(rt.replace("%", ""))
            if rt_num >= 90:
                rt_boost = 0.3
            elif rt_num >= 75:
                rt_boost = 0.1
            elif rt_num < 50:
                rt_boost = -0.2
        except ValueError:
            pass

    diff += rt_boost

    if diff >= 2.0:
        return "🏆🔥 יצירת מופת — חובה לראות!"
    if diff >= 1.2:
        return "🔥 מעולה — שווה כל דקה"
    if diff >= 0.5:
        return "👍 סרט טוב — מומלץ"
    if diff >= 0.0:
        return "🤷 סביר — תלוי בטעם שלך"
    if diff >= -0.8:
        return "😐 בינוני — יש טובים ממנו"
    return "👎 חלש — אולי תבחר משהו אחר"


def format_movie_response(d: dict) -> str:
    """Format movie details into the Hebrew response template."""
    # Cast list
    cast_lines = []
    for c in d["cast"]:
        if c["character"]:
            cast_lines.append(f"• {c['name']} — בתפקיד {c['character']}")
        else:
            cast_lines.append(f"• {c['name']}")
    cast_str = "\n".join(cast_lines) if cast_lines else "N/A"

    # Similar movies
    similar_str = ", ".join(d["similar"]) if d["similar"] else "N/A"

    # Verdict
    verdict = _get_verdict(d)

    # ── Build response — ratings first, big and bold ──
    lines = [
        f"🎬 {d['hebrew_title']} / {d['original_title']} ({d['year']})",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"⭐  IMDb:  {d['imdb_rating']}/10",
        f"🍅  Rotten Tomatoes:  {d['rt_rating']}",
        f"Ⓜ️  Metacritic:  {d['metacritic']}/100",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if verdict:
        lines.append(f"      {verdict}")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    lines += [
        "",
        f"🎭 ז'אנר: {d['genres']}",
        f"⏱️ אורך: {d['runtime']} דקות",
        f"🌍 מדינה / שפה: {d['countries']} / {d['languages']}",
        "",
        "🎭 שחקנים ראשיים:",
        cast_str,
        "",
        f"🎬 במאי: {d['directors']}",
        f"✍️ תסריט: {d['writers']}",
        "",
        "📝 תקציר:",
        d["overview"],
    ]

    if d["awards"]:
        lines.append("")
        lines.append(f"🏆 פרסים בולטים: {d['awards']}")

    lines.append("")
    lines.append(f"🍿 אם אהבת את זה: {similar_str}")

    return "\n".join(lines)
