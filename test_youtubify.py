from click.testing import CliRunner

from test_constants import playlist_json, isrc_to_data_liked_songs_active, ytfy_data_liked_songs_active
from youtubify import convert, lsman, ls, activate


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
    assert isrc_to_data == isrc_to_data_liked_songs_active
    assert ytfy_data == ytfy_data_liked_songs_active
    assert convert_result.stdout_bytes == b'Data file not found; starting with empty database.\n\rProcessing Liked Songs: 0/1\nData saved.\n'
    assert convert_result.exit_code == 0


def test_lsman():
    runner = CliRunner()
    result = runner.invoke(lsman)
    assert not result.exception
    assert result.exit_code == 0


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
    assert result.exit_code == 0
    assert result.stdout_bytes == b'    0   Liked Songs\n    1   testing\n'


def test_reset():
    pass


def test_review():
    pass


if __name__ == "__main__":
    # TODO: make tests isolated - currently test_convert() affects output of test_list()
    test_list()
    test_convert()
