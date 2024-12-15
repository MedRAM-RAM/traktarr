import os
import re
import requests
import base64
import xml.etree.ElementTree as ET
from config import settings
from utils import (
    normalize_name, is_similar, get_shows_in_collection,
    get_last_watched_and_next_episodes
)

class ShowDownloader:
    def __init__(self):
        self.nzbget_url = settings['NZBGET_URL']
        self.nzbget_username = settings['NZBGET_USERNAME']
        self.nzbget_password = settings['NZBGET_PASSWORD']
        self.indexers = [idx for idx in settings['INDEXERS'] 
                        if idx['enabled'] and idx['api_key']]
        self.indexers.sort(key=lambda x: x.get('priority', 999))
        self.resolutions = settings['RESOLUTIONS']
        self.max_results = 50

    def _normalize_nzbget_name(self, name):
        """
        Special normalization for NZBGet names that preserves episode numbers
        while making comparison reliable
        """
        # Remove file extension if present
        if name.endswith('.nzb'):
            name = name[:-4]
        
        # Convert to lowercase
        name = name.lower()
        
        # Replace dots with spaces but preserve episode numbers
        name = re.sub(r'\.(?!(S\d{2}E\d{2}))', ' ', name)
        
        # Remove any duplicate spaces
        name = re.sub(r'\s+', ' ', name)
        
        return name.strip()
    
    def _get_nzbget_active_downloads(self):
        """
        Get list of active downloads from NZBGet with parsed show info
        Returns list of dicts with show_name, season, episode
        """
        headers = {"Content-Type": "application/json"}
        payload = {
            "method": "listgroups",
            "params": []
        }

        try:
            response = requests.post(
                self.nzbget_url,
                json=payload,
                auth=(self.nzbget_username, self.nzbget_password),
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("result"):
                return []
                
            active_downloads = []
            print("\nCurrent NZBGet downloads:")
            for group in result["result"]:
                status = group.get("Status", "")
                filename = group.get("NZBName", "")
                
                print(f"Found in NZBGet - Name: {filename}, Status: {status}")
                
                # Skip if definitely done or failed
                if status in ["DELETED", "FAILED"]:
                    continue

                # Use the same pattern matching logic used elsewhere
                match = re.search(r"(.+?)\.S(\d{2})E(\d{2})", filename)
                if match:
                    show_name, season, episode = match.groups()
                    show_name = show_name.replace(".", " ").strip()
                    active_downloads.append({
                        'show_name': show_name,
                        'season': int(season),
                        'episode': int(episode),
                        'full_name': filename
                    })
                    print(f"Extracted: Show='{show_name}', S{season}E{episode}")
            
            return active_downloads
            
        except Exception as e:
            print(f"Error getting NZBGet downloads: {e}")
            return []

    def _episode_exists(self, show_name, season, episode):
        """
        Check if episode already exists in organized folder, unorganized folder,
        or is being downloaded
        """
        print(f"\nChecking if episode exists: {show_name} S{season:02}E{episode:02}")
        
        # Check NZBGet active downloads first
        print("Checking NZBGet active downloads")
        active_downloads = self._get_nzbget_active_downloads()
        for download in active_downloads:
            if (download['season'] == season and 
                download['episode'] == episode and 
                is_similar(normalize_name(show_name), 
                         normalize_name(download['show_name']))[0]):
                print(f"Episode is being downloaded: {download['full_name']}")
                return True
                    
        # Check organized TV Shows folder
        organized_path = settings['MEDIA_LIBRARY_TV_SHOWS_PATH']
        print(f"Checking organized folder: {organized_path}")
        
        # First, try to find the show folder
        show_pattern = f"{show_name}"
        if "(" in show_name:  # Handle shows with year
            show_pattern = show_name.split(" (")[0]
            
        for show_dir in os.listdir(organized_path):
            if show_pattern in show_dir:
                show_path = os.path.join(organized_path, show_dir)
                if os.path.isdir(show_path):
                    season_path = os.path.join(show_path, f"Season {season:02}")
                    if os.path.exists(season_path):
                        for file in os.listdir(season_path):
                            if not file.endswith((".mkv", ".mp4", ".avi")):
                                continue
                            
                            # Extract episode number
                            ep_match = re.search(rf"S{season:02}E{episode:02}", file)
                            if ep_match:
                                print(f"Episode found in organized folder: {file}")
                                return True

        # Check unorganized TV Shows folder
        unorganized_path = settings['UNORGANIZED_TV_SHOWS_PATH']
        print(f"Checking unorganized folder: {unorganized_path}")
        for item in os.listdir(unorganized_path):
            full_path = os.path.join(unorganized_path, item)
            if os.path.isdir(full_path):
                # Extract show name and episode info from folder name
                match = re.search(rf"S{season:02}E{episode:02}", item)
                if match and normalize_name(show_pattern) in normalize_name(item):
                    print(f"Episode found in unorganized folder: {item}")
                    return True

        print(f"Episode not found: {show_name} S{season:02}E{episode:02}")
        return False

    def process_show(self, show):
        """Process a single show"""
        show_name = show["show"]["title"]
        show_slug = show["show"]["ids"]["slug"]

        print(f"\nProcessing show: {show_name}")
        _, next_episodes = get_last_watched_and_next_episodes(show_slug)

        if not next_episodes:
            print("No episodes to download")
            return

        for next_ep in next_episodes:
            season = next_ep["season"]
            episode = next_ep["number"]
            
            # Check if episode already exists or is being downloaded
            if self._episode_exists(show_name, season, episode):
                print(f"Skipping S{season:02}E{episode:02} - already exists or downloading")
                continue
            
            # Proceed with download if episode doesn't exist
            for resolution in self.resolutions:
                if self.find_and_download_episode(show_name, season, episode, resolution):
                    break

    def search_indexer(self, indexer, normalized_query):
        """Search a single indexer for a query"""
        print(f"\nSearching {indexer['name']} for: {normalized_query}")
        url = f"{indexer['url']}"
        params = {
            't': 'search',
            'q': normalized_query,
            'apikey': indexer['api_key']
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error searching {indexer['name']}: {e}")
            return None

    def parse_nzbgeek_results(self, xml_data):
        """Parse NZBGeek XML results"""
        root = ET.fromstring(xml_data)
        items = root.findall("./channel/item")
        results = []
        for item in items[:self.max_results]:
            results.append({
                "title": item.find("title").text,
                "nzb_url": item.find("link").text,
            })
        return results
    
    def send_to_nzbget(self, nzb_name, nzb_content):
        """Send NZB to NZBGet"""
        headers = {"Content-Type": "application/json"}
        
        # Add timestamp to make DupeKey unique
        import time
        unique_key = f"{nzb_name}_{int(time.time())}"
        
        payload = {
            "method": "append",
            "params": [
                nzb_name,  # NZBFilename
                base64.b64encode(nzb_content).decode("utf-8"),  # NZBContent
                "Series",  # Category
                0,  # Priority
                False,  # Add to top
                False,  # Add paused
                unique_key,  # DupeKey - Now unique for each attempt
                0,  # DupeScore
                "FORCE",  # DupeMode - Changed from "SCORE" to "FORCE"
                [],  # Post-process parameters
            ],
        }

        response = requests.post(
            self.nzbget_url,
            json=payload,
            auth=(self.nzbget_username, self.nzbget_password),
            headers=headers
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("result"):
            print(f"Successfully sent '{nzb_name}' to NZBGet.")
            return True
        else:
            print(f"Failed to send '{nzb_name}' to NZBGet: {result.get('error', 'Unknown error')}")
            return False

    def find_and_download_episode(self, show_name, season, episode, resolution):
        """Search for and download a specific episode"""
        normalized_query = f"{normalize_name(show_name)} S{season:02}E{episode:02} {resolution}"

        # Check active downloads first
        active_downloads = self._get_nzbget_active_downloads()
        for download in active_downloads:
            if (download['season'] == season and 
                download['episode'] == episode and 
                is_similar(normalize_name(show_name), 
                         normalize_name(download['show_name']))[0]):
                print(f"Skipping - episode already downloading: {download['full_name']}")
                return True

        # Try each enabled indexer in priority order
        for indexer in self.indexers:
            print(f"\nTrying indexer: {indexer['name']}")
            xml_data = self.search_indexer(indexer, normalized_query)
            
            if not xml_data:
                continue
                
            results = self.parse_nzbgeek_results(xml_data)  # Can keep same parser as it's standard Newznab XML

            for nzb_data in results:
                nzb_title = nzb_data["title"]
                similar, _ = is_similar(normalize_name(show_name), 
                                      normalize_name(nzb_title.split('.S')[0]))
                
                if similar:
                    print(f"Found matching release on {indexer['name']}: {nzb_title}")
                    try:
                        nzb_content = requests.get(nzb_data["nzb_url"]).content
                        if self.send_to_nzbget(nzb_title + ".nzb", nzb_content):
                            return True
                    except Exception as e:
                        print(f"Error downloading from {indexer['name']}: {e}")
                        continue

        return False

    def run(self):
        """Run the complete download process"""
        print("Starting download process...")
        shows = get_shows_in_collection()
        
        for show in shows:
            self.process_show(show)
        
        print("Download process complete!")


if __name__ == "__main__":
    downloader = ShowDownloader()
    downloader.run()
