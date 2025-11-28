/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

export interface BoundingBox {
  id: string;
  label: string;
  confidence: number;
  box: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  distance?: number;
  position?: {
    x: number;
    y: number;
    z: number;
  };
}

export interface MetadataFrame {
  timestamp: number;
  frameId: number;
  detections: BoundingBox[];
}
