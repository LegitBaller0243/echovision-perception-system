// src/App.jsx
import React, { useState, useEffect } from "react";
import { checkHealth } from "./api";
import CameraFeed from "./components/CameraFeed";
import AudioInterface from "./components/AudioInterface";

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
        setError(null);
      } catch (err) {
        console.error("Health check error:", err);
        setError("Backend connection failed. Make sure Flask server is running on port 5000.");
        setHealthStatus("unhealthy");
      }
    };
    checkBackendHealth();
  }, []);

  const handleComponentClick = async () => {
    try {
      const res = await checkHealth();
      setHealthStatus(res.status);
      setError(null);
    } catch (err) {
      console.error("Health check error:", err);
      setError("Backend connection failed.");
      setHealthStatus("unhealthy");
    }
  };

  return (
    <div style={{ textAlign: "center", padding: "2rem" }}>
      <h1>KLR Vision Assistant</h1>

      {error && (
        <div style={{ 
          margin: "1rem auto", 
          padding: "1rem", 
          backgroundColor: "#fee", 
          color: "#c00",
          borderRadius: "4px",
          maxWidth: "600px"
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Camera and audio now trigger the same health check */}
      <CameraFeed onCapture={setLatestImage} onAction={handleComponentClick} />
      <AudioInterface
        latestImage={latestImage}
        onAction={handleComponentClick}
      />

      {healthStatus && (
        <p style={{ marginTop: "1rem" }}>
          🩺 Flask backend status: <strong>{healthStatus}</strong>
        </p>
      )}
    </div>
  );
}
