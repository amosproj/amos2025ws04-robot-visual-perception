# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
"""Model downloader and cache management for ML models."""
import logging
import shutil
from pathlib import Path
from typing import Optional

import torch
from ultralytics import YOLO  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL_DIR = Path("models")
DEFAULT_MIDAS_MODEL = "MiDaS_small"
DEFAULT_MIDAS_REPO = "intel-isl/MiDaS"
PYTORCH_HUB_CACHE = Path.home() / ".cache" / "torch" / "hub"
ULTRALYTICS_CACHE = Path.home() / ".ultralytics" / "weights"


def _copy_file(source: Path, dest: Path) -> None:
    """Safely copy a file with error handling.

    Args:
        source: Source file path
        dest: Destination file path

    Raises:
        OSError: If file copy fails
    """
    try:
        shutil.copy2(str(source), str(dest))
        logger.debug("Copied %s to %s", source, dest)
    except OSError as e:
        logger.error("Failed to copy %s to %s: %s", source, dest, e)


def ensure_yolo_model_downloaded(
    model_name: str = "yolo11n.pt",
    cache_dir: Optional[Path] = None,
) -> Path:
    """Ensure YOLO model is downloaded and cached.

    Args:
        model_name: Name of the YOLO model file
        cache_dir: Directory to cache the model

    Returns:
        Path to the downloaded model file

    Raises:
        RuntimeError: If model download fails
    """
    cache_dir = cache_dir or DEFAULT_MODEL_DIR
    model_path = cache_dir / model_name

    if model_path.exists():
        logger.debug("Using cached YOLO model at %s", model_path)
        return model_path

    logger.info("Downloading YOLO model %s...", model_name)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        model = YOLO(model_name)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), model_path)
        return model_path
    except Exception as e:
        error_msg = f"Failed to download YOLO model {model_name}: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def get_midas_cache_dir(custom_path: Optional[Path] = None) -> Path:
    """Get the directory where MiDaS models are cached.

    Args:
        custom_path: Custom directory for MiDaS model cache. If None,
            uses the default PyTorch Hub cache location.

    Returns:
        Path to the cache directory
    """
    if custom_path:
        return custom_path.expanduser().resolve()
    return PYTORCH_HUB_CACHE


def ensure_midas_model_available(
    model_type: str = DEFAULT_MIDAS_MODEL,
    midas_repo: str = DEFAULT_MIDAS_REPO,
    cache_dir: Optional[Path] = None,
) -> Path:
    """Ensure MiDaS model is downloaded and cached.

    Args:
        model_type: Type of MiDaS model ("MiDaS_small", "DPT_Hybrid", "DPT_Large")
        midas_repo: Repository identifier for the MiDaS model
        cache_dir: Custom cache directory (default: ~/.cache/torch/hub)

    Returns:
        Path to the model cache directory

    Raises:
        RuntimeError: If model download or loading fails
    """
    cache_dir = get_midas_cache_dir(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info("Downloading %s model from %s...", model_type, midas_repo)
        torch.hub.set_dir(str(cache_dir))
        model = torch.hub.load(midas_repo, model_type, trust_repo=True)
        model.eval()  # Ensure model is in evaluation mode
        logger.info("%s model is cached and ready in %s", model_type, cache_dir)
        return cache_dir
    except Exception as e:
        error_msg = f"Failed to load {model_type} model from {midas_repo}: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
