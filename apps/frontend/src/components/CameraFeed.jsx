import React, { useEffect, useRef, useState } from "react";
import { sendAutoDetect, sendQuery, sendTextToSpeech } from "../api";

const AUTO_DETECT_INTERVAL_MS = 12000;

export default function CameraFeed({ onCapture, onAction }) {
  const [result, setResult] = useState(null);
  const [queryText, setQueryText] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isAutoDetectOn, setIsAutoDetectOn] = useState(false);
  const [statusText, setStatusText] = useState("Ready");
  const [uiError, setUiError] = useState("");
  const [pendingAudioSrc, setPendingAudioSrc] = useState("");
  const videoRef = useRef(null);
  const canvasRef = useRef(document.createElement("canvas"));
  const recognitionRef = useRef(null);
  const processedFinalRef = useRef(false);
  const isProcessingRef = useRef(false);
  const audioUnlockedRef = useRef(false);
  const audioContextRef = useRef(null);
  const ttsAudioRef = useRef(new Audio());

  useEffect(() => {
    isProcessingRef.current = isProcessing;
  }, [isProcessing]);

  const ensureAudioUnlocked = async () => {
    if (audioUnlockedRef.current) return;
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) {
      audioUnlockedRef.current = true;
      return;
    }
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioCtx();
      }
      if (audioContextRef.current.state === "suspended") {
        await audioContextRef.current.resume();
      }
      const oscillator = audioContextRef.current.createOscillator();
      const gain = audioContextRef.current.createGain();
      gain.gain.value = 0.0001;
      oscillator.connect(gain);
      gain.connect(audioContextRef.current.destination);
      oscillator.start();
      oscillator.stop(audioContextRef.current.currentTime + 0.01);
      audioUnlockedRef.current = true;
    } catch (_err) {
      // keep Tap Play fallback
    }
  };

  useEffect(() => {
    const enableCamera = async () => {
      try {
        setStatusText("Starting camera...");
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
          audio: false,
        });
        if (videoRef.current) videoRef.current.srcObject = stream;
        setStatusText("Ready");
      } catch (err) {
        if (err?.name === "NotAllowedError") {
          setUiError("Camera blocked");
        } else if (err?.name === "NotFoundError") {
          setUiError("No camera");
        } else {
          setUiError("Camera error");
        }
        setStatusText("Camera failed");
      }
    };
    enableCamera();
  }, []);

  const captureFrame = () =>
    new Promise((resolve, reject) => {
      const video = videoRef.current;
      if (!video || !video.videoWidth || !video.videoHeight) {
        reject(new Error("Camera not ready"));
        return;
      }

      const canvas = canvasRef.current;
      const targetWidth = video.clientWidth || video.videoWidth;
      const targetHeight = video.clientHeight || video.videoHeight;
      canvas.width = targetWidth;
      canvas.height = targetHeight;
      const ctx = canvas.getContext("2d");

      // Match CSS object-fit: cover so preview framing equals analyzed framing.
      const sourceWidth = video.videoWidth;
      const sourceHeight = video.videoHeight;
      const scale = Math.max(targetWidth / sourceWidth, targetHeight / sourceHeight);
      const cropWidth = targetWidth / scale;
      const cropHeight = targetHeight / scale;
      const cropX = (sourceWidth - cropWidth) / 2;
      const cropY = (sourceHeight - cropHeight) / 2;

      ctx.drawImage(
        video,
        cropX,
        cropY,
        cropWidth,
        cropHeight,
        0,
        0,
        targetWidth,
        targetHeight
      );
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            reject(new Error("Capture failed"));
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
      throw new Error(ttsResponse?.error || "Audio failed");
    }

    const src = `data:${ttsResponse.content_type || "audio/mpeg"};base64,${ttsResponse.audio_base64}`;
    const audio = ttsAudioRef.current;
    audio.src = src;
    try {
      await audio.play();
      setPendingAudioSrc("");
      return true;
    } catch (err) {
      setPendingAudioSrc(src);
      return false;
    }
  };

  const runAutoDetect = async ({ playAudio = true, suppressError = false } = {}) => {
    if (isProcessingRef.current) return;
    setIsProcessing(true);
    setUiError("");
    setStatusText("Capturing...");
    try {
      await ensureAudioUnlocked();
      onAction && onAction();
      const blob = await captureFrame();
      onCapture && onCapture(blob);
      setStatusText("Analyzing...");
      const response = await sendAutoDetect(blob);
      const text = response?.result || "No response";
      setResult(text);
      if (playAudio) {
        setStatusText("Speaking...");
        const played = await playTTS(text);
        setStatusText(played ? "Ready" : "Tap Play");
      } else {
        setStatusText("Ready");
      }
    } catch (err) {
      if (!suppressError) {
        setUiError(err.message || "Scan failed");
        setStatusText("Scan failed");
      } else {
        setStatusText("Ready");
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const runQueryFlow = async (spokenText) => {
    setIsProcessing(true);
    setUiError("");
    setStatusText("Capturing...");
    try {
      onAction && onAction();
      const blob = await captureFrame();
      onCapture && onCapture(blob);
      setStatusText("Analyzing...");
      const response = await sendQuery(spokenText, blob);
      const responseText =
        response?.result?.response_text ||
        response?.result ||
        "No response";
      setResult(responseText);
      setStatusText("Speaking...");
      const played = await playTTS(responseText);
      setStatusText(played ? "Ready" : "Tap Play");
    } catch (err) {
      setUiError(err.message || "Query failed");
      setStatusText("Query failed");
    } finally {
      setIsProcessing(false);
    }
  };

  const startListening = () => {
    if (isAutoDetectOn) {
      setIsAutoDetectOn(false);
    }

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setUiError("Speech unavailable");
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
          setStatusText("Analyzing...");
          runQueryFlow(finalTranscript.trim());
        }
      };

      recognition.onerror = (event) => {
        setIsListening(false);
        if (event.error !== "no-speech") {
          setUiError("Mic error");
          setStatusText("Mic failed");
        }
      };

      recognition.onend = () => {
        setIsListening(false);
        if (!isProcessing) setStatusText("Ready");
      };

      recognitionRef.current = recognition;
    }

    processedFinalRef.current = false;
    setQueryText("");
    setUiError("");
    setStatusText("Listening...");
    setIsListening(true);
    try {
      ensureAudioUnlocked();
      recognitionRef.current.start();
    } catch (err) {
      setIsListening(false);
      setUiError("Mic blocked");
      setStatusText("Mic failed");
    }
  };

  const stopListening = () => {
    try {
      recognitionRef.current?.stop();
    } catch (_err) {
      // ignore
    }
    setIsListening(false);
    if (!isProcessing) setStatusText("Ready");
  };

  const replayAudio = async () => {
    if (!pendingAudioSrc) return;
    try {
      setStatusText("Speaking...");
      const audio = ttsAudioRef.current;
      audio.src = pendingAudioSrc;
      await audio.play();
      setPendingAudioSrc("");
      setStatusText("Ready");
    } catch (_err) {
      setUiError("Play blocked");
      setStatusText("Tap Play");
    }
  };

  useEffect(() => {
    if (!isAutoDetectOn) return undefined;

    const intervalId = window.setInterval(() => {
      if (!isListening && !isProcessingRef.current) {
        runAutoDetect({ playAudio: true, suppressError: true });
      }
    }, AUTO_DETECT_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [isAutoDetectOn, isListening]);

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

        <button className="scan-button" onClick={runAutoDetect} disabled={isProcessing || isListening}>
          Quick Scan
        </button>

        <button
          className="scan-button"
          onClick={() => setIsAutoDetectOn((prev) => !prev)}
          disabled={isListening}
        >
          {isAutoDetectOn ? "Stop Auto Detect" : "Start Auto Detect"}
        </button>
      </div>

      {!!pendingAudioSrc && (
        <div className="controls">
          <button className="scan-button replay-button" onClick={replayAudio} disabled={isProcessing}>
            Tap Play
          </button>
        </div>
      )}

      <div className="status-block">
        <p className="status-line">{statusText}</p>
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
