/**
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 *
 * This component provides a real-time video streaming interface
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

// Simple SVG icon components
const Play = ({ size = 24, fill = 'white' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill}>
    <path d="M8 5v14l11-7z"/>
  </svg>
);

const Pause = ({ size = 24, fill = 'white' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill}>
    <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
  </svg>
);

const Maximize = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
  </svg>
);

interface WebRTCStreamPlayerProps {
  signalingEndpoint?: string;
  className?: string;
  style?: React.CSSProperties;
  autoPlay?: boolean;
}

function normalizeOfferUrl(raw?: string): string {
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

function WebRTCStreamPlayer({
  signalingEndpoint,
  className,
  style,
  autoPlay = false,
}: WebRTCStreamPlayerProps) {
  const offerUrl = useMemo(() => {
    const envUrl = (import.meta as any)?.env?.VITE_BACKEND_URL as string | undefined;
    const base = signalingEndpoint ?? envUrl ?? 'http://localhost:8001';
    return normalizeOfferUrl(base);
  }, [signalingEndpoint]);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);

  const [connectionState, setConnectionState] = useState<'idle' | 'connecting' | 'connected' | 'error'>('idle');
  const [errorReason, setErrorReason] = useState('');
  const [isPaused, setIsPaused] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [latency, setLatency] = useState<number | null>(null);

  const connect = useCallback(async () => {
    if (pcRef.current) return;
    setErrorReason('');
    setConnectionState('connecting');

    const pc = new RTCPeerConnection({ iceServers: [{ urls: ['stun:stun.l.google.com:19302'] }] });
    pcRef.current = pc;

    pc.addTransceiver('video', { direction: 'recvonly' });

    // Monitor connection stats for latency
    const statsInterval = setInterval(async () => {
      if (pc.connectionState !== 'connected') return;
      try {
        const stats = await pc.getStats();
        stats.forEach((report) => {
          if (report.type === 'inbound-rtp' && report.kind === 'video') {
            const jitter = report.jitter ? Math.round(report.jitter * 1000) : null;
            setLatency(jitter);
          }
        });
      } catch {}
    }, 1000);

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

    pc.onconnectionstatechange = () => {
      if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') {
        clearInterval(statsInterval);
        setLatency(null);
      }
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
        body: JSON.stringify({ sdp: pc.localDescription?.sdp ?? '', type: 'offer' }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const answer = await res.json();
      await pc.setRemoteDescription(new RTCSessionDescription(answer));
      setConnectionState('connected');
      setIsPaused(false);
    } catch (err) {
      setConnectionState('error');
      setErrorReason(String(err));
      clearInterval(statsInterval);
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
        videoRef.current.srcObject = null;
      } catch {}
    }
    setIsPaused(false);
    setConnectionState('idle');
    setLatency(null);
  }, []);

  const togglePlayPause = useCallback(async () => {
    if (connectionState !== 'connected') {
      await connect();
      return;
    }
    if (!videoRef.current) return;
    if (isPaused) {
      try {
        pcRef.current?.getReceivers().forEach((r) => r.track && (r.track.enabled = true));
      } catch {}
      await videoRef.current.play().catch(() => {});
      setIsPaused(false);
    } else {
      try {
        pcRef.current?.getReceivers().forEach((r) => r.track && (r.track.enabled = false));
      } catch {}
      videoRef.current.pause();
      setIsPaused(true);
    }
  }, [connectionState, isPaused, connect]);

  const enterFullscreen = useCallback(() => {
    const el = videoRef.current?.parentElement ?? videoRef.current;
    if (!el) return;
    const anyEl = el as any;
    const req = anyEl.requestFullscreen || anyEl.webkitRequestFullscreen || anyEl.msRequestFullscreen;
    if (req) req.call(anyEl);
  }, []);

  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  return (
    <div className={className} style={{ display: 'flex', flexDirection: 'column', gap: 16, ...style }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span style={{
            fontSize: 14,
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}>
            <span style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: connectionState === 'connected' ? '#22c55e' : connectionState === 'connecting' ? '#eab308' : connectionState === 'error' ? '#ef4444' : '#6b7280',
              boxShadow: connectionState === 'connected' ? '0 0 8px #22c55e' : 'none',
              transition: 'all 0.3s'
            }} />
            {connectionState === 'idle' && 'Ready'}
            {connectionState === 'connecting' && 'Connecting…'}
            {connectionState === 'connected' && (isPaused ? 'Paused' : 'Live')}
            {connectionState === 'error' && 'Connection Error'}
          </span>

          {latency !== null && connectionState === 'connected' && (
            <span style={{
              fontSize: 13,
              padding: '4px 10px',
              backgroundColor: latency < 50 ? '#dcfce7' : latency < 100 ? '#fef9c3' : '#fee2e2',
              color: latency < 50 ? '#166534' : latency < 100 ? '#854d0e' : '#991b1b',
              borderRadius: 4,
              fontWeight: 500
            }}>
              {latency}ms
            </span>
          )}
        </div>

        <button
          onClick={disconnect}
          disabled={connectionState === 'idle'}
          style={{
            padding: '10px 24px',
            backgroundColor: connectionState === 'idle' ? '#9ca3af' : '#ef4444',
            color: 'white',
            border: 'none',
            borderRadius: 6,
            fontSize: 15,
            fontWeight: 600,
            cursor: connectionState === 'idle' ? 'not-allowed' : 'pointer',
            opacity: connectionState === 'idle' ? 0.6 : 1,
            transition: 'all 0.2s',
            boxShadow: connectionState === 'idle' ? 'none' : '0 2px 8px rgba(239, 68, 68, 0.3)'
          }}
          onMouseOver={(e) => {
            if (connectionState !== 'idle') {
              e.currentTarget.style.backgroundColor = '#dc2626';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }
          }}
          onMouseOut={(e) => {
            if (connectionState !== 'idle') {
              e.currentTarget.style.backgroundColor = '#ef4444';
              e.currentTarget.style.transform = 'translateY(0)';
            }
          }}
        >
          Disconnect
        </button>
      </div>

      {connectionState === 'error' && (
        <div style={{
          padding: '12px 16px',
          backgroundColor: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: 8,
          color: '#991b1b',
          fontSize: 14
        }}>
          <strong>Error:</strong> {errorReason}
        </div>
      )}

      <div
        style={{
          width: '100%',
          aspectRatio: '16 / 9',
          maxHeight: 'calc(100vh - 200px)',
          position: 'relative',
          backgroundColor: '#000',
          borderRadius: 8,
          overflow: 'hidden'
        }}
        onMouseEnter={() => setShowControls(true)}
        onMouseLeave={() => setShowControls(false)}
      >
        <video
          ref={videoRef}
          autoPlay={autoPlay}
          playsInline
          muted
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            background: '#000',
            display: 'block'
          }}
        />

        <div style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          padding: '16px',
          background: 'linear-gradient(to top, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0.4) 70%, transparent 100%)',
          opacity: showControls ? 1 : 0,
          transition: 'opacity 0.3s',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          {/* Left side - Play/Pause */}
          <button
            onClick={togglePlayPause}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'white',
              cursor: 'pointer',
              padding: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 4,
              transition: 'background 0.2s'
            }}
            onMouseOver={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.2)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
          >
            {connectionState !== 'connected' || isPaused ? <Play size={28} fill="white" /> : <Pause size={28} fill="white" />}
          </button>

          {/* Right side - Fullscreen */}
          <button
            onClick={enterFullscreen}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'white',
              cursor: 'pointer',
              padding: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 4,
              transition: 'background 0.2s'
            }}
            onMouseOver={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.2)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <Maximize size={22} />
          </button>
        </div>
      </div>
    </div>
  );
}

function App() {
  const envUrl = (import.meta as any)?.env?.VITE_BACKEND_URL as string | undefined;
  return (
    <div id="app">
      <header>
        <h1>OptiBot</h1>
        <p>T-Systems Project - AMOS 2025</p>
      </header>
      <main>
        <WebRTCStreamPlayer signalingEndpoint={envUrl} autoPlay />
      </main>
    </div>
  );
}

export default App;