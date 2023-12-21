import re
import subprocess

import click
import json
import os
import webbrowser

from src import conf
from src.file_index import FileIndex
from src.persistance.storage import Storage, SusCode
from src.playlist import Playlist
from src.search import Search
from src.utils.fs_utils import ensure_dir
from src.youtube.search import isrc_search, get_search_url, get_search_terms
from src.ytdownload import get_filename_ext
from src.universal_menu import Menu
from src.track import Track, SusTrack
from src.local_files import LocalFileManager

singleton_spotify_playlists = []
singleton_local_file_manager = []


def get_local_file_manager() -> LocalFileManager:
    if len(singleton_local_file_manager) == 0:
        singleton_local_file_manager.append(LocalFileManager())
    return singleton_local_file_manager[0]


def is_track_acceptable(isrc):
    if isrc not in Storage.isrc_to_access_url:
        return False
    if Storage.is_manual_confirm(isrc):
        return True
    if isrc in Storage.sus_tracks:
        code = Storage.get_sus_track(isrc)['code']
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
    # TODO: think about reimplementing match count.
    # The last implementation counted how many keywords matched.
    # Since this does not seem crucial, reimplementing it - now it counts every math with an artist or title.

    tracks = map(lambda x: Track.from_storage_isrc_to_track_data_isrc(*x), Storage.get_isrc_to_track_datas().items())
    while True:
        search_string = input("Search track; or enter 'q' to return to menu: ")
        if search_string == 'q':
            return None
        kws = search_string.split()
        search = Search()
        search.search_tracks(tracks, kws)
        if search.has_results():
            print('No tracks match search.')
        return search.get_results(max_results)


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
    return not is_track_acceptable(isrc) and not Storage.is_track_ignored(isrc)


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
        print(f'\rProcessing {playlist.get_displayname()}: {i}/{number_of_tracks}', end='')
        # TODO: solve deleted playlists hanging out in Storage, deimplement soft delete?
        convert_track_to_youtube_link(track)
    print()


def convert_active_playlists_to_youtube_links():
    playlists = get_playlists()

    # TODO: This code does not use Storage anymore. Think how to link up with Storage if even needed.
    for playlist in playlists:
        if not playlist.is_active: continue
        convert_playlist_tracks_to_youtube_links(playlist)


def open_browser_link_if_valid(url):
    if isinstance(url, str) and url:
        webbrowser.open(url)


def review_with_browser():
    review(True)


def review(browser=False):
    tracks = list(filter(lambda isrc: needs_converting(isrc), Storage.sus_tracks.copy()))
    track_count = len(tracks)
    for i, isrc in enumerate(tracks):
        sus_track = SusTrack(isrc)
        print(f'{i + 1}/{track_count} {sus_track}')

        if browser:
            if sus_track.url:
                open_browser_link_if_valid(sus_track.url)
            open_browser_link_if_valid(get_search_url(get_search_terms(sus_track.artists, sus_track.title)))

        while True:
            prompt_commands = {'Enter new link': get_new_link,
                               'Confirm old link': confirm_old_link,
                               'Skip': lambda x: 1,
                               'Ignore': ignore_sus_track,
                               'Back to main menu': lambda x: 1}
            prompts = list(prompt_commands)
            selected = Menu(prompts).show()
            selected_prompt = prompts[selected]
            prompt_commands[selected_prompt](sus_track)
            if selected == 4: return
            if selected == 1 and not sus_track.url:
                print("Old url missing. Type 'skip' to skip")
                continue
            break


def get_flacified_path(in_filename_ext: str):
    filename_no_ext = in_filename_ext[:in_filename_ext.rindex('.')]
    return os.path.join(conf.flacified_audio_folder, filename_no_ext + '.flac')


