import requests
from difflib import SequenceMatcher
import unicodedata
import re
import base64
import xml.etree.ElementTree as ET
from config import settings

# Use settings directly
TRAKT_CLIENT_ID = settings['TRAKT_CLIENT_ID']
TRAKT_ACCESS_TOKEN = settings['TRAKT_ACCESS_TOKEN']
NZBGEEK_API_KEY = settings['NZBGEEK_API_KEY']
NZBGET_URL = settings['NZBGET_URL']
NZBGET_USERNAME = settings['NZBGET_USERNAME']
NZBGET_PASSWORD = settings['NZBGET_PASSWORD']
RESOLUTIONS = settings['RESOLUTIONS']

MAX_RESULTS = 50
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TRAKT_ACCESS_TOKEN}",
    "trakt-api-version": "2",
    "trakt-api-key": TRAKT_CLIENT_ID,
}

# Normalize strings
def normalize_name(name):
    name = unicodedata.normalize('NFKD', name)
    name = name.replace("/", " ")
    name = re.sub(r"(?<=[a-zA-Z])(?=\d)|(?<=\d)(?=[a-zA-Z])", " ", name)
    name = ''.join(c for c in name if c.isalnum() or c.isspace())
    return name.strip().lower()

# Extract show title from NZB name
def extract_title_from_nzb(nzb_title):
    nzb_title = re.sub(r"\.S\d{2}E\d{2}.*", "", nzb_title)
    nzb_title = re.sub(r"\.\d{4}\..*", "", nzb_title)
    nzb_title = re.sub(r"[^a-zA-Z0-9\s]", " ", nzb_title)
    return normalize_name(nzb_title)

# Check similarity between two strings
def is_similar(name1, name2):
    similarity = SequenceMatcher(None, name1, name2).ratio()
    return similarity >= 0.8, similarity

# Validate if NZB matches the intended show
def is_valid_nzb(show_name, nzb_title, include_year=False, year=None):
    normalized_show_name = normalize_name(show_name)
    if include_year and year:
        normalized_show_name += f" {year}"
    extracted_title = extract_title_from_nzb(nzb_title)

    similar, similarity_score = is_similar(normalized_show_name, extracted_title)

    print(f"Query Show Title (Normalized): {normalized_show_name}")
    print(f"NZB Extracted Title: {extracted_title}")
    print(f"Similarity: {similarity_score:.2f}")

    return similar

# Check if an episode has been watched
def has_been_watched(episode_id):
    url = f"https://api.trakt.tv/sync/history/episodes/{episode_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    history = response.json()

    for item in history:
        if item.get("episode", {}).get("ids", {}).get("trakt") == episode_id:
            return True

    return False

def get_last_watched_and_next_episodes(show_slug):

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
        print(f"Could not fetch show ID for slug: {show_slug}")
        return None, None

    # Use the /history/shows/show_id endpoint to get the last watched episode
    url = f"https://api.trakt.tv/sync/history/shows/{show_id}?limit=1&extended=full"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    history = response.json()

    if not history:
        print(f"No watched history found for show: {show_slug}")
        # Assume the first two episodes are the next to watch
        next_episodes = []
        for season in range(1, 3):
            for episode in range(1, 3):
                url = f"https://api.trakt.tv/shows/{show_slug}/seasons/{season}/episodes/{episode}"
                response = requests.get(url, headers=HEADERS)
                if response.status_code == 200:
                    episode_data = response.json()
                    next_episodes.append({
                        "season": season,
                        "number": episode,
                        "title": episode_data.get("title", "Title not available"),
                        "id": episode_data.get("ids", {}).get("trakt"),
                    })
                    if len(next_episodes) == 2:
                        break
            if len(next_episodes) == 2:
                break

        if next_episodes:
            print("Next 2 unwatched episodes:")
            for ep in next_episodes:
                print(f"S{ep['season']:02}E{ep['number']:02} - {ep['title']}")
        else:
            print("No unwatched episodes found.")

        return None, next_episodes

    last_watched_episode = history[0].get("episode", {})
    last_watched_season = last_watched_episode.get("season")
    last_watched_number = last_watched_episode.get("number")

    if not last_watched_season or not last_watched_number:
        print("Could not determine the last watched episode.")
        return None, []

    print(f"Last watched episode: S{last_watched_season:02}E{last_watched_number:02} - {last_watched_episode.get('title', 'Title not available')}")

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
            next_episodes.append({
                "season": last_watched_season,
                "number": last_watched_number,
                "title": episode_data.get("title", "Title not available"),
                "id": episode_data.get("ids", {}).get("trakt"),
            })

    if next_episodes:
        print("Next 2 unwatched episodes:")
        for ep in next_episodes:
            print(f"S{ep['season']:02}E{ep['number']:02} - {ep['title']}")
    else:
        print("No unwatched episodes found.")

    return last_watched_episode, next_episodes


