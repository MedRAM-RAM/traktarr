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
- Trakt.tv account
- NZBGeek account

## Android Media Server Setup

1. Install and configure Emby Server:
   - Install from [website](https://emby.media/server-android.html)
   - Launch and follow initial setup
   - Add your media folders (e.g., /storage/emulated/0/TV Shows)
   - Do not check `Save artwork into media folders`
   - Create user account

2. Install Termux from [Play Store](https://play.google.com/store/apps/details?id=com.termux)
   
3. Install and Configure NZBGet:
   - Install via Termux: `pkg install nzbget`
   - Run via Termux: `nzbget -D`
   - Access web interface at http://localhost:6789
   - Configure news server settings
   - Configure categories, particularly the path for Series (e.g., `/storage/emulated/0/TV Shows - Unorganized`)

## Traktarr Installation

1. Install required packages in Termux:
   ```sh
   pkg update
   pkg install python git
   ```

3. Clone the repository:
   ```sh
   git clone https://github.com/bluelight773/traktarr.git
   cd traktarr
   ```

4. Install Python requirements:
   ```sh
   pip install -r requirements.txt
   ```

## Configuration

1. Set up configuration files:
   ```sh
   cp settings.default.yaml settings.local.yaml
   ```

3. Edit settings.local.yaml with your personal settings:
   - Do NOT modify settings.default.yaml directly
   - `settings.default.yaml` will be overwritten by updates

4. Required settings to configure:

   - `TRAKT_CLIENT_ID` and `TRAKT_CLIENT_SECRET`:
     - Go to https://trakt.tv/oauth/applications
     - Click New Application
     - Set name to `Traktarr` followed by some number so that it's available.
     - Set description to `A lightweight, Trakt-based media automation solution designed to run on Android through Termux.`
     - Set Redirect:uri to `urn:ietf:wg:oauth:2.0:oob`
     - Leave everything else as is
     - Click Save App
     - You should see the values to use for `TRAKT_CLIENT_ID` and `TRAKT_CLIENT_SECRET`
     
   - `TRAKT_ACCESS_TOKEN`:
     - `cd` to `traktarr/src` directory in Termux: `cd traktarr/src`
     - Run `python trakt_authorizer.py`
     - Follow instructions to obtain the value for `TRAKT_ACCESS_TOKEN`
     
   - `NZBGEEK_API_KEY`: Get from [nzbgeek.info](https://nzbgeek.info/) > My Account
       
   - `UNORGANIZED_TV_SHOWS_PATH`: Where NZBGet downloads files categories as Series
     
   - `MEDIA_LIBRARY_TV_SHOWS_PATH`: Where Emby looks for TV show media

## Usage

### Manual Run

Run these commands in Termux given you are within the `traktarr` directory:

    python src/downloader.py  # Check and download new episodes
    python src/organizer.py   # Organize downloaded files

### Automated Setup with Cron in Termux

1. Install `cronie` in Termux:
   ```sh
   pkg install cronie
   ```

3. Start the cron daemon:
   crond

4. Edit crontab:
   ```sh
   crontab -e
   ```

6. Add these lines to make `downloader.py` run every hour at the top of the hour and to make `organizer.py` run every hour at the 30-minute mark:
   ```
   0 * * * * /data/data/com.termux/files/usr/bin/python3 /data/data/com.termux/files/home/traktarr/src/downloader.py >> /data/data/com.termux/files/home/downloader.log 2>&1
   30 * * * * /data/data/com.termux/files/usr/bin/python3 /data/data/com.termux/files/home/traktarr/src/organizer.py >> /data/data/com.termux/files/home/organizer.log 2>&1
   ```

## How It Works

1. downloader.py:
   - Checks your Trakt collection
   - Finds the next 2 unwatched episodes relative to your last watched episode
   - Searches NZBGeek for matching releases
   - Sends download to NZBGet

2. organizer.py:
   - Monitors download directory
   - Organizes completed downloads
   - Moves files to correct show/season folders
   - Names files according to Emby conventions

## Potential future features

- [ ] Movie support
- [ ] Torrent support via Transmission
- [ ] Quality control options
- [ ] Multiple indexer support
- [ ] Web interface

## Contributing

Contributions and forks are welcome!

## License

This project is licensed under the MIT License - see the LICENSE file for details.
