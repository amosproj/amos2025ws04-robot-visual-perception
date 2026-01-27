# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from common.utils.model_downloader import (
    convert_onnx_to_fp16,
    ensure_midas_model_available,
    ensure_yolo_model_downloaded,
    get_midas_cache_dir,
)

try:
    import onnx
    from onnx import TensorProto, helper, numpy_helper
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False


@pytest.fixture
def tmp_models_dir(tmp_path):
    """Create a temporary models directory for testing."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    return models_dir


@pytest.fixture
def mock_yolo():
    """Mock YOLO model."""
    with patch("common.utils.model_downloader.YOLO") as mock_yolo_cls:
        mock_model = MagicMock()
        mock_yolo_cls.return_value = mock_model
        mock_model.ckpt_path = "/tmp/yolo11n.pt"
        mock_model.weights = "/tmp/yolo118n.pt"
        yield mock_model


@pytest.fixture
def mock_torch():
    """Mock torch for MiDaS model loading."""
    with patch("common.utils.model_downloader.torch") as mock_torch:
        mock_torch.hub.load.return_value = MagicMock()
        yield mock_torch


def test_get_midas_cache_dir_default():
    """Test that get_midas_cache_dir returns default PyTorch cache location."""
    cache_dir = get_midas_cache_dir()
    expected = Path.home() / ".cache" / "torch" / "hub"
    assert cache_dir == expected


def test_get_midas_cache_dir_custom(tmp_path):
    """Test that get_midas_cache_dir uses custom path when provided."""
    custom_path = tmp_path / "custom_cache"
    cache_dir = get_midas_cache_dir(custom_path)
    assert cache_dir == custom_path
    # get_midas_cache_dir does not create the directory, so we don't assert it exists


def test_ensure_yolo_model_downloaded_uses_cached_model(tmp_models_dir):
    """Test that ensure_yolo_model_downloaded returns cached model if it exists."""
    model_name = "yolo11n.pt"
    model_path = tmp_models_dir / model_name
    model_path.touch()

    result = ensure_yolo_model_downloaded(model_name, tmp_models_dir)

    assert result == model_path
    assert result.exists()


@patch("common.utils.model_downloader.YOLO")
def test_ensure_yolo_model_downloaded_downloads_if_not_cached(
    mock_yolo, tmp_models_dir
):
    """Test that ensure_yolo_model_downloaded downloads model if not cached."""
    model_name = "yolo11n.pt"
    model_path = tmp_models_dir / model_name

    mock_yolo_instance = MagicMock()
    mock_yolo_instance.ckpt_path = str(tmp_models_dir / "downloaded_model.pt")
    mock_yolo.return_value = mock_yolo_instance

    with patch("shutil.copy2") as mock_copy:
        downloaded_path = Path(mock_yolo_instance.ckpt_path)
        downloaded_path.touch()

        result = ensure_yolo_model_downloaded(model_name, tmp_models_dir)

        mock_yolo.assert_called_once_with(model_name)
        # The implementation passes Path objects to copy2
        mock_copy.assert_called_once_with(downloaded_path, model_path)
        assert result == model_path


def test_ensure_midas_model_available_sets_cache_directory(tmp_path, mock_torch):
    """Test that ensure_midas_model_available sets PyTorch Hub cache directory."""
    cache_dir = tmp_path / "midas_cache"

    # Call the function
    ensure_midas_model_available(cache_dir=cache_dir)

    # Verify the results
    mock_torch.hub.set_dir.assert_called_once_with(str(cache_dir))
    mock_torch.hub.load.assert_called_once_with(
        "intel-isl/MiDaS", "MiDaS_small", trust_repo=True
    )


def test_ensure_midas_model_available_handles_errors_gracefully(tmp_path, mock_torch):
    """Test that ensure_midas_model_available raises RuntimeError on failure."""
    cache_dir = tmp_path / "midas_cache"

    # Make the hub.load raise an exception
    mock_torch.hub.load.side_effect = Exception("Network error")

    # Call the function and check it raises RuntimeError
    with pytest.raises(RuntimeError):
        ensure_midas_model_available(cache_dir=cache_dir)

    # Verify the results
    mock_torch.hub.set_dir.assert_called_once_with(str(cache_dir))
    mock_torch.hub.load.assert_called_once()


def test_ensure_yolo_model_downloaded_creates_cache_directory(tmp_path, mock_yolo):
    """Test that ensure_yolo_model_downloaded creates cache directory if it doesn't exist."""
    model_name = "yolo11n.pt"
    cache_dir = tmp_path / "new_models_dir"
    model_path = cache_dir / model_name

    with patch("shutil.copy2") as mock_copy:
        # Mock the downloaded file
        downloaded_path = Path("/tmp/yolo11n.pt")
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
        # The implementation passes Path objects to copy2
        mock_copy.assert_called_once_with(downloaded_path, model_path)


@pytest.mark.skipif(not ONNX_AVAILABLE, reason="ONNX not installed")
def test_convert_onnx_to_fp16(tmp_path):
    """Test FP16 conversion reduces model size and converts weights to float16."""
    #  a basic ONNX model with FP32 weights
    weight_data = np.random.randn(100, 100).astype(np.float32)
    weight_tensor = numpy_helper.from_array(weight_data, name="weight")

    input_info = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 100])
    output_info = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 100])

    node = helper.make_node("MatMul", ["input", "weight"], ["output"])
    graph = helper.make_graph([node], "test", [input_info], [output_info], [weight_tensor])
    model = helper.make_model(graph)

    model_path = tmp_path / "model.onnx"
    onnx.save(model, str(model_path))
    fp32_size = model_path.stat().st_size

    convert_onnx_to_fp16(model_path)
    fp16_size = model_path.stat().st_size

    converted = onnx.load(str(model_path))
    converted_weight = numpy_helper.to_array(converted.graph.initializer[0])

    assert converted_weight.dtype == np.float16
    assert fp16_size < fp32_size * 0.6  #  around 50% smaller
    assert converted.graph.input[0].type.tensor_type.elem_type == TensorProto.FLOAT16
