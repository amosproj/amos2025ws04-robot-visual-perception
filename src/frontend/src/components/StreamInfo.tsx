/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { memo } from 'react';

export interface StreamInfoProps {
  videoResolution?: { width: number; height: number };
  packetLoss?: number;
  jitter?: number;
  bitrate?: number;
  framesReceived?: number;
  framesDecoded?: number;
}

function StreamInfo({
  videoResolution,
  packetLoss,
  jitter,
  bitrate,
  framesReceived,
  framesDecoded,
}: StreamInfoProps) {
  return (
    <div className="bg-theme-bg-secondary border border-theme-border-subtle p-5 rounded-lg shadow-card">
      <h3 className="my-0 mb-4 text-theme-accent text-xl">Stream Info</h3>

      <div className="space-y-3">
        {/* Video Resolution */}
        {videoResolution && (
          <InfoRow
            label="Resolution"
            value={`${videoResolution.width} × ${videoResolution.height}`}
            valueClass="text-theme-accent"
          />
        )}

        {/* Network Quality */}
        {(packetLoss !== undefined ||
          jitter !== undefined ||
          bitrate !== undefined) && (
          <>
            <div className="text-theme-text-muted text-xs font-semibold uppercase mt-4 mb-2">
              Network Quality
            </div>

            {packetLoss !== undefined && (
              <InfoRow
                label="Packet Loss"
                value={`${packetLoss.toFixed(2)}%`}
                valueClass={
                  packetLoss < 1
                    ? 'text-theme-success'
                    : packetLoss < 5
                      ? 'text-theme-warning'
                      : 'text-theme-error'
                }
              />
            )}

            {jitter !== undefined && (
              <InfoRow
                label="Jitter"
                value={`${jitter.toFixed(1)} ms`}
                valueClass="text-[#a29bfe]"
              />
            )}

            {bitrate !== undefined && (
              <InfoRow
                label="Bitrate"
                value={`${bitrate.toFixed(2)} Mbps`}
                valueClass="text-theme-accent"
              />
            )}
          </>
        )}

        {/* Video Quality */}
        {(framesReceived !== undefined || framesDecoded !== undefined) && (
          <>
            <div className="text-theme-text-muted text-xs font-semibold uppercase mt-4 mb-2">
              Video Quality
            </div>

            {framesReceived !== undefined && (
              <InfoRow
                label="Frames Received"
                value={framesReceived.toString()}
                valueClass="text-theme-text-muted"
              />
            )}

            {framesDecoded !== undefined && (
              <InfoRow
                label="Frames Decoded"
                value={framesDecoded.toString()}
                valueClass="text-theme-text-muted"
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}

// Helper component for info rows
const InfoRow = memo(
  ({
    label,
    value,
    valueClass,
  }: {
    label: string;
    value: string;
    valueClass: string;
  }) => {
    return (
      <div className="flex justify-between items-center">
        <span className="text-theme-text-secondary text-sm">{label}:</span>
        <span className={`font-semibold text-sm ${valueClass}`}>{value}</span>
      </div>
    );
  }
);

InfoRow.displayName = 'InfoRow';

export default memo(StreamInfo);
