# Traktarr

A lightweight, Trakt-based media automation solution designed to run on Android through Termux. Think of it as a minimalist alternative to Sonarr/Radarr that works directly with your Trakt.tv collection.

## Features

- 🤖 Automated TV show downloading based on Trakt collection
- 📱 Runs natively on Android through Termux
- 📺 Integrates with NZBGet for downloading
- 🎯 Smart episode tracking using Trakt watch history
- 📂 Automatic media organization for Emby server

## Prerequisites

- Android device
- [Termux](https://f-droid.org/packages/com.termux/) (install from F-Droid, not Play Store)
- [NZBGet for Android](https://play.google.com/store/apps/details?id=com.greatlancergames.nzbget)
- [Emby Server for Android](https://play.google.com/store/apps/details?id=mediabrowser.server.android)
- Trakt.tv account
- NZBGeek account

## Android Media Server Setup

1. Install Emby Server:
   - Install from website
   - Launch and follow initial setup
   - Add your media folders (e.g., /storage/emulated/0/TV Shows)
   - Create admin account
   - Configure remote access if needed

2. Install and Configure NZBGet:
   - Install in Termux
   - Launch and note the web interface port (default: 6789)
   - Access web interface at http://localhost:6789
   - Default login: nzbget/tegbzn6789
   - Configure news server settings
   - Set download path (e.g., /storage/emulated/0/TV Shows - Unorganized)

## Traktarr Installation

1. Install Termux from Play Store

2. Install required packages in Termux:
    pkg update
    pkg install python git

3. Clone the repository:
    git clone https://github.com/bluelight773/traktarr.git
    cd traktarr

4. Install Python requirements:
    pip install -r requirements.txt

## Configuration

1. Set up configuration files:
    cp settings.default.yaml settings.local.yaml

2. Edit settings.local.yaml with your personal settings:
   - Do NOT modify settings.default.yaml directly
   - settings.default.yaml will be overwritten by updates

3. Required settings to configure:

   - TRAKT_CLIENT_ID: Get from trakt.tv/oauth/applications
     - Create new application
     - Set name (e.g., "Traktarr")
     - Set redirect URI to http://localhost
     
   - TRAKT_ACCESS_TOKEN: Generate using Trakt OAuth
     - Use the provided client ID
     - Follow Trakt OAuth documentation
     
   - NZBGEEK_API_KEY: Get from nzbgeek.info
     - Found in account settings

4. Configure paths in settings.local.yaml:
   - UNORGANIZED_TV_SHOWS_PATH: Where NZBGet downloads files
   - MEDIA_LIBRARY_TV_SHOWS_PATH: Where Emby looks for media

## Usage

### Manual Run

Run these commands in Termux:

    python src/downloader.py  # Check and download new episodes
    python src/organizer.py   # Organize downloaded files

### Automated Setup with Cron in Termux

1. Install cronie in Termux:
    pkg install cronie

2. Start the cron daemon:
    crond

3. Edit crontab:
    crontab -e

4. Add these lines:
   ```
   # Check for new episodes every 4 hours
   0 */4 * * * cd ~/traktarr && python src/downloader.py
   # Organize files every hour
   0 * * * * cd ~/traktarr && python src/organizer.py
   ```

## How It Works

1. downloader.py:
   - Checks your Trakt collection
   - Finds unwatched episodes
   - Searches NZBGeek for matching releases
   - Sends downloads to NZBGet

2. organizer.py:
   - Monitors download directory
   - Organizes completed downloads
   - Moves files to correct show/season folders
   - Names files according to Emby conventions

## Roadmap

- [ ] Movie support
- [ ] Torrent support via Transmission
- [ ] Quality control options
- [ ] Multiple indexer support
- [ ] Web interface

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
