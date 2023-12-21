import os
import unicodedata
from src import conf


class FileIndex:

    def __init__(self, folders):
        self.folders = folders
        self.file_map = {}
        self.folder_map = {}
        if folders:
            for folder in folders:
                for i in os.listdir(folder):
                    if not conf.is_audio_file(i) or os.path.isdir(os.path.join(folder, i)):
                        continue
                    key = i[:i.rindex('.')]
                    key_norm = unicodedata.normalize('NFC', key)
                    if key in self.file_map or key_norm in self.file_map:
                        print('WARNING: track', key, 'has multiple instances in spotify local files')
                    self.file_map[key] = i
                    self.file_map[key_norm] = i
                    self.folder_map[key] = folder
                    self.folder_map[key_norm] = folder
        self.folders_index = {x: i for i, x in enumerate(folders)}

    def which_folder(self, filename):
        if filename not in self.folder_map:
            return None
        return self.folders_index[self.folder_map[filename]]
    
