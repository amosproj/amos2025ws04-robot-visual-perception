/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import WebRTCStreamPlayer from './components/WebRTCStreamPlayer';

function App() {
  const envUrl = (import.meta as any)?.env?.VITE_BACKEND_URL as
    | string
    | undefined;
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#667eea] to-[#764ba2] text-white">
      <div className="text-center p-8 w-full max-w-4xl">
        <header>
          <h1 className="text-5xl mb-2 font-bold">OptiBot</h1>
          <p className="text-xl opacity-90 mb-8">
            T-Systems Project - AMOS 2025
          </p>
        </header>
        <main>
          <WebRTCStreamPlayer
            signalingEndpoint={envUrl}
            autoPlay
            muted
            enableOverlay={true}
            overlayTestMode={true}
            className="backdrop-blur-md bg-white/10 rounded-2xl p-8 border border-white/20 shadow-xl"
          />
        </main>
      </div>
    </div>
  );
}

export default App;
