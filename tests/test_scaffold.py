import pytest
from jlangbase.cli import main


def test_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "Japanese Language Baseline" in capsys.readouterr().out
