import json
import os
from queue import Queue
import threading
import time

from src import conf
from src.ytdownload import YtDownload

ISRC_MAP = '_isrc_map'
YT = 'yt'
ISRC = 'isrc'
ARTISTS = 'artists'
NAME = 'name'
FILENAME = 'filename'
playlists_file = os.path.join("spotify", "playlists.json")

encoder = '@'
path_encoding = {
    '\\': encoder + '5C',
    '/': encoder + '2F',
    ':': encoder + '3A',
    '*': encoder + '2A',
    '?': encoder + '3F',
    '"': encoder + '22',
    '<': encoder + '3C',
    '>': encoder + '3E',
    '|': encoder + '7C',
    '%': encoder + '25'
}

nice_path_encoding = {
    '\\': '',
    '/': '',
    ':': '',
    '*': '',
    '?': '',
    '"': '\'',
    '<': '',
    '>': '',
    '|': '',
    '%': '',
}


class DlThread(threading.Thread):
    def __init__(self, threadID, name, q, queueLock, checkExit):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q
        self.queueLock = queueLock
        self.checkExit = checkExit
        self.downloader = YtDownload(outDir=conf.downloaded_audio_folder)

    def run(self):
        print("Starting " + self.name)
        self.process_data(self.q)
        print("Exiting " + self.name)

    def process_data(self, q):
        while not self.checkExit():
            self.queueLock.acquire()
            if not q.empty():
                track = q.get()
                size = q.qsize()
                self.queueLock.release()
                if FILENAME not in track or YT not in track:
                    print("%s, track missing: %s" % (self.name, track[ISRC]))
                yt = track[YT]
                filename = track[FILENAME]
                print("%s processing %s, about %d remaining (%s)" % (self.name, filename, size, yt))
                self.downloader.download(yt, filename=filename)
            else:
                self.queueLock.release()
            time.sleep(0.01)


def path_encode(path, encoding):
    for key in encoding:
        path = path.replace(key, encoding[key])
    return path


def get_raw_path(name, artists):
    return path_encode(', '.join(['%s' % artist for artist in artists]) + ' - %s' % name, path_encoding)


def get_nice_path(name, artists):
    if len(artists) > 0 and artists[0]:

        return path_encode(artists[0] + ' - ' + name, nice_path_encoding)
    else:
        return path_encode(name, nice_path_encoding)


def load_spotify_playlists(file=playlists_file):
    f = open(file, "r")
    data = json.loads(f.read())
    for playlist in data:
        isrc_map = {}
        for track in playlist['tracks']:
            if track['track']['is_local']:
                continue
            isrc = track['track']['external_ids']['isrc']
            isrc_map[isrc] = track
        playlist[ISRC_MAP] = isrc_map
    return data


def pick_spotify_playlist(data, idx=None):
    if idx is None:
        for i, playlist in enumerate(data):
            print(i, playlist['name'])
    else:
        return data[idx]


def init_yt_isrc_tracks(tracks, playlists):
    for track in tracks:
        isrc = track[ISRC]
        name, artists = None, None
        for playlist in playlists:
            if isrc in playlist[ISRC_MAP]:
                strack = playlist[ISRC_MAP][isrc]
                name = strack['track']['name']
                artists = [y['name'] for y in strack['track']['artists']]
                break
        if name is None or artists is None:
            continue
        track[NAME] = name
        track[ARTISTS] = artists
        track[FILENAME] = get_nice_path(name, artists)


def download_playlist(tracks, num_threads=1):
    exitFlag = 0
    threadList = ["Thread-" + str(i + 1) for i in range(num_threads)]
    queueLock = threading.Lock()
    workQueue = Queue()
    threads = []
    threadID = 1

    def checkExit():
        return exitFlag

    # Create new threads
    for tName in threadList:
        thread = DlThread(threadID, tName, workQueue, queueLock, checkExit)
        thread.start()
        threads.append(thread)
        threadID += 1

    # Fill the queue
    queueLock.acquire()
    for track in tracks:
        workQueue.put(track)
    queueLock.release()

    # Wait for queue to empty
    while not workQueue.empty():
        pass

    # Notify threads it's time to exit
    exitFlag = 1

    # Wait for all threads to complete
    for t in threads:
        t.join()
    print("Exiting Main Thread")
