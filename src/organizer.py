import os
import shutil
import re
from config import settings
from utils import (
    normalize_name, is_similar, get_shows_in_collection,
    get_last_watched_and_next_episodes, sanitize_filename
)

class VideoOrganizer:
    def __init__(self):
        self.media_path = settings['MEDIA_LIBRARY_TV_SHOWS_PATH']
        self.unorganized_path = settings['UNORGANIZED_TV_SHOWS_PATH']
        self.shows = get_shows_in_collection()
        self.next_episodes = self._get_all_next_episodes()

    def _get_all_next_episodes(self):
        """Get next episodes for all shows in collection"""
        print("Gathering information about next episodes to watch...")
        episodes = []
        for show in self.shows:
            show_name = show["show"]["title"]
            show_slug = show["show"]["ids"]["slug"]
            print(f"\nProcessing show: {show_name}")
            last_watched, next_eps = get_last_watched_and_next_episodes(show_slug, verbose=True)
            if next_eps:
                for ep in next_eps:
                    episodes.append({
                        "show_name": show_name,
                        "season": ep["season"],
                        "episode": ep["number"],
                        "show_data": show["show"]
                    })
                if last_watched:
                    print("Next episodes to watch:")
                    for ep in next_eps:
                        print(f"S{ep['season']:02}E{ep['number']:02} - {ep['title']}")
        print("\nFinished gathering episode information.")
        return episodes


    def _construct_show_folder_name(self, show_data):
        """Create standardized show folder name with year"""
        name = show_data["title"]
        year = show_data.get("year", "")
        clean_name = sanitize_filename(name)
        if year:
            return f"{clean_name} ({year})"
        return clean_name

    def _parse_episode_info(self, folder_name):
        """Extract show name, season, and episode from folder name"""
        match = re.match(r"(.+?)\.S(\d{2})E(\d{2})\.(.+)", folder_name, re.IGNORECASE)
        if match:
            return match.groups()
        return None

    def organize_unorganized(self):
        """Process files in unorganized folder"""
        if not os.path.exists(self.unorganized_path):
            print(f"Error: Unorganized path does not exist: {self.unorganized_path}")
            return

        print("\nScanning unorganized folders:")
        for root, _, files in os.walk(self.unorganized_path, topdown=False):
            video_files = [f for f in files if f.endswith((".mkv", ".mp4", ".avi"))]
            if not video_files:
                continue

            folder_name = os.path.basename(root)
            print(f"\nProcessing folder: {folder_name}")
            
            # Extract show name and episode info from folder name
            match = re.search(r"(.+?)\.S(\d{2})E(\d{2})", folder_name)
            if not match:
                print(f"Skipping: Could not parse episode information from folder name: {folder_name}")
                if root != self.unorganized_path:
                    print(f"Removing folder with invalid name format: {root}")
                    self._force_delete_folder(root)
                continue

            show_name, season, episode = match.groups()
            season = int(season)
            episode = int(episode)
            
            # Remove year if present for matching purposes
            show_name = re.sub(r"\s*\(\d{4}\)|\.\d{4}", "", show_name)
            show_name = show_name.replace(".", " ").strip()

            print(f"Extracted info - Show: '{show_name}', S{season:02}E{episode:02}")

            # Try to match with next episodes
            episode_match = None
            matched_show = None
            
            for next_ep in self.next_episodes:
                trakt_show_name = next_ep["show_name"]
                # First find matching show using similarity
                similar, similarity = is_similar(normalize_name(show_name), 
                                            normalize_name(trakt_show_name))
                
                if similar and next_ep["season"] == season and next_ep["episode"] == episode:
                    print(f"Found matching episode: {trakt_show_name} S{season:02}E{episode:02}")
                    episode_match = next_ep
                    # Find the full show data from our collection
                    for show in self.shows:
                        if show["show"]["title"] == trakt_show_name:
                            matched_show = show
                            break
                    break

            if not episode_match or not matched_show:
                print(f"No matching upcoming episode found for: {folder_name}")
                if root != self.unorganized_path:
                    print(f"Removing unmatched folder: {root}")
                    self._force_delete_folder(root)
                continue

            # Construct destination path
            show_folder = self._construct_show_folder_name(matched_show["show"])
            season_folder = f"Season {season:02}"
            dest_dir = os.path.join(self.media_path, show_folder, season_folder)
            os.makedirs(dest_dir, exist_ok=True)

            # Move each video file
            for video_file in video_files:
                source_path = os.path.join(root, video_file)
                # Use the folder name as the final filename, but ensure it ends with .mkv
                final_name = folder_name if folder_name.endswith('.mkv') else f"{folder_name}.mkv"
                dest_path = os.path.join(dest_dir, final_name)
                
                print(f"Moving: {source_path} -> {dest_path}")
                shutil.move(source_path, dest_path)

            # Clean up source folder after moving files
            if root != self.unorganized_path:
                self._force_delete_folder(root)

    def cleanup_library(self):
        """Remove files that don't match next episodes"""
        for root, dirs, files in os.walk(self.media_path, topdown=False):
            for file in files:
                if not file.endswith((".mkv", ".mp4", ".avi")):
                    continue

                file_path = os.path.join(root, file)
                if not self._is_needed_episode(file):
                    print(f"Removing unneeded file: {file_path}")
                    os.remove(file_path)

            # Remove empty directories
            if not os.listdir(root) and root != self.media_path:
                self._force_delete_folder(root)

    def _is_needed_episode(self, filename):
        """Check if file matches any next episodes"""
        match = re.search(r"S(\d{2})E(\d{2})", filename)
        if not match:
            return False

        season, episode = map(int, match.groups())
        
        # Extract show name from the filename itself
        show_match = re.match(r"(.*?)\.S\d{2}E\d{2}", os.path.basename(filename))
        if not show_match:
            print(f"Could not extract show name from filename: {filename}")
            return False
            
        show_name = show_match.group(1)
        # Remove year if present
        show_name = re.sub(r"\s*\(\d{4}\)|\.\d{4}", "", show_name)
        # Replace dots with spaces
        show_name = show_name.replace(".", " ").strip()

        print(f"Extracted show: '{show_name}', S{season:02}E{episode:02}")
        
        for next_ep in self.next_episodes:
            trakt_show_name = next_ep["show_name"]
            # Compare normalized names and episode numbers
            if (normalize_name(trakt_show_name) == normalize_name(show_name) and
                next_ep["season"] == season and
                next_ep["episode"] == episode):
                print(f"Found match: {filename} corresponds to {trakt_show_name} S{season:02}E{episode:02}")
                return True
                
        print(f"No match found for: {os.path.basename(filename)}")
        print(f"Looking for matches with show: '{show_name}', S{season:02}E{episode:02}")
        print("Available next episodes:", [f"{ep['show_name']} S{ep['season']:02}E{ep['episode']:02}" 
                                        for ep in self.next_episodes])
        return False

    def _force_delete_folder(self, folder_path):
        """Forcefully remove a folder and all its contents"""
        try:
            # Use rm -rf to force delete folder and all contents
            os.system(f"rm -rf '{folder_path}'")
            print(f"Successfully deleted folder and contents: {folder_path}")
        except Exception as e:
            print(f"Error removing folder {folder_path}: {e}")

    def run(self):
        """Run the complete organization process"""
        print("Starting organization process...")
        print("Processing unorganized files...")
        self.organize_unorganized()
        print("\nCleaning up library...")
        self.cleanup_library()
        print("Organization complete!")


if __name__ == "__main__":
    organizer = VideoOrganizer()
    organizer.run()
