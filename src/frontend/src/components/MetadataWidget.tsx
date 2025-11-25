/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import React from 'react';
import { MetadataFrame, BoundingBox } from './VideoOverlay';

export interface StreamMetadata {
  /** Connection state */
  connectionState: 'idle' | 'connecting' | 'connected' | 'error';
  /** WebRTC connection latency in milliseconds */
  latencyMs?: number;

  /** Video resolution */
  videoResolution?: { width: number; height: number };
  /** Canvas overlay rendering FPS */
  renderFps?: number;
  /** Actual video stream FPS (camera framerate) */
  videoFps?: number;

  /** Network quality - packet loss percentage */
  packetLoss?: number;
  /** Network quality - jitter in milliseconds */
  jitter?: number;
  /** Network quality - bitrate in Mbps */
  bitrate?: number;

  /** Video quality - frames dropped */
  framesDropped?: number;
  /** Video quality - frames received */
  framesReceived?: number;
  /** Video quality - frames decoded */
  framesDecoded?: number;
}

export interface MetadataWidgetProps {
  /** Stream-related metadata (latency, connection, etc.) */
  streamMetadata: StreamMetadata;
  /** Detection metadata from AI backend */
  detectionMetadata?: MetadataFrame;
  /** Optional: custom class name */
  className?: string;
  /** Optional: custom style */
  style?: React.CSSProperties;
  /** Optional: Compact mode (show less details) */
  compact?: boolean;
}

/**
 * MetadataWidget displays relevant stream and object detection information
 *
 * Shows:
 * - Stream Info: Latency, FPS, Resolution, Connection Status
 * - Detection Info: Number of detected objects, their labels, confidence, and distances
 */
