# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from common.core.model_downloader import (
    ensure_midas_model_available,
    ensure_yolo_model_downloaded,
    get_midas_cache_directory,
)


@pytest.fixture
def tmp_models_dir(tmp_path):
    """Create a temporary models directory for testing."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    return models_dir


def test_get_midas_cache_directory_default():
    """Test that get_midas_cache_directory returns default PyTorch cache location."""
    cache_dir = get_midas_cache_directory()
    expected = Path.home() / ".cache" / "torch" / "hub"
    assert cache_dir == expected


def test_get_midas_cache_directory_custom(tmp_path):
    """Test that get_midas_cache_directory uses custom path when provided."""
    custom_path = tmp_path / "custom_cache"
    cache_dir = get_midas_cache_directory(custom_path)
    assert cache_dir == custom_path
    assert cache_dir.exists()


def test_ensure_yolo_model_downloaded_uses_cached_model(tmp_models_dir):
    """Test that ensure_yolo_model_downloaded returns cached model if it exists."""
    model_name = "yolov8n.pt"
    model_path = tmp_models_dir / model_name
    model_path.touch()

    result = ensure_yolo_model_downloaded(model_name, tmp_models_dir)

    assert result == model_path
    assert result.exists()


@patch("common.core.model_downloader.YOLO")
def test_ensure_yolo_model_downloaded_downloads_if_not_cached(
    mock_yolo, tmp_models_dir
):
    """Test that ensure_yolo_model_downloaded downloads model if not cached."""
    model_name = "yolov8n.pt"
    model_path = tmp_models_dir / model_name

    mock_yolo_instance = MagicMock()
    mock_yolo_instance.ckpt_path = str(tmp_models_dir / "downloaded_model.pt")
    mock_yolo.return_value = mock_yolo_instance

    with patch("shutil.copy2") as mock_copy:
        downloaded_path = Path(mock_yolo_instance.ckpt_path)
        downloaded_path.touch()

        result = ensure_yolo_model_downloaded(model_name, tmp_models_dir)

        mock_yolo.assert_called_once_with(model_name)
        mock_copy.assert_called_once_with(str(downloaded_path), str(model_path))
        assert result == model_path


@patch("common.core.model_downloader.YOLO")
@patch("common.core.model_downloader.Path.home")
def test_ensure_yolo_model_downloaded_fallback_to_ultralytics_cache(
    mock_home, mock_yolo, tmp_models_dir
):
    """Test that ensure_yolo_model_downloaded falls back to Ultralytics cache."""
    model_name = "yolov8n.pt"
    model_path = tmp_models_dir / model_name

    mock_yolo_instance = MagicMock()
    mock_yolo_instance.ckpt_path = None
    mock_yolo_instance.weights = None
    mock_yolo.return_value = mock_yolo_instance

    mock_home.return_value = tmp_models_dir
    ultralytics_cache = tmp_models_dir / ".ultralytics" / "weights" / model_name
    ultralytics_cache.parent.mkdir(parents=True)
    ultralytics_cache.touch()

    with patch("shutil.copy2") as mock_copy:
        result = ensure_yolo_model_downloaded(model_name, tmp_models_dir)

        mock_copy.assert_called_once_with(str(ultralytics_cache), str(model_path))
        assert result == model_path


@patch("builtins.__import__")
def test_ensure_midas_model_available_sets_cache_directory(mock_import, tmp_path):
    """Test that ensure_midas_model_available sets PyTorch Hub cache directory."""
    cache_dir = tmp_path / "midas_cache"

    mock_torch = MagicMock()
    mock_torch.hub.load.return_value = MagicMock()

    def import_side_effect(name, *args, **kwargs):
        if name == "torch":
            return mock_torch
        return __import__(name, *args, **kwargs)

    mock_import.side_effect = import_side_effect

    ensure_midas_model_available(cache_directory=cache_dir)

    mock_torch.hub.set_dir.assert_called_once_with(str(cache_dir))
    mock_torch.hub.load.assert_called_once_with(
        "intel-isl/MiDaS", "MiDaS_small", trust_repo=True
    )


@patch("builtins.__import__")
def test_ensure_midas_model_available_handles_errors_gracefully(mock_import, tmp_path):
    """Test that ensure_midas_model_available handles download errors gracefully."""
    cache_dir = tmp_path / "midas_cache"

    mock_torch = MagicMock()
    mock_torch.hub.load.side_effect = Exception("Network error")

    def import_side_effect(name, *args, **kwargs):
        if name == "torch":
            return mock_torch
        return __import__(name, *args, **kwargs)

    mock_import.side_effect = import_side_effect

    ensure_midas_model_available(cache_directory=cache_dir)

    mock_torch.hub.set_dir.assert_called_once_with(str(cache_dir))
    mock_torch.hub.load.assert_called_once()


def test_ensure_yolo_model_downloaded_creates_cache_directory(tmp_path):
    """Test that ensure_yolo_model_downloaded creates cache directory if it doesn't exist."""
    model_name = "yolov8n.pt"
    cache_dir = tmp_path / "new_models_dir"
    model_path = cache_dir / model_name

    with patch("common.core.model_downloader.YOLO") as mock_yolo:
        mock_yolo_instance = MagicMock()
        mock_yolo_instance.ckpt_path = None
        mock_yolo_instance.weights = None
        mock_yolo.return_value = mock_yolo_instance

        with patch("shutil.copy2"):
            with patch("common.core.model_downloader.Path.home") as mock_home:
                mock_home.return_value = tmp_path
                ultralytics_cache = tmp_path / ".ultralytics" / "weights" / model_name
                ultralytics_cache.parent.mkdir(parents=True)
                ultralytics_cache.touch()

                result = ensure_yolo_model_downloaded(model_name, cache_dir)

                assert cache_dir.exists()
                assert result == model_path