# Search NZBGeek for a query
def search_nzbgeek(normalized_query):
    print(f"\nSearching for (Normalized): {normalized_query}")
    url = f"https://api.nzbgeek.info/api?t=search&q={normalized_query}&apikey={NZBGEEK_API_KEY}"
    response = requests.get(url)
    response.raise_for_status()
    return response.text

# Parse NZBGeek XML results
def parse_nzbgeek_results(xml_data):
    root = ET.fromstring(xml_data)
    items = root.findall("./channel/item")
    results = []
    for item in items[:MAX_RESULTS]:
        results.append({
            "title": item.find("title").text,
            "nzb_url": item.find("link").text,
        })
    return results

# Send NZB to NZBGet
def send_to_nzbget(nzb_name, nzb_content):
    headers = {"Content-Type": "application/json"}
    payload = {
        "method": "append",
        "params": [
            nzb_name,  # NZBFilename
            base64.b64encode(nzb_content).decode("utf-8"),  # NZBContent (Base64 encoded)
            "Series",  # NZBGet category
            0,  # Priority
            False,  # Add to top
            False,  # Add paused
            "",  # DupeKey
            0,  # DupeScore
            "SCORE",  # DupeMode
            [],  # Post-process parameters
        ],
    }

    response = requests.post(
        NZBGET_URL, json=payload, auth=(NZBGET_USERNAME, NZBGET_PASSWORD), headers=headers
    )
    response.raise_for_status()
    result = response.json()
    if result.get("result"):
        print(f"Successfully sent '{nzb_name}' to NZBGet.")
    else:
        print(f"Failed to send '{nzb_name}' to NZBGet: {result.get('error', 'Unknown error')}")

# Fetch shows in the user's Trakt collection
def get_shows_in_collection():
    url = f"https://api.trakt.tv/users/me/collection/shows"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    shows = get_shows_in_collection()

    for show in shows:
        show_name = show["show"]["title"]
        release_year = show["show"].get("year", "")
        show_slug = show["show"]["ids"]["slug"]

        print(f"\nProcessing show: {show_name}")
        last_watched, next_episodes = get_last_watched_and_next_episodes(show_slug)

        if next_episodes:
            for next_ep in next_episodes:
                season = f"S{next_ep['season']:02}"
                episode = f"E{next_ep['number']:02}"

                for resolution in RESOLUTIONS:
                    # Query with release year
                    normalized_query = f"{normalize_name(show_name)} {season}{episode} {resolution}"
                    results = parse_nzbgeek_results(search_nzbgeek(normalized_query))

                    valid_found = False
                    for nzb_data in results:
                        nzb_title = nzb_data["title"]
                        print(f"Full NZB Name: {nzb_title}")
                        if is_valid_nzb(show_name, nzb_title):
                            print(f"Valid NZB found: {nzb_title}")
                            nzb_content = requests.get(nzb_data["nzb_url"]).content
                            # send_to_nzbget(nzb_title + ".nzb", nzb_content)
                            valid_found = True
                            break

                    if valid_found:
                        break
