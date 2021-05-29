@echo off
echo Command                     Description
echo python spotify_import.py    - download spotify data (step 1, run this first, asks for spotify logins)
echo python youtubify.py         - run playlist converter (step 2)
echo python download.py          - download the converted playlist (step 3, downloads the actual audio files)
echo python metadata.py          - insert metadata into the newly downloaded files (step 4, optional)
echo python playlist_export.py   - make playlist files for a music player (step 5, optional)
