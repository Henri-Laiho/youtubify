import logging

import yt_dlp as youtube_dl
import os
import re

try:
    from src.utils.fs_utils import ensure_dir, get_filename_ext
except ImportError:
    from utils.fs_utils import ensure_dir, get_filename_ext


def sanitize_string(input_string):
    sanitized_string = "".join([
        ch if re.match(r'[A-Za-z0-9 ]', ch) else "%u" + format(ord(ch), '04x') for ch in input_string
    ])
    return sanitized_string


class YtDownload(object):
    def __init__(self, outDir='downloaded', name='downloader', logger=logging.getLogger(''), update_status_callback=None):
        self.outdir = outDir
        self.name = name
        self.outtempl = os.path.join(outDir, '%(title)s.%(ext)s')
        self.logger = logger
        self.update_status_callback = update_status_callback

        ensure_dir(outDir)

        self.ydl_opts = {
            'audio-format': 'best',
            'socket_timeout': 5,
            'retries': 5,
            'logger': logger,
            'progress_hooks': [self.msg_hook],
            'outtmpl': self.outtempl,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
            }]
        }

    def msg_hook(self, d):
        if self.update_status_callback:
            self.update_status_callback(d)
        elif d['status'] == 'finished':
            self.logger.info('Done downloading, now converting ...')
        elif d['status'] == 'downloading':
            self.logger.info('downloading %s of %s @%s, ETA %s' % (d['_percent_str'], d['_total_bytes_str'], d['_speed_str'], d['_eta_str']))

    def download(self, link, filename, overwrite=False):
        if filename is not None:
            fname = get_filename_ext(filename, self.outdir)
            if fname is not None:
                if overwrite:
                    os.remove(os.path.join(self.outdir, fname))
                else:
                    self.logger.info("File already downloaded, skipping: %s" % fname)
                    return
        filename_sanitized = None
        if filename is not None:
            filename_sanitized = sanitize_string(filename)
            self.ydl_opts['outtmpl'] = os.path.join(self.outdir, filename_sanitized + '.%(ext)s')
        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            ydl.download([link])
        if filename is not None:
            self.ydl_opts['outtmpl'] = self.outtempl
            fname = get_filename_ext(filename_sanitized, self.outdir)
            if fname is not None:
                ext = fname[fname.rfind('.'):]
                os.rename(
                    os.path.join(self.outdir, fname),
                    os.path.join(self.outdir, filename + ext)
                )


def main():
    logging.getLogger('').setLevel(logging.NOTSET)
    logging.getLogger('').addHandler(logging.StreamHandler())
    while True:
        dl = YtDownload()
        print("Enter yt link:")
        link = input()
        if '/' not in link:
            break
        dl.download(link, None)


if __name__ == '__main__':
    main()
