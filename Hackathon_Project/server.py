from flask import Flask, request, jsonify, render_template
import re
app = Flask(__name__)

# ================================
# Your Python chatbot logic here
# ================================
def chatbot_reply(user_message):
    if "hello" in user_message.lower():
        return "Hi! How can I help you?"

    return "I'm not sure, can you rephrase that?"

def chatbot_reply(user_message):
    if re.search(r"\b(hello|hi|hey)\b", user_message, re.I):
        return "Hello there!"

    if re.search(r"\bweather\b", user_message, re.I):
        return "Do you want today's weather?"

    return "Not sure what you mean."


# ================
# CHAT ENDPOINT
# ================
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "")
    reply = chatbot_reply(message)
    return jsonify({"reply": reply})


# ================
# LOAD MAIN PAGE
# ================
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
