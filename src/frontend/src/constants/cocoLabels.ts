/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

/**
 * COCO Dataset Class Labels
 *
 * YOLOv8 is trained on the COCO (Common Objects in Context) dataset,
 * which contains 80 object classes. This array maps class IDs (0-79)
 * to human-readable labels.
 *
 * Source: https://github.com/ultralytics/ultralytics
 */
export const COCO_LABELS: string[] = [
  'person',
  'bicycle',
  'car',
  'motorcycle',
  'airplane',
  'bus',
  'train',
  'truck',
  'boat',
  'traffic light',
  'fire hydrant',
  'stop sign',
  'parking meter',
  'bench',
  'bird',
  'cat',
  'dog',
  'horse',
  'sheep',
  'cow',
  'elephant',
  'bear',
  'zebra',
  'giraffe',
  'backpack',
  'umbrella',
  'handbag',
  'tie',
  'suitcase',
  'frisbee',
  'skis',
  'snowboard',
  'sports ball',
  'kite',
  'baseball bat',
  'baseball glove',
  'skateboard',
  'surfboard',
  'tennis racket',
  'bottle',
  'wine glass',
  'cup',
  'fork',
  'knife',
  'spoon',
  'bowl',
  'banana',
  'apple',
  'sandwich',
  'orange',
  'broccoli',
  'carrot',
  'hot dog',
  'pizza',
  'donut',
  'cake',
  'chair',
  'couch',
  'potted plant',
  'bed',
  'dining table',
  'toilet',
  'tv',
  'laptop',
  'mouse',
  'remote',
  'keyboard',
  'cell phone',
  'microwave',
  'oven',
  'toaster',
  'sink',
  'refrigerator',
  'book',
  'clock',
  'vase',
  'scissors',
  'teddy bear',
  'hair drier',
  'toothbrush',
];

/**
 * Get human-readable label for a COCO class ID (capitalized)
 */
export function getCocoLabel(classId: number | string): string {
  const id = typeof classId === 'string' ? parseInt(classId, 10) : classId;
  if (isNaN(id) || id < 0 || id >= COCO_LABELS.length) {
    return `Unknown (${classId})`;
  }
  const label = COCO_LABELS[id];
  return label.charAt(0).toUpperCase() + label.slice(1);
}
