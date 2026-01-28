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
    import onnx
except ImportError:
    onnx = None  # type: ignore

try:
    from onnxruntime.transformers.float16 import convert_float_to_float16 # type: ignore[import-untyped]

    HAS_ONNX_QUANTIZATION = True
except ImportError:
    convert_float_to_float16 = None  # type: ignore
    HAS_ONNX_QUANTIZATION = False


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


# Ops that don't work well with FP16 on cpu (can be removed if on gpu)
FP16_OP_BLOCK_LIST = [
    "Resize",
    "Upsample",
]


def quantize_onnx_dynamic(model_path: Path) -> None:
    """Convert ONNX model to FP16 (mixed precision) in-place.

    Uses ONNX Runtime's float16 converter which properly handles:
    - Keeping inputs/outputs as FP32 for compatibility
    - Blocking problematic ops (Resize, Upsample) from FP16 conversion
    - Inserting Cast nodes where needed

    This provides ~50% model size reduction while maintaining CPU compatibility.

    Args:
        model_path: Path to the ONNX model to convert

    Raises:
        RuntimeError: If onnxruntime.transformers is not available
    """
    if not HAS_ONNX_QUANTIZATION or not onnx:
        raise RuntimeError("onnx, onnxruntime are required for FP16 conversion. ")

    logger.info("Converting ONNX model to FP16 (mixed precision)...")

    model = onnx.load(str(model_path))

    model_fp16 = convert_float_to_float16(
        model,
        keep_io_types=True,
        op_block_list=FP16_OP_BLOCK_LIST,
    )

    onnx.save(model_fp16, str(model_path))
    logger.info("FP16 conversion complete: %s", model_path)


def export_yolo_to_onnx(
    yolo_path: Path,
    output_path: Path,
    opset: int = 18,
    imgsz: int = 640,
    simplify: bool = True,
    half: bool = False,
) -> Path:
    """Export YOLO model to ONNX format.

    Args:
        yolo_path: Path to the .pt model file
        output_path: Path where the .onnx model should be saved
        opset: ONNX opset version
        imgsz: Image size
        simplify: Whether to run ONNX simplifier
        half: Apply INT8 quantization for smaller model size (better than FP16 for CPU)

    Returns:
        Path to the exported ONNX model
    """
    logger.info("Exporting YOLO model to ONNX (quantize=%s)...", half)
    try:
        if not yolo_path.exists():
            raise FileNotFoundError(f"YOLO model not found at {yolo_path}")

        model = YOLO(str(yolo_path))

        # Export to ONNX in FP32 first
        exported_filename = model.export(
            format="onnx",
            opset=opset,
            imgsz=imgsz,
            simplify=simplify,
            half=False,
        )

        exported_path = Path(exported_filename).resolve()

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if exported_path != output_path:
            shutil.move(str(exported_path), str(output_path))
            logger.info("Moved exported YOLO model to %s", output_path)

        # Apply INT8 quantization if requested (replaces old FP16 conversion)
        if half:
            quantize_onnx_dynamic(output_path)

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
    half: bool = False,
) -> Path:
    """Export MiDaS model to ONNX format.

    Args:
        cache_dir: Directory with cached model
        output_path: File path to save ONNX model
        model_type: Type of MiDaS model
        model_repo: Repo
        opset: ONNX opset version
        input_size: Optional manual input size override
        half: Apply INT8 quantization for smaller model size (better than FP16 for CPU)

    Returns:
        Path to the exported ONNX model
    """
    logger.info("Exporting %s model to ONNX (quantize=%s)...", model_type, half)
    try:
        torch.hub.set_dir(str(cache_dir))
        model = torch.hub.load(model_repo, model_type, trust_repo=True)
        model.eval()

        # Always export in FP32 first, then quantize post-export
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

        # Apply INT8 quantization if requested (replaces old FP16 conversion)
        if half:
            quantize_onnx_dynamic(output_path)

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
