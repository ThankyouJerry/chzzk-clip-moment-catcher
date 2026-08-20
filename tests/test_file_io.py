from pathlib import Path

import pytest

from core.file_io import atomic_save


def test_atomic_save_keeps_previous_destination_when_writer_fails(tmp_path):
    destination = tmp_path / "result.txt"
    destination.write_text("previous", encoding="utf-8")

    def failing_writer(temporary: Path):
        temporary.write_text("partial", encoding="utf-8")
        raise OSError("disk full")

    with pytest.raises(OSError, match="disk full"):
        atomic_save(destination, failing_writer)

    assert destination.read_text(encoding="utf-8") == "previous"
    assert [path for path in tmp_path.iterdir() if path != destination] == []


def test_atomic_save_replaces_destination_after_complete_write(tmp_path):
    destination = tmp_path / "result.txt"
    destination.write_text("previous", encoding="utf-8")

    atomic_save(destination, lambda temporary: temporary.write_text("complete", encoding="utf-8"))

    assert destination.read_text(encoding="utf-8") == "complete"
