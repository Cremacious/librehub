import re
from pathlib import Path

import librehub

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def test_version_present():
    assert re.fullmatch(r"\d+\.\d+\.\d+", librehub.__version__)


def test_version_matches_pyproject():
    declared = re.search(r'^version = "([^"]+)"',
                         PYPROJECT.read_text(), re.M).group(1)
    assert librehub.__version__ == declared
