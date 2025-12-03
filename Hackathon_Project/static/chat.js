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

function addMessage(sender, text) {
    const msgDiv = document.createElement("div");
    msgDiv.className = sender === "You" ? "message user" : "message bot";
    msgDiv.innerHTML = `<b>${sender}:</b> ${text}`;
    chatbox.appendChild(msgDiv);
    chatbox.scrollTop = chatbox.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById("input");
    const message = input.value.trim();
    if (!message) return;

    addMessage("You", message);
    input.value = "";

    const res = await fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message})
    });

    const data = await res.json();
    addMessage("Bot", data.reply);
}
