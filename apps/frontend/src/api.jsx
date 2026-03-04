import axios from "axios";

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL || window.location.origin;

export const checkHealth = async () => {
  try {
    const res = await axios.get(`${API_BASE}/health`, {
      withCredentials: false, // don't include cookies
      headers: {
        "Content-Type": "application/json",
      },
    });
    return res.data;
  } catch (err) {
    console.error("Health check failed:", err);
    return { status: "unhealthy" };
  }
};
// 🆕 NEW: call the /auto-detect endpoint
export const sendAutoDetect = async (imageBlob) => {
  try {
    // Convert the image blob to base64
    const base64Image = await blobToBase64(imageBlob);
    if (!base64Image || typeof base64Image !== "string") {
      throw new Error("Captured frame is empty. Try again.");
    }

    const res = await axios.post(
      `${API_BASE}/auto-detect`,
      { image: base64Image },
      {
        withCredentials: false,
        headers: { "Content-Type": "application/json" },
      }
    );

    return res.data; // should be { result: ... }
  } catch (err) {
    console.error("Auto-detect failed:", err);
    throw toApiError(err, "Auto-detect request failed");
  }
};

export const sendQuery = async (query, imageBlob) => {
  try {
    if (!query || typeof query !== "string" || !query.trim()) {
      throw new Error("Query text is empty.");
    }
    const base64Image = await blobToBase64(imageBlob);
    if (!base64Image || typeof base64Image !== "string") {
      throw new Error("Captured frame is empty. Try again.");
    }

    const res = await axios.post(
      `${API_BASE}/query`,
      { query: query.trim(), image: base64Image },
      {
        withCredentials: false,
        headers: { "Content-Type": "application/json" },
      }
    );
    return res.data;
  } catch (err) {
    console.error("Query request failed:", err);
    throw toApiError(err, "Query request failed");
  }
};

export const sendTextToSpeech = async (text) => {
  try {
    const res = await axios.post(
      `${API_BASE}/text-to-speech`,
      { text },
      {
        withCredentials: false,
        headers: { "Content-Type": "application/json" },
      }
    );

    return res.data;
  } catch (err) {
    console.error("Text-to-speech failed:", err);
    throw toApiError(err, "Text-to-speech failed");
  }
};

// Helper: convert Blob → Base64
const blobToBase64 = (blob) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      try {
        if (typeof reader.result !== "string" || !reader.result.includes(",")) {
          reject(new Error("Unable to encode captured image."));
          return;
        }
        let base64 = reader.result.split(",")[1]; // remove data: prefix
        if (!base64) {
          reject(new Error("Captured image has no data."));
          return;
        }
        // 🧩 fix padding if necessary
        const padding = base64.length % 4;
        if (padding) {
          base64 += "=".repeat(4 - padding);
        }
        resolve(base64);
      } catch (err) {
        reject(err);
      }
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
};

const toApiError = (err, fallbackMessage) => {
  if (axios.isAxiosError(err)) {
    const apiMessage =
      err.response?.data?.error ||
      err.response?.data?.message ||
      err.response?.data?.detail;
    if (apiMessage) return new Error(apiMessage);
    if (err.response?.status) {
      return new Error(`${fallbackMessage} (HTTP ${err.response.status})`);
    }
    if (err.request) return new Error("No response from server.");
  }
  return err instanceof Error ? err : new Error(fallbackMessage);
};
