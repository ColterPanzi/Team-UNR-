from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import os
import json
from uuid import uuid4
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super-secret-key"  # needed for flash messages

# ================================
# CONFIG FOR JSON DB
# ================================
DB_FILE = "db_groceries.json"
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
USER_ID = "demo_user"  # single demo user for hackathon

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def load_db():
    """Load groceries JSON DB"""
    if not os.path.exists(DB_FILE):
        return {"users": {}}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)


def get_user(db, user_id):
    if "users" not in db:
        db["users"] = {}
    if user_id not in db["users"]:
        db["users"][user_id] = {
            "groceries": [],
            "images": []
        }
    return db["users"][user_id]


def add_image_record(user, image_path, ingredients):
    user["images"].append({
        "id": str(uuid4()),
        "image_path": image_path,
        "detected_items": ingredients,
        "uploaded_at": datetime.utcnow().isoformat()
    })


def add_grocery_items(user, ingredients):
    now = datetime.utcnow().isoformat()
    for name in ingredients:
        user["groceries"].append({
            "id": str(uuid4()),
            "name": name,
            "quantity": None,
            "unit": None,
            "added_at": now
        })


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


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
    ("drinking fire is good for hydration", "fact"),
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


# ================================
# GROCERIES
# ================================
@app.route("/groceries", methods=["GET"])
def groceries_page():
    db = load_db()
    user = get_user(db, USER_ID)
    groceries = user["groceries"]
    images = user["images"]
    return render_template("groceries.html",
                           groceries=groceries,
                           images=images)


# ================================
# UPLOAD GROCERIES
# ================================
@app.route("/upload_grocery", methods=["POST"])
def upload_grocery():
    if "photo" not in request.files:
        flash("No file uploaded.")
        return redirect(url_for("groceries_page"))

    file = request.files["photo"]
    if file.filename == "":
        flash("No selected file.")
        return redirect(url_for("groceries_page"))

    if not allowed_file(file.filename):
        flash("File type not allowed (use png/jpg/jpeg).")
        return redirect(url_for("groceries_page"))

    # Save image to static/uploads
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid4()}.{ext}"
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)

    ingredients = ["tomato", "cheese", "spinach"]

    db = load_db()
    user = get_user(db, USER_ID)
    add_image_record(user, save_path, ingredients)
    add_grocery_items(user, ingredients)
    save_db(db)

    flash(f"Temporary ingredients saved: {', '.join(ingredients)} (no AI yet)")
    return redirect(url_for("groceries_page"))


# ================================
# GENERATE RECIPES
# ================================
@app.route("/recipes", methods=["GET"])
def recipes_page():
    db = load_db()
    user = get_user(db, USER_ID)
    ingredients = sorted({item["name"] for item in user["groceries"]})

    if ingredients:
        recipes_text = (
            "In the future, this page will show AI-generated recipes using these ingredients:\n\n"
            + ", ".join(ingredients)
        )
    else:
        recipes_text = "No ingredients found yet. Please upload a grocery photo first."

    return render_template("recipes.html",
                           ingredients=ingredients,
                           recipes_text=recipes_text)


# ================
# LOAD MAIN PAGE
# ================
@app.route("/", methods=["GET"])
def index():
    return render_template("menu.html")


if __name__ == "__main__":
    app.run(debug=True)
