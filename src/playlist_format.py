# TODO: implement UI for mode choice
mode = 'm3u8'


def format_m3u8(fname: str, number: int, fullpath: str):
    return "#EXTINF:%d,%s%s%s" % (number, fname, '\n', fullpath)


def format_simple(fname: str, number: int, fullpath: str):
    return fname

class PlaylistFormat:
    def __init__(self, mode, header, formatter, extension):
        self.mode = mode
        self.header = header
        self.formatter = formatter
        self.extension = extension
