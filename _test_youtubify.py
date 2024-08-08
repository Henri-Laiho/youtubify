from click.testing import CliRunner
from os import linesep

from _test_constants import playlist_json, isrc_to_data_liked_songs_active, ytfy_data_liked_songs_active
from youtubify import convert, lsman, ls, activate

nl = linesep.encode()


def assertEquals(x, y):
    if x != y:
        print('Expected:', x)
        print('But got:', y)
    assert x == y


def seed_playlists_json():
    with open('playlists.json', 'w+') as playlists_file:
        playlists_file.write(playlist_json)


def get_file_contents(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()


def get_isrc_to_data_json():
    return get_file_contents('isrc_to_data.json')


def get_ytfy_data_json():
    return get_file_contents('ytfy_data.json')


def test_convert():
    runner = CliRunner()
    with runner.isolated_filesystem("tests"):
        seed_playlists_json()
        runner.invoke(activate, ['0'])
        convert_result = runner.invoke(convert)
        isrc_to_data = get_isrc_to_data_json()
        ytfy_data = get_ytfy_data_json()
    assertEquals(isrc_to_data, isrc_to_data_liked_songs_active)
    assertEquals(ytfy_data, ytfy_data_liked_songs_active)
    assertEquals(convert_result.stdout_bytes, b'Data file not found; starting with empty database.' + nl + b'\rProcessing Liked Songs: 0/1' + nl + b'Data saved.' + nl)
    assertEquals(convert_result.exit_code, 0)


def test_lsman():
    runner = CliRunner()
    result = runner.invoke(lsman)
    assertEquals(not result.exception, True)
    assertEquals(result.exit_code, 0)


def test_activate():
    pass


def test_deactivate():
    pass


def test_compose():
    pass


def test_list():
    runner = CliRunner()
    with runner.isolated_filesystem("tests"):
        seed_playlists_json()
        result = runner.invoke(ls)
    assertEquals(result.exit_code, 0)
    assertEquals(result.stdout_bytes, b'    0   Liked Songs' + nl + b'    1   testing' + nl)


def test_reset():
    pass


def test_review():
    pass


if __name__ == "__main__":
    # TODO: make tests isolated - currently test_convert() affects output of test_list()
    test_list()
    test_convert()