export default function MetadataWidget({
  streamMetadata,
  detectionMetadata,
  className = '',
  style,
  compact = false,
}: MetadataWidgetProps) {
  const {
    latencyMs,
    connectionState,
    videoResolution,
    renderFps,
    videoFps,
    packetLoss,
    jitter,
    bitrate,
    framesDropped,
    framesReceived,
    framesDecoded,
  } = streamMetadata;
  const detections = detectionMetadata?.detections || [];

  // Determine status color
  const getStatusColor = (state: string) => {
    if (state === 'connected') return 'text-status-connected';
    if (state === 'connecting') return 'text-status-connecting';
    if (state === 'error') return 'text-status-error';
    return 'text-status-idle';
  };

  // Format timestamp
  const formatTimestamp = (ts?: number) => {
    if (!ts) return 'N/A';
    return new Date(ts).toLocaleTimeString('de-DE', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    });
  };

  return (
    <div
      className={`bg-gray-900 bg-opacity-90 text-white rounded-lg p-4 ${className}`}
      style={style}
    >
      {/* Stream Information Section */}
      <div className="mb-4">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-400 mb-2">
          Video Stream
        </h3>
        <div className="space-y-1 text-sm">
          <div className="flex justify-between items-center">
            <span className="text-gray-300">Status:</span>
            <span className={`font-semibold ${getStatusColor(connectionState)}`}>
              {connectionState.charAt(0).toUpperCase() + connectionState.slice(1)}
            </span>
          </div>

          {connectionState === 'connected' && (
            <>
              <div className="flex justify-between items-center">
                <span className="text-gray-300">Latency:</span>
                <span
                  className={`font-semibold ${
                    latencyMs !== undefined && latencyMs < 100
                      ? 'text-green-400'
                      : 'text-yellow-400'
                  }`}
                >
                  {latencyMs !== undefined ? `${latencyMs} ms` : 'N/A'}
                </span>
              </div>

              {videoResolution && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-300">Resolution:</span>
                  <span className="font-semibold text-blue-400">
                    {videoResolution.width} × {videoResolution.height}
                  </span>
                </div>
              )}

              {videoFps !== undefined && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-300">Camera FPS:</span>
                  <span className="font-semibold text-blue-400">{videoFps}</span>
                </div>
              )}

              {renderFps !== undefined && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-300">Render FPS:</span>
                  <span className="font-semibold text-blue-400">{renderFps}</span>
                </div>
              )}

              {/* Network Quality Metrics */}
              {packetLoss !== undefined && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-300">Packet Loss:</span>
                  <span
                    className={`font-semibold ${
                      packetLoss < 1 ? 'text-green-400' : packetLoss < 5 ? 'text-yellow-400' : 'text-red-400'
                    }`}
                  >
                    {packetLoss.toFixed(2)}%
                  </span>
                </div>
              )}

              {jitter !== undefined && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-300">Jitter:</span>
                  <span className="font-semibold text-purple-400">
                    {jitter.toFixed(1)} ms
                  </span>
                </div>
              )}

              {bitrate !== undefined && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-300">Bitrate:</span>
                  <span className="font-semibold text-cyan-400">
                    {bitrate.toFixed(2)} Mbps
                  </span>
                </div>
              )}

              {/* Video Quality Metrics */}
              {framesDropped !== undefined && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-300">Frames Dropped:</span>
                  <span
                    className={`font-semibold ${
                      framesDropped === 0 ? 'text-green-400' : 'text-yellow-400'
                    }`}
                  >
                    {framesDropped}
                  </span>
                </div>
              )}

              {framesReceived !== undefined && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-300">Frames Received:</span>
                  <span className="font-semibold text-gray-400">
                    {framesReceived}
                  </span>
                </div>
              )}

              {framesDecoded !== undefined && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-300">Frames Decoded:</span>
                  <span className="font-semibold text-gray-400">
                    {framesDecoded}
                  </span>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Detection Information Section */}
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-400 mb-2">
          Object Detection
        </h3>

        {detectionMetadata ? (
          <>
            <div className="space-y-1 text-sm mb-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-300">Objects detected:</span>
                <span className="font-semibold text-green-400">
                  {detections.length}
                </span>
              </div>

              {!compact && (
                <>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300">Frame ID:</span>
                    <span className="font-mono text-xs text-blue-400">
                      {detectionMetadata.frameId}
                    </span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-gray-300">Timestamp:</span>
                    <span className="font-mono text-xs text-blue-400">
                      {formatTimestamp(detectionMetadata.timestamp)}
                    </span>
                  </div>
                </>
              )}
            </div>

            {/* List of detected objects */}
            {detections.length > 0 && (
              <div className="mt-3 space-y-2 max-h-64 overflow-y-auto">
                {detections.map((detection, idx) => (
                  <DetectionItem
                    key={detection.id || idx}
                    detection={detection}
                    compact={compact}
                  />
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="text-sm text-gray-400 italic">
            {connectionState === 'connected'
              ? 'Waiting for detection data...'
              : 'No data available'}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Individual detection item component
 */
function DetectionItem({
  detection,
  compact,
}: {
  detection: BoundingBox;
  compact: boolean;
}) {
  const { label, confidence, distance, position } = detection;

  return (
    <div className="bg-gray-800 bg-opacity-60 rounded p-2 border-l-2 border-green-400">
      <div className="flex justify-between items-start mb-1">
        <span className="font-semibold text-green-300">{label}</span>
        <span className="text-xs text-gray-400">
          {(confidence * 100).toFixed(1)}%
        </span>
      </div>

      {distance !== undefined && (
        <div className="text-sm text-gray-300">
          <span className="text-gray-400">Distance:</span>{' '}
          <span className="font-semibold text-yellow-300">
            {distance.toFixed(2)} m
          </span>
        </div>
      )}

      {!compact && position && (
        <div className="text-xs text-gray-400 mt-1 font-mono">
          Position: ({position.x.toFixed(2)}, {position.y.toFixed(2)},{' '}
          {position.z.toFixed(2)})
        </div>
      )}
    </div>
  );
}
