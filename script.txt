const API_BASE = "https://studyrag-ai-v2.onrender.com";

const pdfInput = document.getElementById("pdfInput");
const uploadBtn = document.getElementById("uploadBtn");
const uploadMessage = document.getElementById("uploadMessage");
const fileName = document.getElementById("fileName");
const fileStatus = document.getElementById("fileStatus");
const askForm = document.getElementById("askForm");
const question = document.getElementById("question");
const askBtn = document.getElementById("askBtn");
const chat = document.getElementById("chat");
const clearBtn = document.getElementById("clearBtn");
let uploaded = false;

pdfInput.addEventListener("change", () => {
  const file = pdfInput.files[0];
  if (!file) return;
  fileName.textContent = file.name;
  fileStatus.textContent = "Ready to upload";
  fileStatus.className = "status";
  uploadBtn.disabled = file.type !== "application/pdf";
  uploadMessage.textContent = file.type === "application/pdf" ? "" : "Please choose a PDF file.";
  uploadMessage.className = "message error";
});

uploadBtn.addEventListener("click", async () => {
  const file = pdfInput.files[0];
  if (!file) return;

  uploadBtn.disabled = true;
  uploadBtn.textContent = "Processing...";
  uploadMessage.textContent = "Uploading and extracting text...";
  uploadMessage.className = "message";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API_BASE}/upload-pdf`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || "PDF upload failed.");

    uploaded = true;
    fileStatus.textContent = `${data.characters || ""} characters processed`;
    fileStatus.className = "status success";
    uploadMessage.textContent = "PDF uploaded successfully. You can ask questions now.";
    uploadMessage.className = "message ok";
    question.disabled = false;
    askBtn.disabled = false;
  } catch (err) {
    uploadMessage.textContent = err.message || "Could not connect to the backend.";
    uploadMessage.className = "message error";
    fileStatus.textContent = "Upload failed";
    fileStatus.className = "status";
  } finally {
    uploadBtn.disabled = false;
    uploadBtn.textContent = "Upload & Process";
  }
});

askForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = question.value.trim();
  if (!q || !uploaded) return;

  addMessage(q, "user");
  question.value = "";
  question.disabled = true;
  askBtn.disabled = true;

  const thinking = addMessage("Thinking...", "ai");

  try {
    const res = await fetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question: q})
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || "Question request failed.");
    thinking.querySelector(".bubble").textContent = data.answer || "No answer returned.";
  } catch (err) {
    thinking.querySelector(".bubble").textContent = "Error: " + (err.message || "Could not connect to the backend.");
  } finally {
    question.disabled = false;
    askBtn.disabled = false;
    question.focus();
  }
});

clearBtn.addEventListener("click", () => {
  chat.innerHTML = "";
  addWelcome();
});

document.querySelectorAll(".suggestion").forEach(btn => {
  btn.addEventListener("click", () => {
    question.value = btn.textContent.replace(/[“”]/g, "").trim();
    question.focus();
  });
});

function addMessage(text, type) {
  const row = document.createElement("div");
  row.className = `msg ${type}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  row.appendChild(bubble);
  chat.appendChild(row);
  chat.scrollTop = chat.scrollHeight;
  return row;
}

function addWelcome() {
  chat.innerHTML = `
    <div class="welcome">
      <div class="welcome-icon">✦</div>
      <h3>Ready when you are</h3>
      <p>Upload a PDF first, then ask something like:</p>
      <button class="suggestion">“Explain the main topics in this PDF.”</button>
      <button class="suggestion">“What is a stack?”</button>
    </div>`;
  chat.querySelectorAll(".suggestion").forEach(btn => {
    btn.addEventListener("click", () => {
      question.value = btn.textContent.replace(/[“”]/g, "").trim();
      question.focus();
    });
  });
}
