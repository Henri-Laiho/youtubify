import json
import logging
import os
from queue import Queue
import threading
import time
import colorama

import youtube_dl

from src import conf
from src.persistance.track_data import Storage
from src.ytdownload import YtDownload

ISRC_MAP = '_isrc_map'
YT = 'yt'
ISRC = 'isrc'
ARTISTS = 'artists'
NAME = 'name'
FILENAME = 'filename'
download_version = 1


colors = [
    colorama.Fore.LIGHTBLACK_EX,
    colorama.Fore.LIGHTGREEN_EX,
    colorama.Fore.LIGHTBLUE_EX,
    colorama.Fore.LIGHTMAGENTA_EX,
    colorama.Fore.LIGHTYELLOW_EX,
    colorama.Fore.CYAN,
    colorama.Fore.GREEN,
    colorama.Fore.WHITE,
    colorama.Fore.YELLOW,
    colorama.Fore.MAGENTA,
    colorama.Fore.BLUE,
]


class DlThread(threading.Thread):
    def __init__(self, threadID, name, q, queueLock, checkExit, update_status_callback):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q
        self.queueLock = queueLock
        self.checkExit = checkExit
        self.log = logging.Logger(name, level=logging.INFO)
        console = logging.StreamHandler()
        color = colors[threadID % len(colors)]
        console.setFormatter(logging.Formatter(fmt=color+f"[%(levelname)s] {name} - %(message)s"+colorama.Fore.RESET))
        self.log.addHandler(console)
        self.downloader = YtDownload(outDir=conf.downloaded_audio_folder, logger=self.log, update_status_callback=lambda data: update_status_callback(threadID, data))
        self.errors = 0

    def run(self):
        logging.info("Starting " + self.name)
        self.process_data(self.q)
        logging.info("Exiting " + self.name)

    def process_data(self, q):
        while not self.checkExit():
            self.queueLock.acquire()
            if not q.empty():
                track = q.get()
                size = q.qsize()
                self.queueLock.release()
                if FILENAME not in track or YT not in track:
                    logging.warning("%s, track missing: %s" % (self.name, track[ISRC]))
                else:
                    yt = track[YT]
                    isrc = track[ISRC]
                    filename = track[FILENAME]
                    logging.info("%s processing %s (%s)" % (self.name, filename, yt))
                    try:
                        self.downloader.download(yt, filename=filename)
                        Storage.isrc_local_downloaded_status[isrc] = download_version
                    except youtube_dl.utils.DownloadError as err:
                        logging.error("%s Download Error, resetting track %s - %s:" % (self.name, filename, yt) + str(err))
                        Storage.reset_track(track[ISRC], force=True)
                        self.errors += 1
                        if self.errors > conf.Flags.max_download_errors:
                            logging.critical("Maximum number if errors reached, %s exiting" % self.name)
                            break

            else:
                self.queueLock.release()
            time.sleep(0.01)


def load_spotify_playlists(file):
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
        if isrc in Storage.isrc_to_track_data:
            track[FILENAME] = Storage.isrc_to_track_data[isrc]['filename']
        else:
            track[FILENAME] = get_nice_path(name, artists)
            print('Warning: using old filename: %s' % track[FILENAME])


cursor_up = lambda lines: '\x1b[{0}A'.format(lines)
cursor_down = lambda lines: '\x1b[{0}B'.format(lines)

def download_playlist(tracks, num_threads=1):
    exitFlag = 0
    threadList = ["Thread-" + str(i + 1) for i in range(num_threads)]
    queueLock = threading.Lock()
    workQueue = Queue()
    threads = []
    threadID = 1
    thread_status_lock = threading.Lock()
    last_status = {'print_time' : 0}
    thread_statuses = {-1 : {'_eta_str': '0s', '_percent_str': '  0.0%', '_speed_str': '  0B/s', '_total_bytes_str': '0B', 'filename': '', 'status': ''}}
    
    def checkExit():
        return exitFlag

    def print_statuses():
        queueLock.acquire()
        lines = ['Downloading: (+%d more in queue)' % workQueue.qsize()]
        queueLock.release()
        for id, d in thread_statuses.items():
            if d['status'] == 'downloading':
                fname = d['filename'][len(conf.downloaded_audio_folder):]
                lines.append('%d. %s / %s @ %s, ETA %s %s, ' % (id, d['_percent_str'], d['_total_bytes_str'], d['_speed_str'], d['_eta_str'], fname[:60]))
        lines.append('Total download speed: %.2fKiB/s\r' % (sum([thread_statuses[x+1]['speed'] for x in range(num_threads) if 'speed' in thread_statuses[x+1]])/1024))
        print('\n'.join(lines))
        print('\r', end='')
        print(cursor_up(len(lines)), end='')

    def update_status(id, data):
        thread_status_lock.acquire()
        thread_statuses[id] = data
        t = time.time_ns()
        if t-last_status['print_time'] > 10e8:
            last_status['print_time'] = t
            print_statuses()
        thread_status_lock.release()

    # Create new threads
    for tName in threadList:
        thread = DlThread(threadID, tName, workQueue, queueLock, checkExit, update_status)
        thread.start()
        threads.append(thread)
        thread_statuses[threadID] = thread_statuses[-1]
        threadID += 1
    del thread_statuses[-1]


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
