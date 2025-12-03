document.getElementById("send").addEventListener("click", sendMessage);
document.addEventListener("DOMContentLoaded", function () {
  document.getElementById("startBtn").addEventListener("click", function () {
    setTimeout(() => {
      addMessage(
        "Bot",
        "👋 Welcome to NutriBot! I can see your profile is set up. Ask me anything about nutrition, diet, or healthy living! 🍎"
      );
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

function showTypingIndicator() {
  // avoid duplicates
  if (document.getElementById("typing-indicator")) return;

  const msgDiv = document.createElement("div");
  msgDiv.id = "typing-indicator";
  msgDiv.className = "message bot typing-indicator";
  msgDiv.innerHTML = `
    <b>Bot:</b> 
    <span class="typing-dots">
      <span>.</span><span>.</span><span>.</span>
    </span>
  `;
  chatbox.appendChild(msgDiv);
  chatbox.scrollTop = chatbox.scrollHeight;
}

function hideTypingIndicator() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
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
    showTypingIndicator();
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

  let typingTimeout;

  // Start 1-second timer before showing dots
  typingTimeout = setTimeout(() => {
    showTypingIndicator();
  }, 1000); // 1000ms = 1 second

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    const data = await res.json();

    // Cancel the timer if response came back fast
    clearTimeout(typingTimeout);

    // Hide dots if they already appeared
    hideTypingIndicator();

    addMessage("Bot", data.reply);
  } catch (err) {
    console.error(err);

    // Cancel timer + hide dots
    clearTimeout(typingTimeout);
    hideTypingIndicator();

    addMessage("Bot", "Sorry, something went wrong. Please try again.");
  }
}
