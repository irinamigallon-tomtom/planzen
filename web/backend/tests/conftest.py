import pytest
from fastapi.testclient import TestClient
from pathlib import Path

import os
import tempfile

# Point session storage at a temp directory during tests
_tmp_session_dir = tempfile.mkdtemp()
os.environ["PLANZEN_SESSION_DIR"] = _tmp_session_dir

from main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def example_xlsx():
    return Path(__file__).parents[3] / "data/examples/input_example.xlsx"
