import axios from "axios";

const API_BASE = "http://127.0.0.1:5000"; // use 127.0.0.1 to match Flask exactly

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
    throw err;
  }
};

// Helper: convert Blob → Base64
const blobToBase64 = (blob) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      try {
        let base64 = reader.result.split(",")[1]; // remove data: prefix
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
