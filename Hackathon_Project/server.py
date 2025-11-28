from flask import Flask, request, jsonify, render_template
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

app = Flask(__name__)

# ================================
# Your Python chatbot logic here
# ================================
# Simple dataset of common nutrition myths and facts
myth_dataset = [
    ("carbs make you fat", "myth"),
    ("detox teas remove toxins", "myth"),
    ("eating late at night causes weight gain", "myth"),
    ("high protein diets damage kidneys", "myth"),
    ("drinking lemon water detoxes the body", "myth"),
    ("protein helps build muscle", "fact"),
    ("vegetables are healthy", "fact"),
    ("vitamin C boosts immune function", "fact"),
    ("drinking water is good for hydration", "fact"),
]

# Split texts and labels
texts = [x[0] for x in myth_dataset]
labels = [x[1] for x in myth_dataset]

# Build pipeline: convert text → vector → classify
myth_model = Pipeline([
    ("vectorizer", TfidfVectorizer()),
    ("classifier", MultinomialNB())
])

# Train model
myth_model.fit(texts, labels)

def chatbot_reply(user_message):
    prediction = myth_model.predict([user_message])[0]  # "myth" or "fact"
    if "hello" in user_message.lower():
        return "Hi! How can I help you?"
    
    if re.search(r"\b(hello|hi|hey)\b", user_message, re.I):
        return "Hello there!"

    if re.search(r"\bweather\b", user_message, re.I):
        return "Do you want today's weather?"
    
    if prediction == "myth":
        return "⚠️ That sounds like a common nutrition myth! Here's the truth: " \
               "Not all carbs make you fat, and detox teas don't remove toxins. " \
               "Science-based nutrition is key!"
    if prediction == "fact":
        return " That’s correct! Good nutrition practice."

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
    return render_template("menu.html")


if __name__ == "__main__":
    app.run(debug=True)
