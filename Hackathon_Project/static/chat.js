document.getElementById("send").addEventListener("click", sendMessage);
document.getElementById("input").addEventListener("keypress", function (e) {
    if (e.key === "Enter") sendMessage();
});

const chatbox = document.getElementById("chatbox");

function addMessage(sender, text) {
    chatbox.innerHTML += `<b>${sender}:</b> ${text}<br>`;
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
