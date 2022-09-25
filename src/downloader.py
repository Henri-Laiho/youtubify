import json
import logging
import os
from queue import Queue
import threading
import time
import colorama

import youtube_dl

from src import conf
from src.persistance.storage import Storage
from src.ytdownload import YtDownload
from src.playlist import Playlist

ISRC_MAP = '_isrc_map'
YT = 'yt'
ISRC = 'isrc'
FILENAME = 'filename'
download_version = 1



class DlThread(threading.Thread):
    def __init__(self, threadID, name, queue : Queue, queueLock, checkExit, update_status_callback, log_handler):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.queue = queue
        self.queueLock = queueLock
        self.checkExit = checkExit
        self.log = logging.Logger(name, level=logging.INFO)
        if log_handler: self.log.addHandler(log_handler)
        self.downloader = YtDownload(outDir=conf.downloaded_audio_folder, logger=self.log, update_status_callback=lambda data: update_status_callback(threadID, data))
        self.errors = 0

    def run(self):
        logging.info("Starting " + self.name)
        self.process_data()
        logging.info("Exiting " + self.name)

    def process_data(self):
        while not self.checkExit():
            self.queueLock.acquire()
            if not self.queue.empty():
                track = self.queue.get()
                size = self.queue.qsize()
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


def load_spotify_playlists(file) -> list:
    with open(file, "r") as f:
        playlists_json = json.loads(f.read())
    playlists = [Playlist.from_json(x) for x in playlists_json]
    return playlists


def pick_spotify_playlist(playlists: list, idx=None) -> Playlist:
    if idx is None:
        for i, playlist in enumerate(playlists):
            print(i, playlist.name)
    else:
        return data[idx]


def init_yt_isrc_tracks(tracks, playlists : list):
    for track in tracks:
        isrc = track[ISRC]
        if isrc in Storage.isrc_to_track_data:
            track[FILENAME] = Storage.isrc_to_track_data[isrc]['filename']
        else:
            # TODO: following logic needs to be redesigned for multi-user-system
            strack = None
            for playlist in playlists:
                if isrc in playlist.isrc_map:
                    strack = playlist.isrc_map[isrc]
                    break
            if strack is None:
                continue
            track[FILENAME] = strack.filename
            print('Warning: using old filename: %s; Make sure you run "youtubify.py -c" before "download.py"' % strack.filename)


cursor_up = lambda lines: '\x1b[{0}A'.format(lines)
cursor_down = lambda lines: '\x1b[{0}B'.format(lines)

def download_playlist(tracks, num_threads=1, log_handler=None):
    exitFlag = 0
    threadList = ["Thread-" + str(i + 1) for i in range(num_threads)]
    queueLock = threading.Lock()
    workQueue = Queue()
    threads = []
    thread_status_lock = threading.Lock()
    last_status = {'print_time' : 0, 'lines' : 0}
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
                lines.append('%d. %s / %s @ %s, ETA %s %-65s' % (id, d['_percent_str'], d['_total_bytes_str'], d['_speed_str'], d['_eta_str'], fname[:60]))
        lines.append('Total download speed: %.2fKiB/s\r' % (sum([thread_statuses[x+1]['speed'] for x in range(num_threads) if 'speed' in thread_statuses[x+1]])/1024))
        if log_handler: log_handler.acquire()
        print('\n'.join(lines))
        print('\r', end='')
        print(cursor_up(len(lines)), end='')
        last_status['lines'] = len(lines)
        if log_handler: log_handler.release()

    def update_status(id, data):
        thread_status_lock.acquire()
        thread_statuses[id] = data
        t = time.time_ns()
        if t-last_status['print_time'] > 10e8:
            last_status['print_time'] = t
            print_statuses()
        thread_status_lock.release()

    # Create new threads
    for threadID, tName in enumerate(threadList):
        thread = DlThread(threadID+1, tName, workQueue, queueLock, checkExit, update_status, log_handler)
        threads.append(thread)
        thread_statuses[threadID+1] = thread_statuses[-1]
        thread.start()
    del thread_statuses[-1]


    # Fill the queue
    queueLock.acquire()
    for track in tracks:
        workQueue.put(track)
    queueLock.release()

    # Wait for queue to empty
    while not workQueue.empty():
        time.sleep(0.1)

    # Notify threads it's time to exit
    exitFlag = 1

    # Wait for all threads to complete
    for t in threads:
        t.join()
    print('\n'*last_status['lines'])
    print("Exiting Main Thread")
