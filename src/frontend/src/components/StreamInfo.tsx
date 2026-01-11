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
  variant?: 'card' | 'section';
}

function StreamInfo({
  videoResolution,
  packetLoss,
  jitter,
  bitrate,
  framesReceived,
  framesDecoded,
  variant = 'card',
}: StreamInfoProps) {
  const { t } = useI18n();
  const containerClass =
    variant === 'card'
      ? 'bg-theme-bg-secondary border border-theme-border-subtle p-5 rounded-lg shadow-card'
      : '';
  const titleClass =
    variant === 'card'
      ? 'my-0 mb-4 text-theme-accent text-xl'
      : 'my-0 mb-3 text-theme-accent text-lg font-semibold';

  return (
    <div className={containerClass}>
      <h3 className={titleClass}>{t('streamInfoTitle')}</h3>

      <div className="space-y-3">
        {/* Video Resolution */}
        {videoResolution && (
          <InfoRow
            label={t('streamInfoResolution')}
            value={`${videoResolution.width} x ${videoResolution.height}`}
            valueClass="text-theme-accent"
          />
        )}

        {/* Network Quality */}
        {(packetLoss !== undefined ||
          jitter !== undefined ||
          bitrate !== undefined) && (
          <>
            <div className="text-theme-text-muted text-xs font-semibold uppercase mt-4 mb-2">
              {t('streamInfoNetworkQuality')}
            </div>

            {packetLoss !== undefined && (
              <InfoRow
                label={t('streamInfoPacketLoss')}
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
                label={t('streamInfoJitter')}
                value={`${jitter.toFixed(1)} ms`}
                valueClass="text-[#a29bfe]"
              />
            )}

            {bitrate !== undefined && (
              <InfoRow
                label={t('streamInfoBitrate')}
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
              {t('streamInfoVideoQuality')}
            </div>

            {framesReceived !== undefined && (
              <InfoRow
                label={t('streamInfoFramesReceived')}
                value={framesReceived.toString()}
                valueClass="text-theme-text-muted"
              />
            )}

            {framesDecoded !== undefined && (
              <InfoRow
                label={t('streamInfoFramesDecoded')}
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
