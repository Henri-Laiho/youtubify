import os


ytdl_extensions = ['.opus', '.m4a', '.mp3']


def is_file_on_disk(filename, directory):
   return get_file_extension_if_exists(filename, directory) is not None


def get_file_extension_if_exists(filename, directory):
    for extension in ytdl_extensions:
        if os.path.isfile(os.path.join(directory, filename + extension)): return extension
    return None


def get_filename_ext(filename, dir):
    for ext in ytdl_extensions:
        if os.path.isfile(os.path.join(dir, filename + ext)):
            return filename + ext
    return None


def ensure_dir(directory):
    if not os.path.isdir(directory):
        os.makedirs(directory)
