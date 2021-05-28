# from __future__ import unicode_literals
import youtube_dl
import os

ytdl_extension = '.m4a'


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
            'format': 'best',
            'socket_timeout': 5,
            'retries': 5,
            'logger': DlLogger(),
            'progress_hooks': [self.msg_hook],
            'outtmpl': self.outtempl,
            # 'nocheckcertificate' : True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                # 'preferredcodec': 'mp3',
                # 'preferredquality': '320',
            }]
        }

    def msg_hook(self, d):
        if d['status'] == 'finished':
            print('Done downloading, now converting ...')

    def download(self, link, filename=None, overwrite=False):
        if os.path.isfile(os.path.join(self.outdir, filename + ytdl_extension)):
            if overwrite:
                os.remove(filename)
            else:
                print("File already downloaded, skipping: %s" % (filename + ytdl_extension))
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
