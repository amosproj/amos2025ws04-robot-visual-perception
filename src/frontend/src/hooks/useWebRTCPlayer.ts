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

// Hook result
export interface UseWebRTCPlayerResult {
  videoRef: React.RefObject<HTMLVideoElement>;
  connectionState: ConnectionState;
  errorReason: string;
  isPaused: boolean;
  latencyMs?: number;
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

  const connect = useCallback(async () => {
    if (pcRef.current) return;
    setErrorReason('');
    setConnectionState('connecting');

    const pc = new RTCPeerConnection({
      iceServers: [{ urls: ['stun:stun.l.google.com:19302'] }],
    });
    pcRef.current = pc;

    pc.addTransceiver('video', { direction: 'recvonly' });

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

      await new Promise<void>((resolve) => {
        if (pc.iceGatheringState === 'complete') return resolve();
        const handler = () => {
          if (pc.iceGatheringState === 'complete') {
            pc.removeEventListener('icegatheringstatechange', handler);
            resolve();
          }
        };
        pc.addEventListener('icegatheringstatechange', handler);
      });

      const res = await fetch(offerUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sdp: pc.localDescription?.sdp ?? '',
          type: 'offer',
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
        if (!pc) return;
        const stats = await pc.getStats();
        let rttSeconds: number | undefined;
        stats.forEach((report) => {
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
        });
        if (rttSeconds != null) {
          setLatencyMs(Math.max(0, Math.round(rttSeconds * 1000)));
        }
      } catch {}
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
    connect,
    disconnect,
    togglePlayPause,
    enterFullscreen,
  };
}
