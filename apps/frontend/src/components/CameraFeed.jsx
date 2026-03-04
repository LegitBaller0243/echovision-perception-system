import React, { useEffect, useRef, useState } from "react";
import { sendAutoDetect, sendQuery, sendTextToSpeech } from "../api";

export default function CameraFeed({ onCapture, onAction }) {
  const [result, setResult] = useState(null);
  const [queryText, setQueryText] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uiError, setUiError] = useState("");
  const videoRef = useRef(null);
  const canvasRef = useRef(document.createElement("canvas"));
  const recognitionRef = useRef(null);
  const processedFinalRef = useRef(false);

  useEffect(() => {
    const enableCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
          audio: false,
        });
        if (videoRef.current) videoRef.current.srcObject = stream;
      } catch (err) {
        console.error("Unable to access camera:", err);
        setUiError("Camera access failed. Please allow camera permission.");
      }
    };
    enableCamera();
  }, []);

  const captureFrame = () =>
    new Promise((resolve, reject) => {
      const video = videoRef.current;
      if (!video || !video.videoWidth || !video.videoHeight) {
        reject(new Error("Camera is not ready yet."));
        return;
      }

      const canvas = canvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            reject(new Error("Failed to capture frame."));
            return;
          }
          resolve(blob);
        },
        "image/jpeg",
        0.92
      );
    });

  const playTTS = async (text) => {
    const ttsResponse = await sendTextToSpeech(text);
    if (!ttsResponse?.ok || !ttsResponse?.audio_base64) {
      throw new Error(ttsResponse?.error || "TTS did not return audio.");
    }

    const audio = new Audio(
      `data:${ttsResponse.content_type || "audio/mpeg"};base64,${ttsResponse.audio_base64}`
    );
    await audio.play();
  };

  const runAutoDetect = async () => {
    setIsProcessing(true);
    setUiError("");
    try {
      onAction && onAction();
      const blob = await captureFrame();
      onCapture && onCapture(blob);
      const response = await sendAutoDetect(blob);
      const text = response?.result || "No auto-detect response.";
      setResult(text);
      await playTTS(text);
    } catch (err) {
      console.error("Auto-detect error:", err);
      setUiError(err.message || "Auto-detect failed.");
    } finally {
      setIsProcessing(false);
    }
  };

  const runQueryFlow = async (spokenText) => {
    setIsProcessing(true);
    setUiError("");
    try {
      onAction && onAction();
      const blob = await captureFrame();
      onCapture && onCapture(blob);
      const response = await sendQuery(spokenText, blob);
      const responseText =
        response?.result?.response_text ||
        response?.result ||
        "No response from query endpoint.";
      setResult(responseText);
      await playTTS(responseText);
    } catch (err) {
      console.error("Query flow error:", err);
      setUiError(err.message || "Query flow failed.");
    } finally {
      setIsProcessing(false);
    }
  };

  const startListening = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setUiError("Speech recognition is not supported on this browser.");
      return;
    }

    if (!recognitionRef.current) {
      const recognition = new SpeechRecognition();
      recognition.lang = "en-US";
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;
      recognition.continuous = false;

      recognition.onresult = (event) => {
        let interim = "";
        let finalTranscript = "";

        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interim += transcript;
          }
        }

        const text = (finalTranscript || interim).trim();
        setQueryText(text);

        if (finalTranscript.trim() && !processedFinalRef.current) {
          processedFinalRef.current = true;
          runQueryFlow(finalTranscript.trim());
        }
      };

      recognition.onerror = (event) => {
        setIsListening(false);
        if (event.error !== "no-speech") {
          setUiError(`Listening failed: ${event.error}`);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }

    processedFinalRef.current = false;
    setQueryText("");
    setUiError("");
    setIsListening(true);
    recognitionRef.current.start();
  };

  const stopListening = () => {
    try {
      recognitionRef.current?.stop();
    } catch (err) {
      console.error("Stop listening error:", err);
    }
    setIsListening(false);
  };

  return (
    <section className="camera-card">
      <div className="video-shell">
        <video ref={videoRef} autoPlay playsInline muted />
      </div>

      <div className="controls">
        <button
          className={`mic-button ${isListening ? "active" : ""}`}
          onClick={isListening ? stopListening : startListening}
          disabled={isProcessing}
        >
          {isListening ? "Stop Listening" : "Start Listening"}
        </button>

        <button className="scan-button" onClick={runAutoDetect} disabled={isProcessing}>
          Quick Scan
        </button>
      </div>

      <div className="status-block">
        <p className="status-line">
          {isProcessing ? "Processing frame..." : isListening ? "Listening..." : "Ready"}
        </p>
        {queryText && <p className="query-line">Heard: "{queryText}"</p>}
        {uiError && <p className="error-line">{uiError}</p>}
      </div>

      {result && (
        <div className="result-card">
          <h3>Latest Guidance</h3>
          <p>{result}</p>
        </div>
      )}
    </section>
  );
}
