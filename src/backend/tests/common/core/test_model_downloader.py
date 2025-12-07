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


@pytest.fixture
def mock_yolo():
    """Mock YOLO model."""
    with patch("common.core.model_downloader.YOLO") as mock_yolo_cls:
        mock_model = MagicMock()
        mock_yolo_cls.return_value = mock_model
        mock_model.ckpt_path = "/tmp/yolov8n.pt"
        mock_model.weights = "/tmp/yolov8n.pt"
        yield mock_model


@pytest.fixture
def mock_torch():
    """Mock torch for MiDaS model loading."""
    with patch("common.core.model_downloader.torch") as mock_torch:
        mock_torch.hub.load.return_value = MagicMock()
        yield mock_torch


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


def test_ensure_midas_model_available_sets_cache_directory(tmp_path, mock_torch):
    """Test that ensure_midas_model_available sets PyTorch Hub cache directory."""
    cache_dir = tmp_path / "midas_cache"

    # Call the function
    ensure_midas_model_available(cache_directory=cache_dir)

    # Verify the results
    mock_torch.hub.set_dir.assert_called_once_with(str(cache_dir))
    mock_torch.hub.load.assert_called_once_with(
        "intel-isl/MiDaS", "MiDaS_small", trust_repo=True
    )


def test_ensure_midas_model_available_handles_errors_gracefully(tmp_path, mock_torch):
    """Test that ensure_midas_model_available handles download errors gracefully."""
    cache_dir = tmp_path / "midas_cache"

    # Make the hub.load raise an exception
    mock_torch.hub.load.side_effect = Exception("Network error")

    # Call the function and check it handles the error
    result = ensure_midas_model_available(cache_directory=cache_dir)

    # Verify the results
    assert result is False
    mock_torch.hub.set_dir.assert_called_once_with(str(cache_dir))
    mock_torch.hub.load.assert_called_once()


def test_ensure_yolo_model_downloaded_creates_cache_directory(tmp_path, mock_yolo):
    """Test that ensure_yolo_model_downloaded creates cache directory if it doesn't exist."""
    model_name = "yolov8n.pt"
    cache_dir = tmp_path / "new_models_dir"
    model_path = cache_dir / model_name

    with patch("shutil.copy2") as mock_copy:
        # Mock the downloaded file
        downloaded_path = Path("/tmp/yolov8n.pt")
        mock_yolo.return_value.ckpt_path = str(downloaded_path)
        mock_yolo.return_value.weights = str(downloaded_path)

        # Create the downloaded file
        downloaded_path.parent.mkdir(parents=True, exist_ok=True)
        downloaded_path.touch()

        # Call the function
        result = ensure_yolo_model_downloaded(model_name, cache_dir)

        # Verify the results
        assert cache_dir.exists()
        assert result == model_path
        mock_copy.assert_called_once_with(str(downloaded_path), str(model_path))
