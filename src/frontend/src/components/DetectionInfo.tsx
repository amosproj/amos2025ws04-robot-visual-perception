/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

export interface Detection {
  id: string;
  label: string;
  confidence: number;
  distance?: number;
}

export interface DetectionInfoProps {
  detections: Detection[];
}

export default function DetectionInfo({ detections }: DetectionInfoProps) {
  if (!detections || detections.length === 0) {
    return null;
  }

  return (
    <div className="detection-info">
      <h3>Latest Detections ({detections.length})</h3>
      <div className="detection-list">
        {detections.map((detection) => (
          <div key={detection.id} className="detection-item">
            <span className="detection-label">{detection.label}</span>
            <span className="detection-confidence">
              {(detection.confidence * 100).toFixed(1)}%
            </span>
            {detection.distance && (
              <span className="detection-distance">
                {detection.distance.toFixed(2)}m
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
