# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
"""Download YOLO and MiDaS models for the analyzer service."""
import argparse
import sys
from pathlib import Path

script_dir = Path(__file__).parent.resolve()
project_root = script_dir.parent
backend_path = project_root / "src" / "backend"

if Path.cwd().name == "backend" and (Path.cwd() / "common").exists():
    backend_path = Path.cwd()

sys.path.insert(0, str(backend_path))

from common.core.model_downloader import (
    ensure_midas_model_available,
    ensure_yolo_model_downloaded,
)


def main() -> None:
    """Download YOLO and MiDaS models."""
    parser = argparse.ArgumentParser(description="Download YOLO and MiDaS models")
    parser.add_argument(
        "--onnx",
        action="store_true",
        help="Export YOLO and MiDaS models to ONNX format after downloading",
    )
    args = parser.parse_args()

    models_dir = backend_path / "models"
    yolo_model_path = models_dir / "yolov8n.pt"
    midas_cache_dir = models_dir / "midas_cache"

    print("Downloading YOLO model...")
    try:
        yolo_path = ensure_yolo_model_downloaded(
            model_name="yolov8n.pt",
            cache_directory=models_dir,
        )
        print(f"YOLO model ready at: {yolo_path}")

        if args.onnx:
            print("Exporting YOLO model to ONNX...")
            from ultralytics import YOLO  # type: ignore[import-untyped]

            model = YOLO(str(yolo_path))
            onnx_path = models_dir / "yolov8n.onnx"
            exported_path = model.export(format="onnx", opset=18, imgsz=640, simplify=True)
            exported_path = Path(exported_path).resolve()
            if exported_path != onnx_path:
                onnx_path.parent.mkdir(parents=True, exist_ok=True)
                exported_path.replace(onnx_path)
            print(f"ONNX model ready at: {onnx_path}")
    except Exception as e:
        print(f"Failed to download YOLO model: {e}")
        sys.exit(1)

    print("Downloading MiDaS model...")
    midas_success = ensure_midas_model_available(cache_directory=midas_cache_dir)
    if not midas_success:
        print("Failed to download MiDaS model")
        sys.exit(1)
    print(f"MiDaS model cached in: {midas_cache_dir}")

    if args.onnx:
        print("Exporting MiDaS model to ONNX...")
        try:
            import torch

            if midas_cache_dir is not None:
                torch.hub.set_dir(str(midas_cache_dir))

            model = torch.hub.load("intel-isl/MiDaS", "MiDaS_small", trust_repo=True)
            model.eval()

            dummy_input = torch.randn(1, 3, 384, 384)
            onnx_path = models_dir / "midas_small.onnx"
            torch.onnx.export(
                model,
                dummy_input,
                str(onnx_path),
                export_params=True,
                opset_version=11,
                do_constant_folding=True,
                input_names=["input"],
                output_names=["output"],
                dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
            )
            print(f"MiDaS ONNX model ready at: {onnx_path}")
        except Exception as e:
            print(f"Failed to export MiDaS to ONNX: {e}")
            sys.exit(1)

    print("All models downloaded successfully.")
    print(f"YOLO model: {yolo_model_path}")
    if args.onnx:
        print(f"YOLO ONNX model: {models_dir / 'yolov8n.onnx'}")
        print(f"MiDaS ONNX model: {models_dir / 'midas_small.onnx'}")
    print(f"MiDaS cache: {midas_cache_dir}")


if __name__ == "__main__":
    main()

