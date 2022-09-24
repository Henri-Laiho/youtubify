from click.testing import CliRunner
from youtubify import lsman


def test_interactive_lsman_no_errors():
    runner = CliRunner()
    result = runner.invoke(lsman)
    assert not result.exception
    assert result.exit_code == 0


if __name__ == "__main__":
    test_interactive_lsman_no_errors()