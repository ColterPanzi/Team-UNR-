document.getElementById("send").addEventListener("click", sendMessage);
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('startBtn').addEventListener('click', function() {
        setTimeout(() => {
            addMessage("Bot", "👋 Welcome to NutriBot! I can see your profile is set up. Ask me anything about nutrition, diet, or healthy living! 🍎");
        }, 500);
    });
});
document.getElementById("input").addEventListener("keypress", function (e) {
  if (e.key === "Enter") sendMessage();
});

const chatbox = document.getElementById("chatbox");
const inputEl = document.getElementById("input");
const attachBtn = document.getElementById("attach");
const imageInput = document.getElementById("imageInput");

function addMessage(sender, text) {
  const msgDiv = document.createElement("div");
  msgDiv.className = sender === "You" ? "message user" : "message bot";
  msgDiv.innerHTML = `<b>${sender}:</b> ${text}`;
  chatbox.appendChild(msgDiv);
  chatbox.scrollTop = chatbox.scrollHeight;
}

attachBtn.addEventListener("click", () => {
  imageInput.click();
});

imageInput.addEventListener("change", async () => {
  if (!imageInput.files.length) return;

  const file = imageInput.files[0];
  addMessage("You", "📎 Uploaded an image");

  const formData = new FormData();
  formData.append("photo", file);
  try {
    const res = await fetch("/upload_grocery", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    const replyText = data.reply || "Image uploaded to pantry.";
    addMessage("Bot", replyText);
  } catch (err) {
    console.error(err);
    addMessage("Bot", "Sorry, there was a problem uploading the image.");
  }
  imageInput.value = "";
});

async function sendMessage() {
  const input = document.getElementById("input");
  const message = input.value.trim();
  if (!message) return;

  addMessage("You", message);
  input.value = "";

  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  const data = await res.json();
  addMessage("Bot", data.reply);
}
