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
    """Safely copy a file with error handling."""
    try:
        shutil.copy2(str(source), str(dest))
        logger.debug("Copied %s to %s", source, dest)
    except OSError as e:
        logger.error("Failed to copy %s to %s: %s", source, dest, e)
        raise


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
    """
    cache_dir = cache_dir or DEFAULT_MODEL_DIR
    model_path = cache_dir / model_name

    if model_path.exists():
        logger.debug("Using cached YOLO model at %s", model_path)
        return model_path

    logger.info("Downloading YOLO model %s...", model_name)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        model = YOLO(f"{model_name.split('.')[0]}.yaml")
        model = YOLO(model_name)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), model_path)
        return model_path
    except Exception as e:
        logger.error("Failed to download YOLO model: %s", e)
        raise


def get_midas_cache_dir(custom_path: Optional[Path] = None) -> Path:
    """Get MiDaS model cache directory."""
    if custom_path:
        return custom_path.expanduser().resolve()
    return PYTORCH_HUB_CACHE


def ensure_midas_model_available(
    cache_dir: Optional[Path] = None,
) -> Path:
    """Ensure MiDaS model is downloaded and cached.

    Args:
        cache_dir: Custom cache directory (default: ~/.cache/torch/hub)

    Returns:
        Path to the model cache directory
    """
    cache_dir = get_midas_cache_dir(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        torch.hub.set_dir(str(cache_dir))
        torch.hub.load(DEFAULT_MIDAS_REPO, DEFAULT_MIDAS_MODEL, trust_repo=True)
        return cache_dir
    except Exception as e:
        logger.error("Failed to load MiDaS model: %s", e)
        raise RuntimeError(f"Failed to download MiDaS model: {e}") from e


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
