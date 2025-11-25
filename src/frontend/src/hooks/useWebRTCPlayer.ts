/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

// ConnectionState: short union for connection lifecycle
export type ConnectionState = 'idle' | 'connecting' | 'connected' | 'error';

// Normalize a backend signaling URL into a full /offer endpoint (uses fallback when invalid)
export function normalizeOfferUrl(raw?: string): string {
  const fallback = 'http://localhost:8001/offer';
  if (!raw) return fallback;
  try {
    const url = new URL(raw);
    const path = url.pathname.replace(/\/+$/, '');
    url.pathname = path.endsWith('/offer') ? path : `${path}/offer`;
    return url.toString();
  } catch {
    try {
      const withScheme = /^https?:\/\//.test(raw) ? raw : `http://${raw}`;
      const url = new URL(withScheme);
      const path = url.pathname.replace(/\/+$/, '');
      url.pathname = path.endsWith('/offer') ? path : `${path}/offer`;
      return url.toString();
    } catch {
      return fallback;
    }
  }
}

// Hook options
export interface UseWebRTCPlayerOptions {
  signalingEndpoint?: string;
  autoPlay?: boolean;
}

// Extended stats for MetadataWidget
export interface WebRTCStats {
  videoResolution?: { width: number; height: number };
  videoFps?: number;
  packetLoss?: number;
  jitter?: number;
  bitrate?: number;
  framesDropped?: number;
  framesReceived?: number;
  framesDecoded?: number;
}

// Hook result
export interface UseWebRTCPlayerResult {
  videoRef: React.RefObject<HTMLVideoElement>;
  connectionState: ConnectionState;
  errorReason: string;
  isPaused: boolean;
  latencyMs?: number;
  stats?: WebRTCStats;
  connect: () => Promise<void>;
  disconnect: () => void;
  togglePlayPause: () => Promise<void>;
  enterFullscreen: () => void;
}

