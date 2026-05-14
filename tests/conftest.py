import pytest
from django.test import TestCase

@pytest.fixture(autouse=True)
def enable_db_for_all_tests(db):
    """Automatically injects database access into every single test."""
    pass
