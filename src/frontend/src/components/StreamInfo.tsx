/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { memo } from 'react';
import { useI18n } from '../i18n';

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
  const { t } = useI18n();

  return (
    <div className="bg-[#2a2a2a] border border-[#404040] p-5 rounded-lg shadow-[0_4px_20px_rgba(0,0,0,0.4)]">
      <h3 className="my-0 mb-4 text-[#00d4ff] text-xl">
        {t('streamInfoTitle')}
      </h3>

      <div className="space-y-3">
        {/* Video Resolution */}
        {videoResolution && (
          <InfoRow
            label={t('streamInfoResolution')}
            value={`${videoResolution.width} x ${videoResolution.height}`}
            valueClass="text-[#00d4ff]"
          />
        )}

        {/* Network Quality */}
        {(packetLoss !== undefined ||
          jitter !== undefined ||
          bitrate !== undefined) && (
          <>
            <div className="text-[#888] text-xs font-semibold uppercase mt-4 mb-2">
              {t('streamInfoNetworkQuality')}
            </div>

            {packetLoss !== undefined && (
              <InfoRow
                label={t('streamInfoPacketLoss')}
                value={`${packetLoss.toFixed(2)}%`}
                valueClass={
                  packetLoss < 1
                    ? 'text-[#00d4aa]'
                    : packetLoss < 5
                      ? 'text-[#fdcb6e]'
                      : 'text-[#fd79a8]'
                }
              />
            )}

            {jitter !== undefined && (
              <InfoRow
                label={t('streamInfoJitter')}
                value={`${jitter.toFixed(1)} ms`}
                valueClass="text-[#a29bfe]"
              />
            )}

            {bitrate !== undefined && (
              <InfoRow
                label={t('streamInfoBitrate')}
                value={`${bitrate.toFixed(2)} Mbps`}
                valueClass="text-[#00d4ff]"
              />
            )}
          </>
        )}

        {/* Video Quality */}
        {(framesReceived !== undefined || framesDecoded !== undefined) && (
          <>
            <div className="text-[#888] text-xs font-semibold uppercase mt-4 mb-2">
              {t('streamInfoVideoQuality')}
            </div>

            {framesReceived !== undefined && (
              <InfoRow
                label={t('streamInfoFramesReceived')}
                value={framesReceived.toString()}
                valueClass="text-[#888]"
              />
            )}

            {framesDecoded !== undefined && (
              <InfoRow
                label={t('streamInfoFramesDecoded')}
                value={framesDecoded.toString()}
                valueClass="text-[#888]"
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
        <span className="text-[#b0b0b0] text-sm">{label}:</span>
        <span className={`font-semibold text-sm ${valueClass}`}>{value}</span>
      </div>
    );
  }
);

InfoRow.displayName = 'InfoRow';

export default memo(StreamInfo);
