python -m pip install --upgrade -r requirements.txt
python spotify_import.py --liked_fuzzy
python sync_with_others.py
python youtubify.py convert
python youtubify.py review
python download.py
python metadata.py
python playlist_export.py
