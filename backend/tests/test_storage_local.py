import shutil
from backend.src.storage import LocalStorageService
from pathlib import Path


def test_local_storage_confirm_and_download(tmp_path):
    # create a fake raw_root and a test file
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    src = raw_root / "folder" / "file.txt"
    src.parent.mkdir()
    content = b"hello-storage"
    src.write_bytes(content)

    svc = LocalStorageService(raw_root)

    # confirm_object should report exists and size
    r = svc.confirm_object("folder/file.txt")
    assert r.get("exists") is True
    assert int(r.get("size_bytes")) == len(content)

    # generate_download_url returns the assets path
    url = svc.generate_download_url("folder/file.txt")
    assert url.endswith("/assets/folder/file.txt")

    # download_to_temp should copy and return a Path
    tmp_copy = svc.download_to_temp("folder/file.txt")
    assert Path(tmp_copy).exists()
    assert Path(tmp_copy).read_bytes() == content
    # cleanup
    try:
        Path(tmp_copy).unlink()
    except Exception:
        pass
