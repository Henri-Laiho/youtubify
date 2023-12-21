python3 -m pip install --upgrade -r requirements.txt
python3 spotify_import.py --liked_fuzzy
python3 sync_with_others.py
python3 youtubify.py convert
python3 youtubify.py review
python3 download.py
python3 youtubify.py flacify
python3 metadata.py -pi 30
python3 metadata.py -fc
python3 playlist_export.py
