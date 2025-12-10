# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
"""Export a YOLO model to ONNX with a safer default opset (18).

Environment variables:
    MODEL_PATH: path to the source .pt model (default: models/yolov8n.pt)
    ONNX_MODEL_PATH: output path (default: MODEL_PATH with .onnx suffix)
    DETECTOR_IMAGE_SIZE: image size used for export (default: 640)
    ONNX_OPSET: ONNX opset version (default: 18)
    ONNX_SIMPLIFY: simplify the exported graph (default: true; set to false to disable)
"""

from __future__ import annotations

import os
from pathlib import Path

from ultralytics import YOLO  # type: ignore[import-untyped]
import torch
import onnx
import onnxslim
from ultralytics.nn.modules import C2f, Classify, Detect, RTDETRDecoder

def _str_to_bool(value: str) -> bool:
    return value.lower() not in {"false", "0", "no", "off", ""}


def main() -> None:
    model_path = Path(os.getenv("MODEL_PATH", "models/yolov8n.pt")).resolve()
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

    # exported_path = model.export(
    #     format="onnx",
    #     opset=22,
    #     imgsz=imgsz,
    #     simplify=simplify,
    #     half=True,
    #     device=0,
    # )

    model = model.model
    for p in model.parameters():
        p.requires_grad = False
    model.eval()
    model.float()
    model = model.fuse()

    for m in model.modules():
        if isinstance(m, Classify):
            m.export = True
        if isinstance(m, (Detect, RTDETRDecoder)):  # includes all Detect subclasses like Segment, Pose, OBB
            m.export = True
            m.format = "onnx"
            # m.max_det = self.args.max_det
        elif isinstance(m, C2f):
            # EdgeTPU does not support FlexSplitV while split provides cleaner ONNX graph
            m.forward = m.forward_split

    

    # model = model.half()
    dummy_input = torch.zeros(1, 3, 640, 640, requires_grad=False)

    y = None
    for _ in range(2):
        y = model(dummy_input)  # dry runs

    model = model # .half()
    dummy_input = dummy_input # .half()

    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        opset_version=opset,
        input_names=["images"],
        output_names=["output0"],
        do_constant_folding=True,
        # dynamic_axes={
        #     "input": {0: "batch", 2: "height", 3: "width"},
        #     "output": {0: "batch", 1: "height", 2: "width"},
        # },
    )

    model_onnx = onnx.load(onnx_path)  # load onnx model
    model_onnx = onnxslim.slim(model_onnx)
    onnx.save(model_onnx, onnx_path)


    # exported_path = Path(exported_path).resolve()
    # if exported_path != onnx_path:
    #     onnx_path.parent.mkdir(parents=True, exist_ok=True)
    #     exported_path.replace(onnx_path)
    #     print(f"Moved exported model to {onnx_path}")
    # else:
    #     print(f"Exported ONNX model to {onnx_path}")


if __name__ == "__main__":  # pragma: no cover - thin wrapper
    main()
