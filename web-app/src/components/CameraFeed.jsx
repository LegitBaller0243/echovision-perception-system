import React, { useEffect, useRef, useState } from "react";
import { sendAutoDetect } from "../api";

export default function CameraFeed({ onCapture, onAction }) {
  const [result, setResult] = useState(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(document.createElement("canvas"));

  useEffect(() => {
    const enableCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (videoRef.current) videoRef.current.srcObject = stream;
      } catch (err) {
        console.error("Unable to access camera:", err);
      }
    };
    enableCamera();
  }, []);

  const captureFrame = () => {
    const video = videoRef.current;
    if (!video) return;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      onCapture && onCapture(blob);
      try {
        const response = await sendAutoDetect(blob);
        console.log(response["result"])
        const audioResponse = await fetch('http://127.0.0.1:5000/text-to-speech', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: response["result"] })
        });
      } catch (err) {
        console.error("Auto-detect error:", err);
      }
    }, "image/jpeg");
  };

  return (
    <div style={{ textAlign: "center" }}>
      <video ref={videoRef} autoPlay playsInline width="320" height="240" />
      <div>
        <button
          onClick={() => {
            captureFrame();
            onAction && onAction(); // still triggers health check
          }}
        >
          Capture Frame
        </button>
      </div>
      {result && (
        <div style={{ marginTop: "1rem" }}>
          <strong>Auto-detect result:</strong>
          <pre style={{ textAlign: "left", display: "inline-block" }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
