/**
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import WebRTCStreamPlayer from './components/WebRTCStreamPlayer';

function App() {
  const envUrl = (import.meta as any)?.env?.VITE_BACKEND_URL as string | undefined;
  return (
    <div id="app">
      <header>
        <h1>OptiBot</h1>
        <p>T-Systems Project - AMOS 2025</p>
      </header>
      <main>
        <WebRTCStreamPlayer signalingEndpoint={envUrl} autoPlay muted />
      </main>
    </div>
  );
}

export default App;
