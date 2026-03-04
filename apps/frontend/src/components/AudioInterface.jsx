import React, { useRef, useState } from "react";

/**
 * Temporary AudioInterface — only triggers health check, no backend media send
 */
export default function AudioInterface({ onAction }) {
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunks = useRef([]);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorderRef.current = new MediaRecorder(stream);
    mediaRecorderRef.current.ondataavailable = (e) => chunks.current.push(e.data);
    mediaRecorderRef.current.onstop = async () => {
      // do nothing with audio yet
      chunks.current = [];
    };
    mediaRecorderRef.current.start();
    setRecording(true);
  };

  const stopRecording = () => {
    mediaRecorderRef.current.stop();
    setRecording(false);
  };

  return (
    <div style={{ marginTop: "1rem", textAlign: "center" }}>
      <button
        onClick={() => {
          if (recording) stopRecording();
          else startRecording();
          onAction && onAction(); // trigger health check
        }}
      >
        {recording ? "Stop Listening" : "Start Listening"}
      </button>
    </div>
  );
}
