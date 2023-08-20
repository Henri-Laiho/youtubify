import os
import re
import time
import json
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import google.oauth2.credentials

from conf.conf_private import data_folder
from src.persistance.storage import Storage

REQUESTS_PER_MINUTE = 10
DAILY_LIMIT = 9500  # Setting it slightly below 10,000 to be safe
DELAY_BETWEEN_REQUESTS = 60 / REQUESTS_PER_MINUTE
YOUTUBE_PLAYLIST_SIZE_LIMIT = 200


def is_daily_youtube_quota_reached():
    if Storage.get_youtube_daily_request_count() >= DAILY_LIMIT:
        print("Reached Youtube API daily limit!")
        return True
    return False


def extract_video_id(url):
    # Regular expressions for different YouTube URL formats
    patterns = [
        r"(?<=v=)[^&#]+",  # Standard format
        r"(?<=be/)[^&#]+",  # Shortened format
        r"(?<=embed/)[^&#]+",  # Embedded format
    ]
    for pattern in patterns:
        video_id = re.search(pattern, url)
        if video_id:
            return video_id.group(0)
    return None


def get_authenticated_service():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = os.path.join(data_folder, "client_secret.json")
    token_file = os.path.join(data_folder, "youtube_token.json")

    credentials = None

    # Check if token file exists and load it
    if os.path.exists(token_file):
        with open(token_file, 'r') as token_file:
            token_data = json.load(token_file)
            credentials = google.oauth2.credentials.Credentials(**token_data)

    # If there are no valid credentials available, prompt the user to log in.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(google.auth.transport.requests.Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, [
                "https://www.googleapis.com/auth/youtube.force-ssl"])
            credentials = flow.run_local_server(port=8080)

        # Save the credentials for the next run
        with open(token_file, 'w') as token_file:
            token_file.write(json.dumps({
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }))

    youtube = googleapiclient.discovery.build(api_service_name, api_version, credentials=credentials)
    return youtube


def get_current_playlist_videos(youtube, playlist_id):
    # Fetch videos from the YouTube playlist
    current_videos = []
    page_token = None
    while True:
        response = youtube.playlistItems().list(playlistId=playlist_id, part="contentDetails", pageToken=page_token).execute()
        current_videos.extend([item['contentDetails']['videoId'] for item in response['items']])
        page_token = response.get('nextPageToken')
        if not page_token:
            break
    return current_videos


def update_playlist(youtube, playlist_name, video_links, playlists=None):
    if playlists is None:
        playlists = get_youtube_playlists(youtube)

    # Check if a playlist with the given name already exists
    playlist_id = None
    for item in playlists['items']:
        if item['snippet']['title'] == playlist_name:
            playlist_id = item['id']
            break

    # If the playlist doesn't exist, create a new one
    if not playlist_id:
        if is_daily_youtube_quota_reached():
            return
        playlist_response = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": playlist_name,
                    "description": "A playlist imported from Spotify",
                },
                "status": {
                    "privacyStatus": "private"
                }
            }
        ).execute()
        playlist_id = playlist_response['id']

    # Get current videos in the playlist
    current_video_ids = get_current_playlist_videos(youtube, playlist_id)
    new_video_ids = [extract_video_id(link) for link in video_links]

    # Identify videos to add and remove
    videos_to_add = set(new_video_ids) - set(current_video_ids)
    videos_to_remove = set(current_video_ids) - set(new_video_ids)

    # Remove old videos
    for i, video_id in enumerate(videos_to_remove):
        print('Adding tracks: %s/%s\r' % (i + 1, len(videos_to_remove)))
        if is_daily_youtube_quota_reached():
            return
        # Retrieve playlistItem id for the video to remove
        playlist_item_id = next((item['id'] for item in youtube.playlistItems().list(playlistId=playlist_id, part="id,contentDetails", videoId=video_id).execute()['items']), None)
        if playlist_item_id:
            youtube.playlistItems().delete(id=playlist_item_id).execute()
            Storage.add_youtube_daily_request()
            time.sleep(DELAY_BETWEEN_REQUESTS)

    free_space = YOUTUBE_PLAYLIST_SIZE_LIMIT - len(current_video_ids) + len(videos_to_remove)

    # Add new videos
    for i, video_id in enumerate(videos_to_add):
        print('Adding tracks: %s/%s\r' % (i + 1, len(videos_to_add)))

        if i >= free_space:
            print(f"Playlist '{playlist_name}' has reached size limit {YOUTUBE_PLAYLIST_SIZE_LIMIT}!")
            return
        if is_daily_youtube_quota_reached():
            return
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        ).execute()
        Storage.add_youtube_daily_request()
        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"Playlist '{playlist_name}' updated successfully!")


def get_youtube_playlists(youtube):
    return youtube.playlists().list(part="id,snippet", mine=True).execute()


if __name__ == '__main__':
    youtube = get_authenticated_service()
    playlist_name = input("Enter the name of the playlist: ")
    video_links = input("Enter YouTube video links separated by commas: ").split(',')
    update_playlist(youtube, playlist_name, video_links)
