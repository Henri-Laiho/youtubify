import click
import json
import os
import webbrowser

from src import conf
from src.persistance.storage import Storage, SusCode, storage_setup, describe_track
from src.playlist import Playlist
from src.search.Search import isrc_search, get_search_url, get_search_terms
from src.ytdownload import get_filename_ext
from src.universal_menu import Menu
from src.track import Track


singleton_spotify_playlists = []


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


def convert_playlist_tracks_to_youtube_links(playlist: Playlist):
    temp_name_to_isrc = dict()
    tracks = playlist.tracks

    for track in tracks:
        store_track_data(track, temp_name_to_isrc)

    number_of_tracks = len(tracks)

    for i, track in enumerate(tracks):
        # TODO: use logger
        print(f'\rProcessing {playlist.name}: {i}/{number_of_tracks}', end='')
        convert_track_to_youtube_link(track)
    print()


def convert_active_playlists_to_youtube_links():
    with open(conf.playlists_file, 'r') as f:
        playlists_json = json.loads(f.read())
    playlists = map(Playlist.from_json, playlists_json)

    # TODO: This code does not use Storage anymore. Think how to link up with Storage if even needed.
    for playlist in playlists:
        if not playlist.is_active: continue
        convert_playlist_tracks_to_youtube_links(playlist)


def review_with_browser():
    review(True)


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


def list_manual():
    print("Manually confirmed tracks:")
    i = 0
    for isrc in Storage.manual_confirm:
        if Storage.manual_confirm[isrc]:
            print("%s; %s; %s" % (isrc, Storage.isrc_to_access_url[isrc], Storage.isrc_to_track_data[isrc]))
            i += 1
    print("Total %d manually confirmed tracks" % i)


def get_playlists() -> [Playlist]:
    if len(singleton_spotify_playlists) == 0:
        with open(conf.playlists_file, "r") as f:
            singleton_spotify_playlists.extend([Playlist.from_json(p) for p in json.loads(f.read())])
    return singleton_spotify_playlists


def list_playlists(playlists: [Playlist]=None) -> [Playlist]:
    if playlists is None:
        playlists = get_playlists()
    for i, playlist in enumerate(playlists):
        click.echo(f"{i:>5} {playlist.get_menu_string_with_active_state()}")
    return playlists


def get_playlist_comp_names():
    data = []
    for i, plist in enumerate(Storage.playlist_compositions.keys()):
        data.append(plist)
    return data


def edit_composition(name, comp):
    playlists = get_playlists()

    while True:
        prompts = [p.get_menu_string_with_composition_status(comp) for p in playlists] + ['Delete composition', 'Back']
        selected_prompt_index = Menu(prompts).show()
        selected_prompt = prompts[selected_prompt_index]

        if selected_prompt == 'Back':
            return
        if selected_prompt == 'Delete composition':
            del Storage.playlist_compositions[name]
            return

        selected_playlist = playlists[selected_prompt_index]
        if selected_playlist.is_in_composition(comp):
            del comp[selected_playlist.id]
        else:
            comp[selected_playlist.id] = True


def compose_playlists():
    while True:
        compositions = get_playlist_comp_names()
        prompts = compositions + ['Enter a new composition', 'Back']
        selected_prompt_index = Menu(prompts).show()
        selected_prompt = prompts[selected_prompt_index]
        if selected_prompt == "Back":
            return
        if selected_prompt == 'Enter a new composition':
            comp_name = click.prompt("Composition name")
            comp = {}
            Storage.playlist_compositions[comp_name] = comp
        else:
            comp_name = selected_prompt
            comp = Storage.playlist_compositions[comp_name]
        edit_composition(comp_name, comp)


def toggle_active_playlists():
    active_playlist_menu_exit = False
    while not active_playlist_menu_exit:
        playlists = get_playlists()
        prompts = [p.get_menu_string_with_active_state() for p in playlists] + ['Back']
        selected = Menu(prompts).show()
        selected_prompt = prompts[selected]
        if selected_prompt == 'Back':
            return
        playlists[selected].toggle_is_active()


def interactive():
    while True:
        prompt_commands = {'Toggle active playlists': toggle_active_playlists,
                   'Convert playlists to youtube': convert_active_playlists_to_youtube_links,
                   'Review sus tracks': review,
                   'Review sus tracks while automatically opening youtube pages': review_with_browser,
                   'Reset confirmed track': reset_track,
                   'List manually confirmed tracks': list_manual,
                   'Edit playlist compositions': compose_playlists,
                   'Exit': quit}
        prompts = list(prompt_commands.keys())
        selected_prompt_index = Menu(prompts).show()
        selected_prompt = prompts[selected_prompt_index]
        prompt_commands[selected_prompt]()
        if selected_prompt_index not in [5, 7]:
            Storage.save()
            click.echo('Data saved.')
        click.echo()


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    storage_setup()
    if ctx.invoked_subcommand is None:
        interactive()


@cli.command("activate")
@click.argument('playlist_number', type=int)
def activate(playlist_number: int):
    get_playlists()[playlist_number].set_active(True)
    Storage.save()
    print('Data saved.')


@cli.command("deactivate")
@click.argument('playlist_number', type=int)
def deactivate_playlist(playlist_number):
    get_playlists()[playlist_number].set_active(False)
    Storage.save()
    print('Data saved.')


@cli.command
def compose():
    compose_playlists()
    Storage.save()
    print('Data saved.')


@cli.command
def ls():
    list_playlists()


@cli.command
def lsman():
    list_manual()


@cli.command
def convert():
    storage_setup()
    convert_active_playlists_to_youtube_links()
    Storage.save()
    print('Data saved.')


@cli.command
def reset():
    reset_track()
    Storage.save()
    print('Data saved.')


@cli.command("review")
@click.option("--browser", default=True, help="Review links in browser")
def review_cli(browser=False):
    review(browser)
    Storage.save()
    print('Data saved.')


if __name__ == '__main__':
    storage_setup()
    cli()
