import click
import json
import os
import webbrowser

from src import conf
from src.persistance.track_data import Storage, SusCode, storage_setup, describe_track
from src.playlist import Playlist
from src.search.Search import isrc_search, get_search_url, get_search_terms
from src.ytdownload import get_filename_ext
from src.universal_menu import Menu
from src.track import Track


@click.group()
def cli():
    pass


def is_track_acceptable(isrc):
    if isrc not in Storage.isrc_to_access_url:
        return False
    if isrc in Storage.manual_confirm and Storage.manual_confirm[isrc]:
        return True
    if isrc in Storage.sus_tracks:
        code = Storage.sus_tracks[isrc]['code']
        if code in [SusCode.isrc_no_artist_match, SusCode.isrc_low_lev]:
            return True
        return False
    else:
        return True


def get_track_duration_s(track):
    return track['track']['duration_ms'] / 1000


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


def store_track_data(track: Track, temp_name_to_isrc):

    if track.is_local:
        return
    if is_filename_not_unique(track, temp_name_to_isrc):
        print('Duplicate names: %s. Adding album name.' % track.filename)
        track.add_album_name_to_filename()
    if is_filename_not_unique(track, temp_name_to_isrc):
        track.add_album_and_isrc_to_filename()
    if is_filename_not_unique(track, temp_name_to_isrc):
        print('ERROR: duplicate artist, title, album and isrc: %s. Ignoring duplicate.' % track.filename)
        return
    temp_name_to_isrc[track.filename.lower()] = track.isrc

    persisted_filename = track.get_persisted_filename()
    if persisted_filename and persisted_filename != track.filename:
        track.update_filename_on_disk(persisted_filename)
    Storage.set_track_data(track.isrc, artists=track.artists, title=track.name, filename=track.filename)


def is_filename_not_unique(track, temp_name_to_isrc):
    return track.filename.lower() in temp_name_to_isrc


def needs_converting(isrc):
    # TODO: convert ignored_tracks to a set so that we can omit
    # "Storage.ignored_tracks[isrc]"
    return not is_track_acceptable(isrc) and not (isrc in Storage.ignored_tracks and Storage.ignored_tracks[isrc])


def convert_track_to_youtube_link(track: Track):
    if track.is_local:
        return

    if needs_converting(track.isrc):
        Storage.reset_track(track.isrc)
        url = isrc_search(track.isrc, track.artists, track.name, track.duration, False, True)
        track.set_download_url(url)
        Storage.add_access_url(track.isrc, track.download_url)


def convert_playlist_tracks_to_youtube_links(playlist_id, data_ids, playlists_to_disable):
    if Storage.is_active_playlist(playlist_id):
        temp_name_to_isrc = dict()
        if playlist_id not in data_ids:
            print("Playlist with id %s not found. Deactivating playlist." % playlist_id)
            if len(Storage.active_playlist_ids) - len(playlists_to_disable) > 1:
                playlists_to_disable.append(playlist_id)
            return
        playlist = data_ids[playlist_id]

        tracks = list(map(Track, playlist['tracks']))

        for track in tracks:
            store_track_data(track, temp_name_to_isrc)

        number_of_tracks = len(tracks)

        for i, track in enumerate(tracks):
            # TODO: use logger
            print('\rProcessing %s: %d/%d' % (playlist['name'], i, number_of_tracks), end='')
            convert_track_to_youtube_link(track)
        print()


def convert_active_playlists_to_youtube_links():
    f = open(conf.playlists_file, "r")
    data = json.loads(f.read())
    f.close()

    playlists_to_disable = []
    data_ids = {'0' if 'id' not in plist else plist['id']: plist for plist in data}
    for playlist_id in Storage.active_playlist_ids:
        convert_playlist_tracks_to_youtube_links(playlist_id, data_ids, playlists_to_disable)

    for playlist_id in playlists_to_disable:
        del Storage.active_playlist_ids[playlist_id]


@cli.command("review")
@click.option("--browser", default=True, help="Review links in browser")
def review_cli(browser=False):
    review(browser)


def review(browser=False):
    state = 3
    added = []
    i = 0
    for isrc in Storage.sus_tracks:
        i += 1
        sus_code = Storage.sus_tracks[isrc]['code']
        if needs_converting(isrc):
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
                text = input('Enter new link, nothing to confirm old link, "skip" to skip this time, "ignore" to ignore next times or "abort" to return to main menu:\n')
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


@cli.command
def reset():
    reset_track()


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
                        newfilename = data['filename']
                        fname_ext = get_filename_ext(newfilename, conf.downloaded_audio_folder)
                        if fname_ext is not None:
                            newpath_ext = os.path.join(conf.downloaded_audio_folder, fname_ext)
                            os.remove(newpath_ext)

                    Storage.reset_track(isrc, force=True)
                    url = input("Enter new track url or 'q' to return to menu: ")
                    if url != '' and url != 'q':
                        Storage.add_access_url(isrc, url)
                        Storage.confirm(isrc)
                    break
            except ValueError:
                print('Invalid input')


