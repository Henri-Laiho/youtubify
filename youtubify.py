import argparse
import json
import os
import webbrowser

from src import conf
from src.downloader import get_nice_path
from src.persistance.track_data import Storage, SusCode, add_storage_argparse, storage_setup, describe_track
from src.search.Search import isrc_search, get_search_url, get_search_terms
from src.ytdownload import ytdl_extension


def is_track_acceptable(isrc):
    if isrc not in Storage.isrc_to_access_url:
        return False
    if isrc in Storage.manual_confirm:
        return True
    if isrc in Storage.sus_tracks:
        code = Storage.sus_tracks[isrc]['code']
        if code in [SusCode.isrc_no_artist_match, SusCode.isrc_low_lev]:
            return True
        return False
    else:
        return True


def matches(track_data, keyword):
    title = track_data['title']
    artists = track_data['artists']
    return keyword.lower() in title.lower() or any(keyword.lower() in artist.lower() for artist in artists)


def search_track(max_results=100):
    while True:
        search_string = input("Search track; or enter 'q' to return to menu: ")
        if search_string == 'q':
            return None
        kws = search_string.split()
        match_counts = []
        for isrc in Storage.isrc_to_track_data:
            data = Storage.isrc_to_track_data[isrc]
            match_counts.append((isrc, sum(matches(data, kw) for kw in kws)))
        match_counts = list(sorted(filter(lambda y: y[1] > 0, match_counts), key=lambda y: y[1]))
        if len(match_counts) > 0:
            if len(match_counts) > max_results > 0:
                return match_counts[-max_results:]
            return match_counts
        print('No tracks match search.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    add_storage_argparse(parser)
    args = parser.parse_args()
    storage_setup(args)

    state = 0
    playlist = None
    browser = False
    while state > -1:
        if state == 0:
            if playlist is not None:
                print('Loaded playlist: ' + playlist['name'])
            else:
                print('No playlist loaded')
            print('1 - Load new playlist')
            print('2 - Convert playlist to youtube')
            print('3 - Review sus tracks')
            print('3a - Review sus tracks while automatically opening youtube pages')
            print('4 - Reset confirmed track')
            print('q - Exit')
            act = input('Select: ')
            if act == '1':
                state = 1
            elif act == '2':
                state = 2
            elif act == '3':
                state = 3
                browser = False
            elif act == '3a':
                state = 3
                browser = True
            elif act == '4':
                state = 4
            elif act == 'q':
                state = -1

        if state == 1:
            f = open(conf.playlists_file, "r")
            data = json.loads(f.read())
            f.close()

            for i, plist in enumerate(data):
                print(i, plist['name'])
            while 1:
                idx = input('Select playlist: ')
                try:
                    playlist = data[int(idx)]
                    for x in playlist['tracks']:
                        if x['track']['is_local']:
                            continue
                        Storage.set_track_data(x['track']['external_ids']['isrc'],
                                               artists=[y['name'] for y in x['track']['artists']],
                                               title=x['track']['name'])
                    break
                except ValueError:
                    print('Invalid input')
            state = 0
        elif state == 2:
            if playlist is None:
                # print('Load playlist first.\n')
                state = 1
                continue
            state = 0
            i = 0
            tracks = playlist['tracks'][:]
            for x in tracks:
                i += 1
                print('Processing: %d/%d' % (i, len(tracks)), end='\r')
                last_track = x
                if x['track']['is_local']:
                    continue
                # spotify adapter
                isrc = x['track']['external_ids']['isrc']
                name = x['track']['name']
                artists = [y['name'] for y in x['track']['artists']]

                if not is_track_acceptable(isrc) and not (
                        isrc in Storage.ignored_tracks and Storage.ignored_tracks[isrc]):
                    Storage.reset_track(isrc)
                    url = isrc_search(isrc, artists, name, x['track']['duration_ms'] / 1000, False, True)
                    Storage.add_access_url(isrc, url)
            print()
            Storage.save()
            print('Data saved.')

        elif state == 3:
            added = []
            i = 0
            for isrc in Storage.sus_tracks:
                i += 1
                sus_code = Storage.sus_tracks[isrc]['code']
                if not is_track_acceptable(isrc) and not (
                        isrc in Storage.ignored_tracks and Storage.ignored_tracks[isrc]):
                    track = Storage.isrc_to_track_data[isrc]
                    name = track['title']
                    artists = track['artists']
                    url = Storage.isrc_to_access_url[isrc]
                    print('%d/%d Sus-code: %s, Track %s - %s, isrc: %s, current url: %s' % (i, len(Storage.sus_tracks),
                                                                                            sus_code.ljust(22),
                                                                                            ', '.join(artists), name,
                                                                                            isrc, url))

                    if browser:
                        if isinstance(url, str):
                            webbrowser.open(url)
                        webbrowser.open(get_search_url(get_search_terms(artists, name)))

                    while 1:
                        text = input(
                            'Enter new link, nothing to confirm old link, "skip" to skip this time, "ignore" to ignore next times or "abort" to return to main menu:\n')
                        if text == 'skip':
                            break
                        elif text == 'ignore':
                            Storage.ignore_track(isrc)
                            break
                        elif text == 'abort':
                            state = 0
                            break
                        elif text == '' or text.startswith('http') or 'youtube.com' in text:
                            if text == '':
                                if isinstance(url, str):
                                    text = url
                                else:
                                    print("Old url missing. Type 'skip' to skip")
                                    continue
                            confirm = input('Confirm link %s (Y/n): ' % text)
                            if confirm.lower() != 'n':
                                added.append((isrc, text))
                                break
                    if state != 3:
                        break
            for isrc, text in added:
                Storage.reset_track(isrc, force=True)
                Storage.add_access_url(isrc, text)
                Storage.confirm(isrc)
            state = 0
            Storage.save()
            print('Data saved.')
        elif state == 4:
            tracks = search_track()
            state = 0
            if tracks is None:
                print('')
                continue
            for i, (isrc, match) in enumerate(tracks):
                print('%d. %s (%d)' % (len(tracks) - i, describe_track(isrc), match))
            while 1:
                idx = input("Select track or enter 'q' to return to menu: ")
                if idx == 'q':
                    break
                elif idx == '':
                    idx = '1'
                else:
                    try:
                        isrc, _ = tracks[len(tracks) - int(idx)]
                        confirm = input('Are you sure to reset %s (Y/n): ' % describe_track(isrc))
                        if confirm.lower() != 'n':

                            if isrc in Storage.isrc_to_track_data:
                                data = Storage.isrc_to_track_data[isrc]
                                newfilename = get_nice_path(data['title'], data['artists'])
                                newpath_ext = os.path.join(conf.downloaded_audio_folder, newfilename) + ytdl_extension
                                if os.path.isfile(newpath_ext):
                                    os.remove(newpath_ext)

                            Storage.reset_track(isrc, force=True)
                            url = input("Enter new track url or 'q' to return to menu: ")
                            if url != '' and url != 'q':
                                Storage.add_access_url(isrc, url)
                                Storage.confirm(isrc)
                            break
                    except ValueError:
                        print('Invalid input')
            Storage.save()
            print('Data saved.')

        print()
    Storage.save()
    print('Data saved.')
