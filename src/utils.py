import unicodedata
import re
from difflib import SequenceMatcher
import requests
from config import settings

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {settings['TRAKT_ACCESS_TOKEN']}",
    "trakt-api-version": "2",
    "trakt-api-key": settings["TRAKT_CLIENT_ID"],
}


def extract_show_info(filename):
    """
    Extract show name, season, and episode from a filename/foldername
    Returns (show_name, season, episode) or None if no match
    """
    # Remove common suffixes and quality indicators
    clean_name = re.sub(
        r"(\.|\s)(1080p|2160p|720p|HDTV|WEB-DL|BluRay|WEBRip|BRRip).*", "", filename
    )

    # Try to match the pattern
    match = re.search(r"(.+?)[\.\s]S(\d{2})E(\d{2})", clean_name, re.IGNORECASE)
    if not match:
        return None

    show_name, season, episode = match.groups()
    # Convert dots to spaces and clean up
    show_name = show_name.replace(".", " ")
    # Remove year if present
    show_name = re.sub(r"\s*\(\d{4}\)\s*$", "", show_name)
    # Remove multiple spaces
    show_name = re.sub(r"\s+", " ", show_name)

    return show_name.strip(), int(season), int(episode)


def shows_match(show1, show2):
    """
    Compare two show names, returns True if they match
    Uses same logic as is_similar but specific for show name comparison
    """
    return is_similar(normalize_name(show1), normalize_name(show2))[0]


def normalize_name(name):
    name = unicodedata.normalize("NFKD", name)
    name = name.replace("/", " ")
    name = re.sub(r"(?<=[a-zA-Z])(?=\d)|(?<=\d)(?=[a-zA-Z])", " ", name)
    name = "".join(c for c in name if c.isalnum() or c.isspace())
    return name.strip().lower()


def is_similar(name1, name2):
    similarity = SequenceMatcher(None, name1, name2).ratio()
    return similarity >= 0.8, similarity


def get_shows_in_collection():
    url = f"https://api.trakt.tv/users/me/collection/shows"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def get_last_watched_and_next_episodes(show_slug, verbose=False):
    """
    Get last watched and next episodes for a show
    If verbose=True, print detailed information
    """

    # Get show ID from slug
    def get_show_id(show_slug):
        url = f"https://api.trakt.tv/shows/{show_slug}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        show_data = response.json()
        return show_data.get("ids", {}).get("trakt")

    # Fetch the show ID
    show_id = get_show_id(show_slug)
    if not show_id:
        if verbose:
            print(f"Could not fetch show ID for slug: {show_slug}")
        return None, None

    # Use the /history/shows/show_id endpoint to get the last watched episode
    url = f"https://api.trakt.tv/sync/history/shows/{show_id}?limit=1&extended=full"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    history = response.json()

    if not history:
        if verbose:
            print("No watched history found")
        # Assume the first two episodes are the next to watch
        next_episodes = []
        for season in range(1, 3):
            for episode in range(1, 3):
                url = f"https://api.trakt.tv/shows/{show_slug}/seasons/{season}/episodes/{episode}"
                response = requests.get(url, headers=HEADERS)
                if response.status_code == 200:
                    episode_data = response.json()
                    next_episodes.append(
                        {
                            "season": season,
                            "number": episode,
                            "title": episode_data.get("title", "Title not available"),
                            "id": episode_data.get("ids", {}).get("trakt"),
                        }
                    )
                    if len(next_episodes) == 2:
                        break
            if len(next_episodes) == 2:
                break

        return None, next_episodes

    last_watched_episode = history[0].get("episode", {})
    last_watched_season = last_watched_episode.get("season")
    last_watched_number = last_watched_episode.get("number")

    if not last_watched_season or not last_watched_number:
        if verbose:
            print("Could not determine the last watched episode.")
        return None, []

    if verbose:
        print(
            f"Last watched episode: S{last_watched_season:02}E{last_watched_number:02} - {last_watched_episode.get('title', 'Title not available')}"
        )

    # Determine the next episodes to watch
    next_episodes = []
    for _ in range(2):
        last_watched_number += 1
        url = f"https://api.trakt.tv/shows/{show_slug}/seasons/{last_watched_season}/episodes/{last_watched_number}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 404:
            # Move to the next season if the episode doesn't exist
            last_watched_season += 1
            last_watched_number = 1
            url = f"https://api.trakt.tv/shows/{show_slug}/seasons/{last_watched_season}/episodes/{last_watched_number}"
            response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            episode_data = response.json()
            next_episodes.append(
                {
                    "season": last_watched_season,
                    "number": last_watched_number,
                    "title": episode_data.get("title", "Title not available"),
                    "id": episode_data.get("ids", {}).get("trakt"),
                }
            )

    return last_watched_episode, next_episodes


def sanitize_filename(name):
    """Remove/replace invalid characters for filenames"""
    # Replace invalid characters with spaces
    name = re.sub(r'[<>:"/\\|?*]', " ", name)
    # Remove multiple spaces
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def find_best_show_match(test_name, shows):
    """
    Find the best matching show from collection.
    Handles matching both with and without year in the name.
    """
    best_match = None
    best_score = 0

    # Try to extract year from test_name if present
    year_match = re.search(r"\((\d{4})\)", test_name)
    test_year = year_match.group(1) if year_match else None
    # Remove year from test_name if present
    clean_test_name = re.sub(r"\s*\(\d{4}\)\s*", "", test_name)
    normalized_test = normalize_name(clean_test_name)

    print(f"Attempting to match: '{test_name}'")
    print(f"Normalized test name: '{normalized_test}'")
    if test_year:
        print(f"Detected year: {test_year}")

    for show in shows:
        show_name = show["show"]["title"]
        show_year = str(show["show"].get("year", ""))

        # Try matching just the show name
        normalized_show = normalize_name(show_name)
        _, similarity1 = is_similar(normalized_test, normalized_show)

        # Try matching show name with year
        if show_year:
            normalized_show_with_year = normalize_name(f"{show_name} ({show_year})")
            _, similarity2 = is_similar(normalized_test, normalized_show_with_year)
        else:
            similarity2 = 0

        # Use the better similarity score
        similarity = max(similarity1, similarity2)

        print(f"Comparing with: '{show_name}' ({show_year})")
        print(
            f"Similarity scores - Name only: {similarity1:.2f}, With year: {similarity2:.2f}"
        )

        # Boost score if years match (when present)
        if test_year and test_year == show_year:
            similarity += 0.1  # Bonus for matching year
            print(f"Year match bonus applied: {similarity:.2f}")

        if similarity > best_score:
            best_score = similarity
            best_match = show
            print(f"New best match: '{show_name}' with score: {similarity:.2f}")

    if best_score >= 0.8:
        print(
            f"Final match: '{best_match['show']['title']}' ({best_match['show'].get('year', '')}) with score: {best_score:.2f}"
        )
        return best_match

    print(f"No match found with score >= 0.8 (best was: {best_score:.2f})")
    return None

def get_imdb_id_from_trakt(show_slug):
  """Get IMDb ID from Trakt API"""
    url = f"https://api.trakt.tv/shows/{show_slug}"
  response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        imdb_id = response.json().get('ids', {}).get('imdb', '')
        return imdb_id.replace('tt', '') if imdb_id else None
    return None