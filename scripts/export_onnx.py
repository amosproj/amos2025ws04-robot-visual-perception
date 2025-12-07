# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
"""Export a YOLO model to ONNX with a safer default opset (18).

Environment variables:
    MODEL_PATH: path to the source .pt model (default: models/yolo11n.pt)
    ONNX_MODEL_PATH: output path (default: MODEL_PATH with .onnx suffix)
    DETECTOR_IMAGE_SIZE: image size used for export (default: 640)
    ONNX_OPSET: ONNX opset version (default: 18)
    ONNX_SIMPLIFY: simplify the exported graph (default: true; set to false to disable)
"""

from __future__ import annotations

import os
from pathlib import Path

from ultralytics import YOLO  # type: ignore[import-untyped]


def _str_to_bool(value: str) -> bool:
    return value.lower() not in {"false", "0", "no", "off", ""}


def main() -> None:
    model_path = Path(os.getenv("MODEL_PATH", "models/yolo11n.pt")).resolve()
    onnx_path = Path(
        os.getenv("ONNX_MODEL_PATH", str(model_path.with_suffix(".onnx")))
    ).resolve()
    opset = int(os.getenv("ONNX_OPSET", "18"))
    imgsz = int(os.getenv("DETECTOR_IMAGE_SIZE", "640"))
    simplify = _str_to_bool(os.getenv("ONNX_SIMPLIFY", "true"))

    if not model_path.exists():
        raise FileNotFoundError(
            f"Source model not found at {model_path}. Set MODEL_PATH to the .pt file."
        )

    model = YOLO(str(model_path))
    exported_path = model.export(
        format="onnx",
        opset=opset,
        imgsz=imgsz,
        simplify=simplify,
    )

    exported_path = Path(exported_path).resolve()
    if exported_path != onnx_path:
        onnx_path.parent.mkdir(parents=True, exist_ok=True)
        exported_path.replace(onnx_path)
        print(f"Moved exported model to {onnx_path}")
    else:
        print(f"Exported ONNX model to {onnx_path}")


if __name__ == "__main__":  # pragma: no cover - thin wrapper
    main()
