# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
"""Model management module for downloading and exporting ML models."""

import logging
import shutil
from pathlib import Path
from typing import Optional

import torch
from ultralytics import YOLO  # type: ignore[import-untyped]

try:
    from transformers import (  # type: ignore[import-untyped]
        AutoImageProcessor,
        AutoModelForDepthEstimation,
    )
except ImportError:
    AutoImageProcessor = None  # type: ignore
    AutoModelForDepthEstimation = None  # type: ignore

try:
    import depth_pro  # type: ignore
except ImportError:
    depth_pro = None

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MIDAS_MODEL = "MiDaS_small"
DEFAULT_MIDAS_REPO = "intel-isl/MiDaS"
PYTORCH_HUB_CACHE = Path.home() / ".cache" / "torch" / "hub"


def ensure_yolo_model_downloaded(
    model_name: str = "yolo11n.pt",
    cache_dir: Optional[Path] = None,
) -> Path:
    """Ensure YOLO model is downloaded and cached.

    Args:
        model_name: Name of the YOLO model file (e.g., 'yolo11n.pt')
        cache_dir: Directory to save the model to

    Returns:
        Path to the downloaded model file

    Raises:
        RuntimeError: If model download fails
    """
    if cache_dir is None:
        cache_dir = Path.cwd() / "models"

    cache_dir = Path(str(cache_dir)).resolve()
    model_path = cache_dir / model_name

    # Create parent directories if they don't exist
    model_path.parent.mkdir(parents=True, exist_ok=True)

    if model_path.exists():
        logger.info("Using cached YOLO model at %s", model_path)
        return model_path

    logger.info("Downloading YOLO model %s to %s...", model_name, model_path)

    try:
        # Download the model using Ultralytics YOLO
        # We load it, which triggers a download if not found locally or in cwd
        model = YOLO(model_name)

        # If the model was downloaded to CWD or some other default location,
        # we need to save it to our target location.
        # Ultralytics usually caches in ./ or ~/.config/Ultralytics/
        # We can force save it to our desired path.
        if hasattr(model, "ckpt_path") and model.ckpt_path:
            source_path = Path(model.ckpt_path)
            if source_path != model_path:
                shutil.copy2(source_path, model_path)
                logger.info("Copied YOLO model to %s", model_path)
        else:
            # Fallback: save state dict or use save method
            model.save(str(model_path))
            logger.info("Saved YOLO model to %s", model_path)

        return model_path

    except Exception as e:
        error_msg = f"Failed to download YOLO model {model_name}: {e}"
        logger.error(error_msg)
        if model_path.exists():
            try:
                model_path.unlink()
            except OSError:
                pass
        raise RuntimeError(error_msg) from e


def export_yolo_to_onnx(
    yolo_path: Path,
    output_path: Path,
    opset: int = 18,
    imgsz: int = 640,
    simplify: bool = True,
) -> Path:
    """Export YOLO model to ONNX format.

    Args:
        yolo_path: Path to the .pt model file
        output_path: Path where the .onnx model should be saved
        opset: ONNX opset version
        imgsz: Image size
        simplify: Whether to run ONNX simplifier

    Returns:
        Path to the exported ONNX model
    """
    logger.info("Exporting YOLO model to ONNX...")
    try:
        if not yolo_path.exists():
            raise FileNotFoundError(f"YOLO model not found at {yolo_path}")

        model = YOLO(str(yolo_path))

        # Ultralytics export saves to the same directory as the source model by default
        # or we can specify 'project' and 'name' but it creates subdirs.
        # Easiest is to let it export, then move if needed.
        exported_filename = model.export(
            format="onnx",
            opset=opset,
            imgsz=imgsz,
            simplify=simplify,
        )

        exported_path = Path(exported_filename).resolve()

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if exported_path != output_path:
            shutil.move(str(exported_path), str(output_path))
            logger.info("Moved exported YOLO model to %s", output_path)
        else:
            logger.info("YOLO ONNX model ready at: %s", output_path)

        return output_path

    except Exception as e:
        logger.error("Failed to export YOLO to ONNX: %s", e)
        raise RuntimeError(f"YOLO export failed: {e}") from e