def convert_track_file_to_flac(in_path: str, in_filename_ext: str):
    flac_filepath = get_flacified_path(in_filename_ext)

    # Analyze the audio file for maximum volume
    analysis_command = [
        'ffmpeg', '-i', in_path,
        '-af', 'volumedetect',
        '-f', 'null', '-'
    ]
    result = subprocess.run(analysis_command, capture_output=True, text=True, encoding='utf-8')

    # Regex to extract max_volume from analysis
    max_volume_match = re.search(r"max_volume: ([\-\d\.]+) dB", result.stderr)
    if max_volume_match:
        max_volume = float(max_volume_match.group(1))
    else:
        print("Failed to analyze file:", in_filename_ext)
        return

    # Calculate required gain to reach the target level
    gain = -0.001 - max_volume

    # Normalize the audio file and convert it to FLAC
    normalize_command = [
        'ffmpeg', '-i', in_path,
        '-af', f'volume={gain}dB',
        '-c:a', 'flac',
        '-map_metadata', '0',
        '-id3v2_version', '3',
        '-y', flac_filepath
    ]
    subprocess.run(normalize_command)


def convert_flacify_playlists_files_to_flac(overwrite: bool = False):
    local_file_index = FileIndex(conf.spotify_local_files_folders)

    playlists = get_playlists()

    path_to_fname_ext = {}
    for playlist in playlists:
        if not playlist.is_flacify:
            continue
        for track in playlist.tracks:
            if track.is_local:
                index, filename = track.get_local_folder_idx_and_filename(local_file_index)
                if not filename:
                    continue
                if index >= len(conf.spotify_local_files_folders):
                    print('WARNING: configuration does not have enough local files folders')
                    continue
                path = os.path.join(conf.spotify_local_files_folders[index], filename)
                path_to_fname_ext[path] = filename
            else:
                fname_ext = get_filename_ext(track.filename, conf.downloaded_audio_folder)
                if not fname_ext:
                    print(f'\nWARNING: track "{fname_ext}" missing')
                    continue
                path = os.path.join(conf.downloaded_audio_folder, fname_ext)
                path_to_fname_ext[path] = fname_ext

    to_skip = set()
    if not overwrite:
        for path, fname_ext in path_to_fname_ext.items():
            if os.path.isfile(get_flacified_path(fname_ext)):
                to_skip.add(path)

    ensure_dir(conf.flacified_audio_folder)
    number_of_tracks = len(path_to_fname_ext) - len(to_skip)
    for i, (path, fname_ext) in enumerate(path_to_fname_ext.items()):
        if path in to_skip:
            continue
        # TODO: use logger
        print(f'Flacifying tracks: {i}/{number_of_tracks}')
        convert_track_file_to_flac(path, fname_ext)


def convert_flacify_playlists_files_to_flac_overwrite():
    convert_flacify_playlists_files_to_flac(True)


def ignore_sus_track(track):
    Storage.ignore_track(track.isrc)


def confirm_old_link(track):
    if track.url:
        Storage.reset_track(track.isrc, force=True)
        Storage.add_access_url(track.isrc, track.url)
        Storage.confirm(track.isrc)


def get_new_link(track):
    new_link = click.prompt("Enter new link")
    confirmation = click.confirm(f"New link set as {new_link}", default=True)
    if confirmation:
        isrc = track.isrc
        Storage.reset_track(isrc, force=True)
        Storage.add_access_url(isrc, new_link)
        Storage.confirm(isrc)


def reset_track():
    # Gives out Track instance with isrc, artists, title and filename, not entire Track set
    tracks = search_track()
    if not tracks: return

    prompts = [f'{track.describe_track()} ({track.match_count})' for track in tracks] + ['Back']
    selected = Menu(prompts).show()

    if prompts[selected] == 'Back': return
    track = tracks[selected]
    confirmed = click.confirm(f'Are you sure to reset {track.isrc}', default=True)

    if not confirmed: return

    filename_with_extension = get_filename_ext(track.filename, conf.downloaded_audio_folder)

    if filename_with_extension:
        new_file_path = os.path.join(conf.downloaded_audio_folder, filename_with_extension)
        os.remove(new_file_path)

    Storage.reset_track(track.isrc, force=True)

    url = input("Enter new track url or 'q' to return to menu: ")
    track.set_download_url(url)
    if url != '' and url != 'q':
        Storage.add_access_url(track.isrc, track.url)
        Storage.confirm(track.isrc)


def list_manual():
    print("Manually confirmed tracks:")
    i = 0
    for isrc in Storage.manual_confirm:
        if Storage.is_manual_confirm(isrc):
            print("%s; %s; %s" % (isrc, Storage.get_access_url(isrc), Storage.get_track_data(isrc)))
            i += 1
    print("Total %d manually confirmed tracks" % i)


