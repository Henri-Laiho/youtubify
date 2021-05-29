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


def convert_tracks():
    f = open(conf.playlists_file, "r")
    data = json.loads(f.read())
    f.close()

    data_ids = {'0' if 'id' not in plist else plist['id']: plist for plist in data}
    for playlist_id in Storage.active_playlist_ids:
        if Storage.is_active_playlist(playlist_id):
            playlist = data_ids[playlist_id]
            for x in playlist['tracks']:
                if x['track']['is_local']:
                    continue
                Storage.set_track_data(x['track']['external_ids']['isrc'],
                                       artists=[y['name'] for y in x['track']['artists']],
                                       title=x['track']['name'])

            i = 0
            tracks = playlist['tracks'][:]
            for x in tracks:
                i += 1
                print('\rProcessing %s: %d/%d' % (playlist['name'], i, len(tracks)), end='')
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


def review(browser=False):
    state = 3
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


def reset_track():
    tracks = search_track()
    if tracks is None:
        print('')
        return None
    for i, (isrc, match) in enumerate(tracks):
        print('%d. %s (%d)' % (len(tracks) - i, describe_track(isrc), match))
    while 1:
        idx = input("Select track or enter 'q' to return to menu: ")
        if idx == 'q':
            break
        elif idx == '':
            pass
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


def list_playlists(data=None):
    if data is None:
        f = open(conf.playlists_file, "r")
        data = json.loads(f.read())
        f.close()
    for i, plist in enumerate(data):
        print('%4d' % i, '+' if Storage.is_active_playlist('0' if 'id' not in plist else plist['id']) else ' ',
              plist['name'])
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    add_storage_argparse(parser)

    parser.add_argument('-c', '--convert', action='store_true', help='Convert playlists to youtube', default=False)
    parser.add_argument('-s', '--reset', action='store_true', help='Reset confirmed track', default=False)
    parser.add_argument('-r', '--review', action='store_true', help='Review sus tracks', default=False)
    parser.add_argument('-R', '--review_browser', action='store_true',
                        help='Review sus tracks while automatically opening youtube pages', default=False)
    parser.add_argument('-l', '--list', action='store_true', help='List available playlists with activation status',
                        default=False)
    parser.add_argument('-a', '--activate', type=int,
                        help='Activate playlist for spotify to youtube synchronization, ' +
                             'use "youtubify -l" to list available playlists', default=None)
    parser.add_argument('-d', '--deactivate', type=int,
                        help='Deactivate playlist from spotify to youtube synchronization, ' +
                             'use "youtubify -l" to list available playlists', default=None)
    args = parser.parse_args()
    storage_setup(args)

    if args.list:
        list_playlists()
    elif args.activate is not None:
        f = open(conf.playlists_file, "r")
        data = json.loads(f.read())
        f.close()
        playlist = data[args.activate]
        id_code = '0' if 'id' not in playlist else playlist['id']
        Storage.set_active_playlist(id_code, True)
        Storage.save()
        print('Data saved.')
    elif args.deactivate is not None:
        f = open(conf.playlists_file, "r")
        data = json.loads(f.read())
        f.close()
        playlist = data[args.deactivate]
        id_code = '0' if 'id' not in playlist else playlist['id']
        Storage.set_active_playlist(id_code, False)
        Storage.save()
        print('Data saved.')
    elif args.convert:
        convert_tracks()
        Storage.save()
        print('Data saved.')
    elif args.review:
        review()
        Storage.save()
        print('Data saved.')
    elif args.review_browser:
        review(True)
        Storage.save()
        print('Data saved.')
    elif args.reset:
        reset_track()
        Storage.save()
        print('Data saved.')
    else:
        state = 0
        playlist = None
        browser = False
        while state > -1:
            if state == 0:
                print('1 - Toggle active playlists')
                print('2 - Convert playlists to youtube')
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
                data = None
                while 1:
                    data = list_playlists(data)
                    idx = input('Select playlist to toggle or enter q to exit: ')
                    if idx == '' or idx == 'q':
                        break
                    try:
                        playlist = data[int(idx)]
                        id_code = '0' if 'id' not in playlist else playlist['id']
                        Storage.set_active_playlist(id_code, not Storage.is_active_playlist(id_code))
                    except ValueError:
                        print('Invalid input')
                Storage.save()
                print('Data saved.')
                state = 0
            elif state == 2:
                convert_tracks()
                Storage.save()
                print('Data saved.')
                state = 0
            elif state == 3:
                review(browser)
                Storage.save()
                print('Data saved.')
                state = 0
            elif state == 4:
                reset_track()
                Storage.save()
                print('Data saved.')
                state = 0
            print()
        Storage.save()
        print('Data saved.')