@cli.command
def lsman():
    list_manual()


def list_manual():
    print("Manually confirmed tracks:")
    i = 0
    for isrc in Storage.manual_confirm:
        if Storage.manual_confirm[isrc]:
            print("%s; %s; %s" % (isrc, Storage.isrc_to_access_url[isrc], Storage.isrc_to_track_data[isrc]))
            i += 1
    print("Total %d manually confirmed tracks" % i)


def is_active(plist):
    return Storage.is_active_playlist('0' if 'id' not in plist else plist['id'])


def is_active_playlist(plist: Playlist):
    return Storage.is_active_playlist(plist.id)


@cli.command("list")
def list_p():
    list_playlists()


def get_playlists():
    with open(conf.playlists_file, "r") as f:
        return [Playlist.from_json(p) for p in json.loads(f.read())]


def list_playlists(playlists: [Playlist] = None, condition=is_active) -> [Playlist]:
    if playlists is None:
        playlists = get_playlists()
    for i, playlist in enumerate(playlists):
        delimiter = '+' if is_active_playlist(playlist) else ' '
        click.echo(f'{i} {delimiter} {playlist.name}')
    return playlists


def list_playlist_comps():
    data = []
    for i, plist in enumerate(Storage.playlist_compositions.keys()):
        print('%4d' % i, plist)
        data.append(plist)
    return data


@cli.command
def compose():
    compose_playlists()


def compose_playlists():
    data = None
    while 1:
        comps = list_playlist_comps()
        name = click.prompt('Enter playlist composition name to edit or create composition, or q to exit')
        if name == '' or name == 'q':
            break
        try:
            name = comps[int(name)]
        except ValueError:
            pass
        if name in Storage.playlist_compositions:
            comp = Storage.playlist_compositions[name]
        else:
            comp = {}

        while 1:
            click.echo('Editing playlist composition "%s"' % name)
            data = list_playlists(data)
            idx = click.prompt('Select playlist to toggle or enter q to exit or enter "delete" to delete the composition')
            if idx == '' or idx == 'q':
                Storage.playlist_compositions[name] = comp
                break
            elif idx == 'delete':
                del Storage.playlist_compositions[name]
                break
            try:
                playlist = data[int(idx)]
                id_code = '0' if 'id' not in playlist else playlist['id']
                if id_code in comp:
                    del comp[id_code]
                else:
                    comp[id_code] = True
            except ValueError:
                print('Invalid input')


@cli.command("activate")
@click.argument('playlist_number', type=int)
def activate_playlist(playlist_number: int):
    toggle_playlist(playlist_number, True)


@cli.command("deactivate")
@click.argument('playlist_number', type=int)
def deactivate_playlist(playlist_number):
    toggle_playlist(playlist_number, False)


def toggle_playlist(selected_playlist, make_active):
    with open(conf.playlists_file, "r") as f:
        data = json.loads(f.read())
    playlist = data[selected_playlist]
    id_code = '0' if 'id' not in playlist else playlist['id']
    Storage.set_active_playlist(id_code, make_active)
    Storage.save()
    click.echo("Changes saved.")


@cli.command()
def interactive():
    main_menu_exit = False
    while not main_menu_exit:
        options = ['Toggle active playlists', 'Convert playlists to youtube', 'Review sus tracks',
                   'Review sus tracks while automatically opening youtube pages', 'Reset confirmed track',
                   'List manually confirmed tracks', 'Edit playlist compositions', 'Exit']
        state = Menu(options).show() + 1
        if state == 1:
            active_playlist_menu_exit = False
            while not active_playlist_menu_exit:
                playlists = get_playlists()
                selected = Menu([f"{'+' if d.is_active else ' '} {d.name}" for d in playlists] + ['Back']).show()
                if selected == len(playlists):
                    break
                try:
                    playlist = playlists[selected]
                    # TODO: make a toggle function to Storage
                    Storage.set_active_playlist(playlist.id, not Storage.is_active_playlist(playlist.id))
                except ValueError:
                    click.echo('Invalid input')
            Storage.save()
            click.echo('Data saved.')
        elif state == 2:
            convert_active_playlists_to_youtube_links()
            Storage.save()
            click.echo('Data saved.')
        elif state == 3:
            review()
            Storage.save()
            click.echo('Data saved.')
        elif state == 4:
            review(browser=True)
            Storage.save()
            click.echo('Data saved.')
        elif state == 5:
            reset_track()
            Storage.save()
            click.echo('Data saved.')
        elif state == 6:
            list_manual()
        elif state == 7:
            compose_playlists()
            Storage.save()
            click.echo('Data saved.')
        elif state == 8:
            quit()
        click.echo()


if __name__ == '__main__':
    storage_setup()
    cli()
    Storage.save()
    print('Data saved.')
