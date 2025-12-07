# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
from pathlib import Path
from typing import Optional

from ultralytics import YOLO  # type: ignore[import-untyped]


def ensure_yolo_model_downloaded(
    model_name: str = "yolov8n.pt",
    cache_directory: Optional[Path] = None,
) -> Path:
    """Ensure YOLO model is downloaded and cached locally.

    Checks if the model exists in the cache directory. If not, downloads it
    using YOLO's built-in download mechanism. YOLO automatically downloads
    models when you instantiate YOLO(model_name), so we trigger that and
    then copy or reference the downloaded model.

    Args:
        model_name: Name of the YOLO model to download (e.g., "yolov8n.pt").
        cache_directory: Directory where models should be cached. If None,
            uses "models" directory in the current working directory.

    Returns:
        Path to the cached model file.

    Example:
        >>> model_path = ensure_yolo_model_downloaded("yolov8n.pt")
        >>> # Model is now available at model_path
    """
    if cache_directory is None:
        cache_directory = Path("models")
    else:
        cache_directory = Path(cache_directory)

    cache_directory.mkdir(parents=True, exist_ok=True)
    model_path = cache_directory / model_name

    if not model_path.exists():
        print(f"Downloading YOLO model {model_name} to {model_path}...")
        yolo_instance = YOLO(model_name)

        downloaded_path = None
        if hasattr(yolo_instance, "ckpt_path") and yolo_instance.ckpt_path:
            downloaded_path = Path(yolo_instance.ckpt_path)
        elif hasattr(yolo_instance, "weights") and yolo_instance.weights:
            downloaded_path = Path(yolo_instance.weights)

        if (
            downloaded_path
            and downloaded_path.exists()
            and downloaded_path != model_path
        ):
            import shutil

            shutil.copy2(str(downloaded_path), str(model_path))
        else:
            import shutil

            default_cache = Path.home() / ".ultralytics" / "weights" / model_name
            if default_cache.exists():
                shutil.copy2(str(default_cache), str(model_path))
            else:
                raise RuntimeError(
                    f"Could not locate downloaded YOLO model. "
                    f"Expected at {downloaded_path or 'unknown location'}. "
                    f"Please check your network connection and try again."
                )
        print(f"Model downloaded successfully to {model_path}")
    else:
        print(f"Using cached YOLO model at {model_path}")

    return model_path


def get_midas_cache_directory(custom_cache_path: Optional[Path] = None) -> Path:
    """Get the directory where MiDaS models are cached.

    PyTorch Hub caches models in ~/.cache/torch/hub by default. This function
    returns either the custom path or the default PyTorch cache location.

    Args:
        custom_cache_path: Custom directory for MiDaS model cache. If None,
            uses the default PyTorch Hub cache location.

    Returns:
        Path to the MiDaS model cache directory.

    Note:
        PyTorch Hub handles downloading and caching automatically when you call
        torch.hub.load(). This function just returns the cache location for
        reference or when you want to use a custom cache directory.
    """
    if custom_cache_path is not None:
        cache_path = Path(custom_cache_path)
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path

    default_cache = Path.home() / ".cache" / "torch" / "hub"
    return default_cache


def ensure_midas_model_available(
    model_type: str = "MiDaS_small",
    midas_repo: str = "intel-isl/MiDaS",
    cache_directory: Optional[Path] = None,
) -> bool:
    """Ensure MiDaS model is downloaded and cached.

    PyTorch Hub automatically caches models, but this function explicitly
    triggers the download if needed. The model will be cached in the
    PyTorch Hub cache directory.

    Args:
        model_type: Type of MiDaS model ("MiDaS_small", "DPT_Hybrid", "DPT_Large").
        midas_repo: Repository identifier for the MiDaS model.
        cache_directory: Custom cache directory. If None, uses PyTorch Hub's
            default cache location.

    Returns:
        True if model was successfully downloaded/cached, False otherwise.

    Note:
        This function loads the model to trigger download, but doesn't return it.
        The actual model loading should be done in DistanceEstimator to avoid
        loading models twice.
    """
    import torch

    if cache_directory is not None:
        torch.hub.set_dir(str(cache_directory))

    print(f"Ensuring MiDaS model {model_type} is available...")
    try:
        torch.hub.load(midas_repo, model_type, trust_repo=True)
        print(f"MiDaS model {model_type} is cached and ready")
        return True
    except Exception as e:
        print(f"Warning: Could not pre-load MiDaS model: {e}")
        print("Model will be downloaded on first use")
        return False