def get_playlists() -> [Playlist]:
    if len(singleton_spotify_playlists) == 0:
        with open(conf.playlists_file, "r") as f:
            singleton_spotify_playlists.extend(map(Playlist.from_json, json.loads(f.read())))
    return singleton_spotify_playlists


def list_playlists(playlists: [Playlist] = None) -> [Playlist]:
    if playlists is None:
        playlists = get_playlists()
    for i, playlist in enumerate(playlists):
        click.echo(f"{i:>5} {playlist.get_menu_string_with_active_state()}")
    return playlists


def list_flacify_playlists(playlists: [Playlist] = None) -> [Playlist]:
    if playlists is None:
        playlists = get_playlists()
    for i, playlist in enumerate(playlists):
        click.echo(f"{i:>5} {playlist.get_menu_string_with_flacify_state()}")
    return playlists


def get_playlist_comp_names():
    data = []
    for i, plist in enumerate(Storage.playlist_compositions.keys()):
        data.append(plist)
    return data


def edit_composition(name, comp):
    filemgr = get_local_file_manager()
    playlists = get_playlists() + filemgr.get_meta_playlists()

    while True:
        prompts = [p.get_menu_string_with_composition_status(comp) for p in playlists] + ['Delete composition', 'Back']
        selected_prompt_index = Menu(prompts).show()
        selected_prompt = prompts[selected_prompt_index]

        if selected_prompt == 'Back':
            return
        if selected_prompt == 'Delete composition':
            Storage.remove_composition(name)
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
    while True:
        playlists = get_playlists()
        prompts = [p.get_menu_string_with_active_state() for p in playlists] + ['Back']
        selected = Menu(prompts).show()
        selected_prompt = prompts[selected]
        if selected_prompt == 'Back':
            return
        playlists[selected].toggle_is_active()


def toggle_flacify_playlists():
    while True:
        playlists = get_playlists()
        prompts = [p.get_menu_string_with_flacify_state() for p in playlists] + ['Back']
        selected = Menu(prompts).show()
        selected_prompt = prompts[selected]
        if selected_prompt == 'Back':
            return
        playlists[selected].toggle_is_flacify()


def interactive():
    while True:
        prompt_commands = {
            'Toggle active playlists': toggle_active_playlists,
            'Convert playlists to youtube': convert_active_playlists_to_youtube_links,
            'Review sus tracks': review,
            'Review sus tracks while automatically opening youtube pages': review_with_browser,
            'Reset confirmed track': reset_track,
            'List manually confirmed tracks': list_manual,
            'Edit playlist compositions': compose_playlists,
            'Toggle active flacify playlists': toggle_flacify_playlists,
            'Flacify playlists': convert_flacify_playlists_files_to_flac,
            'Flacify playlists with overwrite': convert_flacify_playlists_files_to_flac_overwrite,
            'Exit': quit
        }
        prompts = list(prompt_commands.keys())
        selected_prompt_index = Menu(prompts).show()
        selected_prompt = prompts[selected_prompt_index]
        prompt_commands[selected_prompt]()
        if selected_prompt_index not in [6, 9, 10]:
            Storage.save()
            click.echo('Data saved.')
        click.echo()


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        interactive()


@cli.command
def ls():
    list_playlists()


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
def lsflacify():
    list_flacify_playlists()


@cli.command("set_flacify")
@click.argument('playlist_number', type=int)
def flacify_playlist(playlist_number: int):
    get_playlists()[playlist_number].set_flacify(True)
    Storage.save()
    print('Data saved.')


@cli.command("unset_flacify")
@click.argument('playlist_number', type=int)
def deflacify_playlist(playlist_number):
    get_playlists()[playlist_number].set_flacify(False)
    Storage.save()
    print('Data saved.')


@cli.command
@click.option("--overwrite", default=False, help="Overwrite flac files")
def flacify(overwrite=False):
    convert_flacify_playlists_files_to_flac(overwrite)


@cli.command
def compose():
    compose_playlists()
    Storage.save()
    print('Data saved.')


@cli.command
def lsman():
    list_manual()


@cli.command
def convert():
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
    Storage.storage_setup()
    cli()
