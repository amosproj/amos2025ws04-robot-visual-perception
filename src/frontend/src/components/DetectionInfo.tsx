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
    <div className="bg-[#2a2a2a] border border-[#404040] p-5 rounded-lg shadow-[0_4px_20px_rgba(0,0,0,0.4)]">
      <h3 className="my-0 mb-4 text-[#00d4ff] text-xl">
        Latest Detections ({detections.length})
      </h3>
      <div className="flex flex-wrap gap-2.5">
        {detections.map((detection) => (
          <div
            key={detection.id}
            className="flex items-center gap-2 px-3 py-2 bg-[#404040] rounded-md border-l-[3px] border-l-[#00d4ff] border border-[#555]"
          >
            <span className="font-semibold text-[#e0e0e0]">
              {detection.label}
            </span>
            <span className="bg-gradient-to-br from-[#74b9ff] to-[#0984e3] text-white px-2 py-0.5 rounded text-xs font-semibold shadow-[0_2px_4px_rgba(116,185,255,0.3)]">
              {(detection.confidence * 100).toFixed(1)}%
            </span>
            {detection.distance && (
              <span className="bg-gradient-to-br from-[#00d4aa] to-[#00b894] text-white px-2 py-0.5 rounded text-xs font-semibold shadow-[0_2px_4px_rgba(0,212,170,0.3)]">
                {detection.distance.toFixed(2)}m
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
