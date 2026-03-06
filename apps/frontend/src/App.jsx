// src/App.jsx
import React, { useState, useEffect } from "react";
import { checkHealth } from "./api";
import CameraFeed from "./components/CameraFeed";

export default function App() {
  const [latestImage, setLatestImage] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);
  const [error, setError] = useState(null);

  // Check health on component mount
  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const res = await checkHealth();
        setHealthStatus(res.status);
        setError(res.status === "healthy" ? null : "Backend down");
      } catch (err) {
        setError("Backend down");
        setHealthStatus("unhealthy");
      }
    };
    checkBackendHealth();
  }, []);

  return (
    <main className="app-shell">
      <header className="hero">
        <p className="badge">KLR.ai</p>
        <h1>Vision Assistant</h1>
        <p className="subtitle">Mobile-ready scene guidance with voice-first interaction.</p>
      </header>

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      <CameraFeed onCapture={setLatestImage} />

      <footer className="health-footer">
        <span>Backend</span>
        <strong className={healthStatus === "healthy" ? "ok" : "down"}>
          {healthStatus || "checking..."}
        </strong>
        {latestImage && <span className="capture-dot" aria-label="captured frame" />}
      </footer>
    </main>
  );
}
