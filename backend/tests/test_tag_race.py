"""Regression tests: concurrent get-or-create of the same tag name.

Reproduces the n8n race where two sessions both fail the existence
check and both attempt to INSERT the same tag name. The loser must
resolve to the winner's row instead of raising IntegrityError.
"""
import threading

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (register models on Base)
import app.services.tag_service as tag_service
from app.database import Base
from app.models import Tag
from app.services.tag_service import get_or_create_tag, get_or_create_tags


@pytest.fixture
def race_session_factory(tmp_path):
    """Session factory over a file-backed SQLite DB with real separate
    connections, so two sessions genuinely contend for the same write."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'race.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(autocommit=False, autoflush=False, bind=engine)
    engine.dispose()


def test_sequential_get_or_create_is_idempotent(db_session):
    first = get_or_create_tag(db_session, "Container")
    second = get_or_create_tag(db_session, "container")
    assert first.id == second.id
    assert first.name == second.name == "container"


def test_get_or_create_tags_with_duplicate_names_is_stable(db_session):
    tags = get_or_create_tags(db_session, ["alpha", "Alpha", " beta "])
    assert [t.name for t in tags] == ["alpha", "alpha", "beta"]
    assert len({t.id for t in tags}) == 2


def test_concurrent_get_or_create_same_tag_resolves_to_one_row(race_session_factory):
    """Two sessions pass the existence check at the same time, then both
    try to INSERT. The loser must fall back to the winner's row."""
    barrier = threading.Barrier(2)
    original_normalize = tag_service.normalize_tag_name

    def synchronized_normalize(name):
        # Hold both threads at the existence check so neither has
        # committed an insert yet.
        barrier.wait(timeout=10)
        return original_normalize(name)

    results = {}
    errors = {}

    def worker(key):
        db = race_session_factory()
        try:
            results[key] = get_or_create_tag(db, "container")
        except Exception as exc:
            errors[key] = exc
        finally:
            db.close()

    tag_service.normalize_tag_name = synchronized_normalize
    try:
        threads = [
            threading.Thread(target=worker, args=("a",)),
            threading.Thread(target=worker, args=("b",)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
    finally:
        tag_service.normalize_tag_name = original_normalize

    assert errors == {}
    assert results["a"].id == results["b"].id
    assert results["a"].name == "container"

    check_db = race_session_factory()
    try:
        count = check_db.query(Tag).filter(Tag.name == "container").count()
        assert count == 1
    finally:
        check_db.close()
