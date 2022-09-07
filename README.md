# Youtubify

Youtubify is a bundle of scripts allowing to download and organize the songs you have in your playlists on Spotify from Youtube onto your computer saving you approximately 7$ per month. Features:

- intelligent AI that verifies Youtube links before downloading
- semi-automatic visual verification of Youtube links with browser popups
- selection of playlists to be downloaded
- creation of mashup playlists of already downloaded songs
- automatic `idv3` tagging through `ffmpeg`
- scalable design - out of 2000 songs only a hundred need manual verification

## Prerequisites

To run this bundle of scripts you need to:

1. clone this repository with `git clone git@github.com:Henri-Laiho/youtubify.git`
2. ensure you have python3 installed and in use with `sudo apt install python3`. You can verify your version with `python --version` or `python3 --version`. You can verify which executable of Python is used with `which python` or `which python3`
3. ensure you have ffmpeg installed and in use with `sudo apt install ffmpeg`
4. ensure you have installed every python package in `requirements.txt` with `pip3 install -r requirements.txt` command in the repository root directory.
5. have enough disk space for the songs to be downloaded

## Usage

You can review all steps to download music with `cat fast_youtubify.bat`:

1. `python spotify_import.py` saves data about your playlists on your local computer
2. `python youtubify.py -c` gets Youtube links and saves them on your computer
3. `python youtubify.py -R` allows you to select and correct suspicious Youtube links to be downloaded with a CLI UI
4. `python download.py` downloads all music you selected
5. `python metadata.py` adds idv3 metadata with `ffmpeg`
6. `python playlist_export.py` creates playlist files readable by most conventional players

In all cases `python youtubify.py --help` can answer most questions. 

## Contribution

Ping @henri-laiho.

## Disclaimer

This is for education or personal use purposes only.