def get_midas_cache_dir(custom_path: Optional[Path] = None) -> Path:
    """Get the directory where MiDaS models are cached."""
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
        cache_dir: Custom cache directory

    Returns:
        Path to the model cache directory
    """
    cache_dir = get_midas_cache_dir(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(
            "Downloading %s model from %s to %s...", model_type, midas_repo, cache_dir
        )
        torch.hub.set_dir(str(cache_dir))

        # This triggers download if not present
        model = torch.hub.load(midas_repo, model_type, trust_repo=True)
        model.eval()

        logger.info("%s model is cached and ready in %s", model_type, cache_dir)
        return cache_dir
    except Exception as e:
        error_msg = f"Failed to load {model_type} model from {midas_repo}: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def get_midas_onnx_config(model_type: str) -> tuple[int, str]:
    """Get input size and default filename for MiDaS models."""
    config_map = {
        "MiDaS_small": (256, "midas_small.onnx"),
        "DPT_Hybrid": (384, "dpt_hybrid.onnx"),
        "DPT_Large": (384, "dpt_large.onnx"),
    }
    # Default to 256 for basic midas if unknown, preserving old behavior or just 384
    return config_map.get(model_type, (384, f"{model_type.lower()}.onnx"))


def export_midas_to_onnx(
    cache_dir: Path,
    output_path: Path,
    model_type: str = "MiDaS_small",
    model_repo: str = "intel-isl/MiDaS",
    opset: int = 18,
    input_size: Optional[int] = None,
) -> Path:
    """Export MiDaS model to ONNX format.

    Args:
        cache_dir: Directory with cached model
        output_path: File path to save ONNX model
        model_type: Type of MiDaS model
        model_repo: Repo
        opset: ONNX opset version
        input_size: Optional manual input size override

    Returns:
        Path to the exported ONNX model
    """
    logger.info("Exporting %s model to ONNX...", model_type)
    try:
        torch.hub.set_dir(str(cache_dir))
        model = torch.hub.load(model_repo, model_type, trust_repo=True)
        model.eval()

        default_size, _ = get_midas_onnx_config(model_type)
        size = input_size if input_size else default_size

        output_path.parent.mkdir(parents=True, exist_ok=True)

        dummy_input = torch.randn(1, 3, size, size)

        torch.onnx.export(
            model,
            (dummy_input,),
            str(output_path),
            export_params=True,
            opset_version=opset,
            do_constant_folding=True,
            input_names=["input"],
            output_names=["output"],
        )

        logger.info("%s ONNX model ready at: %s", model_type, output_path)
        return output_path
    except Exception as e:
        logger.error("Failed to export %s to ONNX: %s", model_type, e)
        raise RuntimeError(f"MiDaS export failed: {e}") from e


def ensure_depth_anything_model_available(
    model_name: str,
    cache_dir: Optional[Path] = None,
) -> Path:
    """Ensure Depth Anything V2 model is downloaded and cached.

    Args:
        model_name: Hugging Face model identifier
        cache_dir: custom cache directory

    Returns:
        Path to the model cache directory
    """
    if cache_dir is None:
        # Default HF cache is usually ~/.cache/huggingface, but we can respect our config default if passed
        cache_dir = Path.home() / ".cache" / "huggingface"

    cache_dir = Path(str(cache_dir)).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading/Verifying Depth Anything model %s...", model_name)
    logger.info("Cache dir: %s", cache_dir)

    try:
        if AutoImageProcessor is None or AutoModelForDepthEstimation is None:
            raise ImportError(
                "transformers not installed. "
                "Please run `uv sync --extra inference` or install `transformers`."
            )
        # These calls trigger download or load from cache
        AutoImageProcessor.from_pretrained(model_name, cache_dir=cache_dir)
        AutoModelForDepthEstimation.from_pretrained(model_name, cache_dir=cache_dir)

        logger.info("Depth Anything model is ready.")
        return cache_dir
    except Exception as e:
        error_msg = f"Failed to load Depth Anything model {model_name}: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def ensure_depth_pro_model_available(
    cache_dir: Optional[Path] = None,
) -> Path:
    """Ensure Depth Pro model is downloaded and cached.

    This function initializes the model once to trigger any internal downloads
    or verifications provided by the 'depth_pro' library.

    Args:
        cache_dir: Directory to cache the model (if applicable/supported by depth_pro)

    Returns:
        Path where the model is expected to be (or just a success confirmation)
    """
    if cache_dir is None:
        cache_dir = (
            Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
        )  # Default guess or config

    # Ensure import
    if depth_pro is None:
        raise ImportError(
            "depth_pro is not available. Please install it via `uv sync --extra inference`"
        )

    try:
        # Define expected checkpoint path
        # depth_pro expects 'checkpoints/depth_pro.pt' by default relative to CWD?
        # actually it looks for config.checkpoint_uri which defaults to that.
        # We should set it or place the file there.

        # NOTE: depth_pro implementation detail:
        # It usually looks for `checkpoints/depth_pro.pt` in the current working directory.
        # We can try to rely on that or see if we can trick it.
        # However, it works best if we download it to a known location and maybe symlink or move it,
        # OR if we can pass the path to `create_model_and_transforms`.
        # Checking depth_pro source (passed context): `load(config.checkpoint_uri)`
        # `config` is imported from `depth_pro`.

        # Let's download to our cache dir first.

        cache_dir = Path(str(cache_dir)).resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_name = "depth_pro.pt"
        checkpoint_path = cache_dir / checkpoint_name

        url = "https://ml-site.cdn-apple.com/models/depth-pro/depth_pro.pt"

        if not checkpoint_path.exists():
            logger.info("Downloading Depth Pro weights to %s...", checkpoint_path)
            torch.hub.download_url_to_file(url, str(checkpoint_path), progress=True)
        else:
            logger.info("Depth Pro weights found at %s", checkpoint_path)

        # Now we need to tell depth_pro where the file is.
        # Since we can't easily patch the config before import if it's already imported,
        # we might need to modify `depth_pro.depth_pro.config.checkpoint_uri`?
        # Or just symlink it to ./checkpoints/depth_pro.pt in the run directory?
        #
        # Let's try to set the config if exposed.
        # Based on typical python modules:
        # import depth_pro.config as dp_config ? or depth_pro.depth_pro.config?
        #
        # A safer bet for now (without deep diving into their config struct) is
        # to ensure the file exists at `./checkpoints/depth_pro.pt` relative to CWD.

        cwd_checkpoints = Path.cwd() / "checkpoints"
        cwd_checkpoints.mkdir(exist_ok=True)
        cwd_target = cwd_checkpoints / "depth_pro.pt"

        if not cwd_target.exists():
            # Symlink or copy
            try:
                cwd_target.symlink_to(checkpoint_path)
                logger.info("Symlinked checkpoint to %s", cwd_target)
            except OSError:
                # Fallback to copy if symlink fails (e.g. windows without privs)
                shutil.copy2(checkpoint_path, cwd_target)
                logger.info("Copied checkpoint to %s", cwd_target)

        # Now instantiate
        depth_pro.create_model_and_transforms()

        logger.info("Depth Pro model is ready.")
        return cache_dir
    except Exception as e:
        logger.error(f"Failed to load Depth Pro model: {e}")
        raise RuntimeError(f"Depth Pro initialization failed: {e}") from e
