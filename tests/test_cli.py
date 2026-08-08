import os
import tempfile

import pytest

from restobot.cli import run


def test_missing_config_exits_cleanly(capsys):
    with pytest.raises(SystemExit) as exc_info:
        run("this_file_does_not_exist.yaml")
    assert exc_info.value.code == 1
    out = capsys.readouterr().out
    assert "Can't find a config file" in out


def test_malformed_yaml_exits_cleanly(capsys):
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write("name: [unterminated")
        path = f.name
    try:
        with pytest.raises(SystemExit) as exc_info:
            run(path)
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert "problem" in out
    finally:
        os.unlink(path)


def test_missing_required_field_exits_cleanly(capsys):
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write("locations: []")
        path = f.name
    try:
        with pytest.raises(SystemExit) as exc_info:
            run(path)
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert "problem" in out
    finally:
        os.unlink(path)
