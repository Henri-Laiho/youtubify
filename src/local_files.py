import os

from src import conf
from src.playlist import Playlist
from src.track import LocalTrack
from src.persistance.storage import get_folder_id
from src.persistance.storage import get_folder_data


class LocalFileManager:
    def __init__(self):
        self.folder_ids = {}
        self.folder_names = {}
        for folder in conf.spotify_local_files_folders:
            self.folder_ids[folder] = get_folder_id(folder, 'Initializing local files folder ' + folder + ' with id %s')
            self.folder_names[folder] = get_folder_data(folder, 'name')
        self.id_folders = {self.folder_ids[x]: x for x in self.folder_ids}

    def get_meta_playlists(self):
        playlists = []
        for x in self.folder_ids:
             plist = Playlist()
             plist.id = self.folder_ids[x]
             plist.name = self.folder_names[x]
             playlists.append(plist)
        return playlists

    def get_playlists(self):
        playlists = self.get_meta_playlists()
        for plist in playlists:
            folder = self.id_folders[plist.id]
            tracks = []
            for filename in os.listdir(folder):
                if os.path.isfile(os.path.join(folder, filename)) and conf.is_audio_file(filename):
                    tracks.append(LocalTrack(filename))
            plist.tracks = tracks
        return playlists