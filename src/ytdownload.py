import logging

import youtube_dl
import os

ytdl_extensions = ['.m4a', '.opus']


def get_filename_ext(filename, dir):
    for ext in ytdl_extensions:
        if os.path.isfile(os.path.join(dir, filename + ext)):
            return filename + ext
    return None


def ensure_dir(directory):
    if not os.path.isdir(directory):
        os.makedirs(directory)


class DlLogger(object):
    def debug(self, msg):
        print("[debug]", msg)
        pass

    def warning(self, msg):
        print("[warning]", msg)
        pass

    def error(self, msg):
        print("[error]", msg)


class YtDownload(object):
    def __init__(self, outDir='downloaded'):
        self.outdir = outDir
        self.outtempl = os.path.join(outDir, '%(title)s.%(ext)s')

        ensure_dir(outDir)

        self.ydl_opts = {
            'audio-format': 'best',
            'socket_timeout': 5,
            'retries': 5,
            'logger': DlLogger(),
            'progress_hooks': [self.msg_hook],
            'outtmpl': self.outtempl,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
            }]
        }

    def msg_hook(self, d):
        if d['status'] == 'finished':
            print('Done downloading, now converting ...')

    def download(self, link, filename, overwrite=False):
        fname = get_filename_ext(filename, self.outdir)
        if fname is not None:
            if overwrite:
                os.remove(os.path.join(self.outdir, fname))
            else:
                logging.info("File already downloaded, skipping: %s" % fname)
                return

        if filename is not None:
            self.ydl_opts['outtmpl'] = os.path.join(self.outdir, filename + '.%(ext)s')
        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            ydl.download([link])
        if filename is not None:
            self.ydl_opts['outtmpl'] = self.outtempl


def main():
    while True:
        print("Enter yt link:")
        link = input()
        if '/' not in link:
            break


if __name__ == '__main__':
    main()