// Hook: manages a WebRTC receiver (connect/disconnect, latency polling)
export function useWebRTCPlayer({
  signalingEndpoint,
  autoPlay = false,
}: UseWebRTCPlayerOptions): UseWebRTCPlayerResult {
  const offerUrl = useMemo(() => {
    const envUrl = (import.meta as any)?.env?.VITE_BACKEND_URL as
      | string
      | undefined;
    const base = signalingEndpoint ?? envUrl ?? 'http://localhost:8001';
    return normalizeOfferUrl(base);
  }, [signalingEndpoint]);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const statsPollRef = useRef<number | null>(null);

  const [connectionState, setConnectionState] =
    useState<ConnectionState>('idle');
  const [errorReason, setErrorReason] = useState('');
  const [isPaused, setIsPaused] = useState(false);
  const [latencyMs, setLatencyMs] = useState<number | undefined>(undefined);
  const [stats, setStats] = useState<WebRTCStats | undefined>(undefined);

  const connect = useCallback(async () => {
    if (pcRef.current) return;
    setErrorReason('');
    setConnectionState('connecting');

    const pc = new RTCPeerConnection({
      iceServers: [{ urls: ['stun:stun.l.google.com:19302'] }],
    });
    pcRef.current = pc;

    pc.addTransceiver('video', { direction: 'recvonly' });

    const waitForFirstCandidate = () =>
      new Promise<void>((resolve) => {
        let resolved = false;
        let timeoutId: number;
        const finish = () => {
          if (resolved) return;
          resolved = true;
          pc.removeEventListener('icecandidate', handler);
          window.clearTimeout(timeoutId);
          resolve();
        };
        const handler = (event: RTCPeerConnectionIceEvent) => {
          if (event.candidate || pc.iceGatheringState === 'complete') {
            finish();
          }
        };
        pc.addEventListener('icecandidate', handler);
        timeoutId = window.setTimeout(finish, 750);
      });

    pc.ontrack = (e) => {
      const [stream] = e.streams;
      if (!videoRef.current) return;
      videoRef.current.srcObject = stream;
      videoRef.current.onloadedmetadata = () => {
        if (autoPlay) {
          videoRef.current?.play().catch(() => {});
        }
      };
    };

    try {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      await waitForFirstCandidate();

      const localDesc = pc.localDescription;
      if (!localDesc?.sdp) {
        throw new Error('Missing local SDP');
      }

      const res = await fetch(offerUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sdp: localDesc.sdp,
          type: localDesc.type,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const answer = await res.json();
      await pc.setRemoteDescription(new RTCSessionDescription(answer));
      setConnectionState('connected');
      setIsPaused(false);
    } catch (err) {
      setConnectionState('error');
      setErrorReason(String(err));
      try {
        pc.close();
      } catch {}
      pcRef.current = null;
    }
  }, [offerUrl, autoPlay]);

  const disconnect = useCallback(() => {
    const pc = pcRef.current;
    if (pc) {
      try {
        pc.getReceivers().forEach((r) => r.track && (r.track.enabled = false));
        pc.close();
      } catch {}
    }
    pcRef.current = null;
    if (videoRef.current) {
      try {
        videoRef.current.pause();
        (videoRef.current as any).srcObject = null;
      } catch {}
    }
    setIsPaused(false);
    setConnectionState('idle');
    setLatencyMs(undefined);
    setStats(undefined);
    if (statsPollRef.current) {
      window.clearInterval(statsPollRef.current);
      statsPollRef.current = null;
    }
  }, []);

  const togglePlayPause = useCallback(async () => {
    if (connectionState !== 'connected') {
      await connect();
      return;
    }
    if (!videoRef.current) return;
    if (isPaused) {
      try {
        pcRef.current
          ?.getReceivers()
          .forEach((r) => r.track && (r.track.enabled = true));
      } catch {}
      await videoRef.current.play().catch(() => {});
      setIsPaused(false);
    } else {
      try {
        pcRef.current
          ?.getReceivers()
          .forEach((r) => r.track && (r.track.enabled = false));
      } catch {}
      videoRef.current.pause();
      setIsPaused(true);
    }
  }, [connectionState, isPaused, connect]);

  const enterFullscreen = useCallback(() => {
    const el = (videoRef.current?.parentElement ?? videoRef.current) as any;
    if (!el) return;
    const doc: any = document as any;
    const isFull =
      doc.fullscreenElement ||
      doc.webkitFullscreenElement ||
      doc.msFullscreenElement;
    if (isFull) {
      const exit =
        doc.exitFullscreen || doc.webkitExitFullscreen || doc.msExitFullscreen;
      if (exit) exit.call(doc);
      return;
    }
    const req =
      el.requestFullscreen ||
      el.webkitRequestFullscreen ||
      el.msRequestFullscreen;
    if (req) req.call(el);
  }, []);

  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  // Poll WebRTC stats for latency when connected
  useEffect(() => {
    if (connectionState !== 'connected' || !pcRef.current) {
      if (statsPollRef.current) {
        window.clearInterval(statsPollRef.current);
        statsPollRef.current = null;
      }
      return;
    }

    const poll = async () => {
      try {
        const pc = pcRef.current;
        const video = videoRef.current;
        if (!pc || !video) return;

        const statsReport = await pc.getStats();

        // Collect all stats
        let rttSeconds: number | undefined;
        let videoWidth: number | undefined;
        let videoHeight: number | undefined;
        let fps: number | undefined;
        let packetsLost = 0;
        let packetsReceived = 0;
        let jitterMs: number | undefined;
        let bytesReceived = 0;
        let framesDropped: number | undefined;
        let framesReceivedCount: number | undefined;
        let framesDecoded: number | undefined;

        statsReport.forEach((report) => {
          // RTT for latency
          if (
            report.type === 'candidate-pair' &&
            (report as any).nominated &&
            (report as any).state === 'succeeded'
          ) {
            const v = (report as any).currentRoundTripTime;
            if (typeof v === 'number') {
              rttSeconds = v;
            }
          }
          if (
            report.type === 'remote-inbound-rtp' &&
            (report as any).roundTripTime != null
          ) {
            const v = (report as any).roundTripTime;
            if (typeof v === 'number') {
              rttSeconds = v;
            }
          }

          // Inbound RTP stats for video
          if (report.type === 'inbound-rtp' && (report as any).kind === 'video') {
            // Resolution
            videoWidth = (report as any).frameWidth;
            videoHeight = (report as any).frameHeight;

            // FPS
            fps = (report as any).framesPerSecond;

            // Packet loss
            packetsLost = (report as any).packetsLost || 0;
            packetsReceived = (report as any).packetsReceived || 0;

            // Jitter (in seconds, convert to ms)
            const jitter = (report as any).jitter;
            if (typeof jitter === 'number') {
              jitterMs = jitter * 1000;
            }

            // Bytes received (for bitrate calculation)
            bytesReceived = (report as any).bytesReceived || 0;

            // Frames
            framesDropped = (report as any).framesDropped;
            framesReceivedCount = (report as any).framesReceived;
            framesDecoded = (report as any).framesDecoded;
          }
        });

        // Calculate packet loss percentage
        const packetLossPercent =
          packetsReceived > 0
            ? (packetsLost / (packetsLost + packetsReceived)) * 100
            : 0;

        // Calculate bitrate (simplified - would need delta calculation for accuracy)
        // Note: This is a rough estimate. For accurate bitrate, we'd need to track bytesReceived over time
        const bitrateKbps =
          bytesReceived > 0 ? (bytesReceived * 8) / 1000 / 250 : undefined; // rough estimate over 250ms poll interval

        // Update latency
        if (rttSeconds != null) {
          setLatencyMs(Math.max(0, Math.round(rttSeconds * 1000)));
        }

        // Update extended stats
        setStats({
          videoResolution:
            videoWidth && videoHeight
              ? { width: videoWidth, height: videoHeight }
              : video.videoWidth && video.videoHeight
                ? { width: video.videoWidth, height: video.videoHeight }
                : undefined,
          videoFps: fps,
          packetLoss: packetLossPercent,
          jitter: jitterMs,
          bitrate: bitrateKbps ? bitrateKbps / 1000 : undefined, // Convert to Mbps
          framesDropped,
          framesReceived: framesReceivedCount,
          framesDecoded,
        });
      } catch (error) {
        console.error('Error polling WebRTC stats:', error);
      }
    };

    // initial poll and interval
    poll();
    statsPollRef.current = window.setInterval(poll, 250);
    return () => {
      if (statsPollRef.current) {
        window.clearInterval(statsPollRef.current);
        statsPollRef.current = null;
      }
    };
  }, [connectionState]);

  return {
    videoRef,
    connectionState,
    errorReason,
    isPaused,
    latencyMs,
    stats,
    connect,
    disconnect,
    togglePlayPause,
    enterFullscreen,
  };
}
