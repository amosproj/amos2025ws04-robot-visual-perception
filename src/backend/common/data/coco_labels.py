# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
"""COCO label utilities for converting class IDs to human-readable text."""

from __future__ import annotations

COCO_LABELS: list[str] = [
    "Person",
    "Bicycle",
    "Car",
    "Motorcycle",
    "Airplane",
    "Bus",
    "Train",
    "Truck",
    "Boat",
    "Traffic light",
    "Fire hydrant",
    "Stop sign",
    "Parking meter",
    "Bench",
    "Bird",
    "Cat",
    "Dog",
    "Horse",
    "Sheep",
    "Cow",
    "Elephant",
    "Bear",
    "Zebra",
    "Giraffe",
    "Backpack",
    "Umbrella",
    "Handbag",
    "Tie",
    "Suitcase",
    "Frisbee",
    "Skis",
    "Snowboard",
    "Sports ball",
    "Kite",
    "Baseball bat",
    "Baseball glove",
    "Skateboard",
    "Surfboard",
    "Tennis racket",
    "Bottle",
    "Wine glass",
    "Cup",
    "Fork",
    "Knife",
    "Spoon",
    "Bowl",
    "Banana",
    "Apple",
    "Sandwich",
    "Orange",
    "Broccoli",
    "Carrot",
    "Hot dog",
    "Pizza",
    "Donut",
    "Cake",
    "Chair",
    "Couch",
    "Potted plant",
    "Bed",
    "Dining table",
    "Toilet",
    "TV",
    "Laptop",
    "Mouse",
    "Remote",
    "Keyboard",
    "Cell phone",
    "Microwave",
    "Oven",
    "Toaster",
    "Sink",
    "Refrigerator",
    "Book",
    "Clock",
    "Vase",
    "Scissors",
    "Teddy bear",
    "Hair drier",
    "Toothbrush",
]


def get_coco_label(class_id: int | str) -> str:
    """Return human-readable label for a COCO class ID."""
    try:
        idx = int(class_id)
    except (TypeError, ValueError):
        return f"Unknown ({class_id})"

    if idx < 0 or idx >= len(COCO_LABELS):
        return f"Unknown ({class_id})"

    return COCO_LABELS[idx]
