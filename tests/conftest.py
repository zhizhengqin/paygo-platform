import pytest
from app.db import reset_db


@pytest.fixture(autouse=True)
def clear_db():
    reset_db()
