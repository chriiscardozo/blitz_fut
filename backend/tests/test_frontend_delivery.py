from pathlib import Path

from config.settings import frontend_static_dirs


def test_vite_assets_are_mounted_directly_below_static_url(tmp_path: Path):
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()

    assert frontend_static_dirs(tmp_path) == [assets_dir]
