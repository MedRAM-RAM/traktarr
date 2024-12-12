import os
import shutil
import re
from config import settings

MEDIA_LIBRARY_TV_SHOWS_PATH = settings['MEDIA_LIBRARY_TV_SHOWS_PATH']
UNORGANIZED_TV_SHOWS_PATH = settings['UNORGANIZED_TV_SHOWS_PATH']

# Create the destination path
def construct_path_and_filename(show_name, season, episode, title):
    season_folder = f"Season {int(season[1:]):02}"  # Format season as "Season XX"
    clean_show_name = show_name.replace(":", "").replace("/", "").replace("\\", "")
    dest_dir = os.path.join(MEDIA_LIBRARY_TV_SHOWS_PATH, f"{clean_show_name}", season_folder)
    os.makedirs(dest_dir, exist_ok=True)  # Ensure the destination folder exists

    # Construct final file name (e.g., "Show.Name.S01E01.Title.mkv")
    final_file_name = f"{clean_show_name}.S{season[1:]:02}E{episode}.{title}.mkv"
    return dest_dir, final_file_name

# Function to delete a folder and all its contents using rm -rf
def force_delete_folder(folder_path):
    try:
        # Use the shell command to delete the folder and all its contents
        os.system(f"rm -rf '{folder_path}'")
        print(f"Successfully deleted folder: {folder_path}")
    except Exception as e:
        print(f"Error deleting folder {folder_path}: {e}")

def move_and_rename_files():
    print("Checking for misplaced files in Unorganized...")
    if not os.path.exists(UNORGANIZED_TV_SHOWS_PATH):
        print(f"Error: Unorganized path does not exist: {UNORGANIZED_TV_SHOWS_PATH}")
        return
        
    print(f"Scanning directory: {UNORGANIZED_TV_SHOWS_PATH}")
    for root, dirs, files in os.walk(UNORGANIZED_TV_SHOWS_PATH, topdown=False):
        print(f"Checking directory: {root}")
        print(f"Found files: {files}")
        for file in files:
            if not file.endswith((".mkv", ".mp4", ".avi")):
                print(f"Skipping non-video file: {file}")
                continue

            # Extract show name, season, episode, and title from the **parent folder name**
            parent_folder = os.path.basename(root)
            print(f"Checking parent folder: {parent_folder}")
            match = re.match(r"(.+?)\.S(\d{2})E(\d{2})\.(.+)", parent_folder, re.IGNORECASE)
            if not match:
                print(f"Skipping: {file} (Parent folder '{parent_folder}' doesn't match expected format)")
                continue

            show_name, season, episode, title = match.groups()

            # Construct the correct destination path and file name
            dest_dir, final_file_name = construct_path_and_filename(
                show_name.replace(".", " "), f"S{season}", episode, title
            )
            source_path = os.path.join(root, file)
            dest_path = os.path.join(dest_dir, final_file_name)

            # Move and rename the file
            if source_path != dest_path:
                print(f"Moving: {source_path} -> {dest_path}")
                shutil.move(source_path, dest_path)

        # Delete the folder after processing files, but skip the root UNORGANIZED_TV_SHOWS_PATH
        if root != UNORGANIZED_TV_SHOWS_PATH and os.path.exists(root):
            print(f"Forcefully removing directory and its contents: {root}")
            force_delete_folder(root)

if __name__ == "__main__":
    move_and_rename_files()
