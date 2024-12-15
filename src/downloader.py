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
        self.nzbgeek_api_key = settings['NZBGEEK_API_KEY']
        self.resolutions = settings['RESOLUTIONS']
        self.max_results = 50

    def search_nzbgeek(self, normalized_query):
        """Search NZBGeek for a query"""
        print(f"\nSearching for (Normalized): {normalized_query}")
        url = f"https://api.nzbgeek.info/api?t=search&q={normalized_query}&apikey={self.nzbgeek_api_key}"
        response = requests.get(url)
        response.raise_for_status()
        return response.text

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
        payload = {
            "method": "append",
            "params": [
                nzb_name,  # NZBFilename
                base64.b64encode(nzb_content).decode("utf-8"),  # NZBContent
                "Series",  # Category
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
        results = self.parse_nzbgeek_results(self.search_nzbgeek(normalized_query))

        for nzb_data in results:
            nzb_title = nzb_data["title"]
            similar, _ = is_similar(normalize_name(show_name), 
                                  normalize_name(nzb_title.split('.S')[0]))
            
            if similar:
                print(f"Found matching release: {nzb_title}")
                nzb_content = requests.get(nzb_data["nzb_url"]).content
                if self.send_to_nzbget(nzb_title + ".nzb", nzb_content):
                    return True
        
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
            
            for resolution in self.resolutions:
                if self.find_and_download_episode(show_name, season, episode, resolution):
                    break

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
