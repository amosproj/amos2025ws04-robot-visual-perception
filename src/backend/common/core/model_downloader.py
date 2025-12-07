# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import logging
import shutil
from pathlib import Path
from typing import Optional

from ultralytics import YOLO  # type: ignore[import-untyped]
import torch

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL_DIR = Path("models")
DEFAULT_MIDAS_MODEL = "MiDaS_small"
DEFAULT_MIDAS_REPO = "intel-isl/MiDaS"
PYTORCH_HUB_CACHE = Path.home() / ".cache" / "torch" / "hub"
ULTRALYTICS_CACHE = Path.home() / ".ultralytics" / "weights"


def _copy_model_file(source: Path, destination: Path) -> None:
    """Copy a model file from source to destination with error handling."""
    try:
        shutil.copy2(str(source), str(destination))
        logger.info(f"Model copied from {source} to {destination}")
    except (IOError, OSError) as e:
        logger.error(f"Failed to copy model from {source} to {destination}: {e}")
        raise


def ensure_yolo_model_downloaded(
    model_name: str = "yolov8n.pt",
    cache_directory: Optional[Path] = None,
) -> Path:
    """Ensure YOLO model is downloaded and cached locally.

    Args:
        model_name: Name of the YOLO model to download (e.g., "yolov8n.pt").
        cache_directory: Directory where models should be cached. If None,
            uses "models" directory in the current working directory.

    Returns:
        Path to the cached model file.
    """
    cache_dir = Path(cache_directory) if cache_directory else DEFAULT_MODEL_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_path = cache_dir / model_name

    if model_path.exists():
        logger.debug(f"Using cached YOLO model at {model_path}")
        return model_path

    logger.info(f"Downloading YOLO model {model_name} to {model_path}...")
    try:
        yolo_instance = YOLO(model_name)
        downloaded_path = getattr(yolo_instance, "ckpt_path", None) or getattr(
            yolo_instance, "weights", None
        )

        if (
            downloaded_path
            and (downloaded_path := Path(downloaded_path)).exists()
            and downloaded_path != model_path
        ):
            _copy_model_file(downloaded_path, model_path)
            return model_path

        # Fallback to default cache location
        default_cache = ULTRALYTICS_CACHE / model_name
        if default_cache.exists():
            _copy_model_file(default_cache, model_path)
            return model_path

        raise FileNotFoundError(
            f"Could not locate downloaded YOLO model. "
            f"Checked: {downloaded_path}, {default_cache}"
        )

    except Exception as e:
        logger.error(f"Failed to download YOLO model: {e}")
        raise RuntimeError(f"Failed to download YOLO model: {e}") from e


def get_midas_cache_directory(custom_cache_path: Optional[Path] = None) -> Path:
    """Get the directory where MiDaS models are cached.

    Args:
        custom_cache_path: Custom directory for MiDaS model cache. If None,
            uses the default PyTorch Hub cache location.

    Returns:
        Path to the MiDaS model cache directory.
    """
    if custom_cache_path is not None:
        cache_path = Path(custom_cache_path)
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path
    return PYTORCH_HUB_CACHE


def ensure_midas_model_available(
    model_type: str = DEFAULT_MIDAS_MODEL,
    midas_repo: str = DEFAULT_MIDAS_REPO,
    cache_directory: Optional[Path] = None,
) -> bool:
    """Ensure MiDaS model is downloaded and cached.

    Args:
        model_type: Type of MiDaS model ("MiDaS_small", "DPT_Hybrid", "DPT_Large").
        midas_repo: Repository identifier for the MiDaS model.
        cache_directory: Custom cache directory. If None, uses PyTorch Hub's
            default cache location.

    Returns:
        bool: True if model is available, False otherwise.

    Note:
        This function loads the model to trigger download, but doesn't return it.
        The actual model loading should be done in DistanceEstimator to avoid
        loading models twice.
    """
    cache_dir = cache_directory or get_midas_cache_directory()
    logger.info(f"Ensuring MiDaS model {model_type} is available in {cache_dir}...")

    try:
        torch.hub.set_dir(str(cache_dir))
        torch.hub.load(midas_repo, model_type, trust_repo=True)
        logger.info(f"MiDaS model {model_type} is cached and ready")
        return True
    except Exception as e:
        logger.warning(f"Could not pre-load MiDaS model: {e}")
        logger.info("Model will be downloaded on first use")
        return False
