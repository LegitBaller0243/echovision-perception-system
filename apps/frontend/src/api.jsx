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
  } catch (_err) {
    return { status: "unhealthy" };
  }
};

export const sendAutoDetect = async (imageBlob) => {
  try {
    const base64Image = await blobToBase64(imageBlob);
    if (!base64Image || typeof base64Image !== "string") {
      throw new Error("Capture failed");
    }

    const res = await axios.post(
      `${API_BASE}/auto-detect`,
      { image: base64Image },
      {
        withCredentials: false,
        headers: { "Content-Type": "application/json" },
      }
    );

    return res.data;
  } catch (err) {
    throw toApiError(err, "Scan failed");
  }
};

export const sendQuery = async (query, imageBlob) => {
  try {
    if (!query || typeof query !== "string" || !query.trim()) {
      throw new Error("No query");
    }
    const base64Image = await blobToBase64(imageBlob);
    if (!base64Image || typeof base64Image !== "string") {
      throw new Error("Capture failed");
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
    throw toApiError(err, "Query failed");
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
    throw toApiError(err, "Audio failed");
  }
};

const blobToBase64 = (blob) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      try {
        if (typeof reader.result !== "string" || !reader.result.includes(",")) {
          reject(new Error("Capture failed"));
          return;
        }
        let base64 = reader.result.split(",")[1];
        if (!base64) {
          reject(new Error("Capture failed"));
          return;
        }
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
    const status = err.response?.status;
    if (status) {
      if (status >= 500) return new Error("Server error");
      if (status === 404) return new Error("Not found");
      if (status === 401 || status === 403) return new Error("Not allowed");
      if (status === 408) return new Error("Timeout");
      return new Error(fallbackMessage);
    }
    if (err.request) return new Error("No server");
  }
  return err instanceof Error ? err : new Error(fallbackMessage);
};
