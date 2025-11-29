from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import os
import json
from uuid import uuid4
from datetime import datetime
import re 
import nltk 
from nltk.tokenize import word_tokenize 
from nltk.stem import WordNetLemmatizer 
from nltk.corpus import stopwords

# Download stopwords ONCE (safe to leave here)
nltk.download("stopwords")


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
    ("fruit has too much sugar to be healthy", "myth"),
    ("all carbs should be avoided", "myth"),
    ("bread is bad for you", "myth"),
    ("gluten-free diets help everyone lose weight", "myth"),
    ("eating fat makes you fat", "myth"),
    ("cholesterol in food causes high cholesterol", "myth"),
    ("salt is always bad for you", "myth"),
    ("organic food is always more nutritious", "myth"),
    ("you must drink 8 cups of water exactly every day", "myth"),
    ("starving yourself helps you lose weight fast", "myth"),
    ("red meat is always bad for health", "myth"),
    ("detox juices cleanse your body", "myth"),
    ("all processed foods are harmful", "myth"),
    ("eggs increase your risk of heart disease", "myth"),
    ("cold water slows your digestion", "myth"),
    ("only animal protein builds muscle", "myth"),
    ("eating late at night automatically makes you gain weight", "myth"),
    ("natural sugar is always healthier than added sugar", "myth"),
    ("drinking coffee dehydrates you", "myth"),
    ("you need supplements to get enough nutrients", "myth"),
    ("eating spicy food causes ulcers", "myth"),
    ("a detox diet resets your metabolism", "myth"),
    ("cutting out all fat is healthy", "myth"),
    ("carrots worsen eyesight", "myth"),
    ("low-carb diets are the only way to lose weight", "myth"),
    ("you must avoid rice to stay slim", "myth"),
    ("eating meat daily is unhealthy for everyone", "myth"),
    ("apple cider vinegar burns belly fat", "myth"),
    ("celery juice cures diseases", "myth"),

    ("greens are rich in vitamins", "fact"),
    ("whole foods generally contain more nutrients", "fact"),
    ("exercise combined with good nutrition improves results", "fact"),
    ("brown rice and white rice have similar calories", "fact"),
    ("frozen vegetables retain nutrients", "fact"),
    ("water helps regulate body temperature", "fact"),
    ("probiotics support gut health", "fact"),
    ("eating enough protein helps prevent muscle loss", "fact"),
    ("healthy snacks can support energy throughout the day", "fact"),
    ("plant-based diets can be nutritionally complete", "fact"),
    ("dark chocolate contains antioxidants", "fact"),
    ("moderate coffee consumption can be healthy", "fact"),
    ("nuts provide healthy fats", "fact"),
    ("eggs are a good source of protein", "fact"),
    ("carbs are the body's main energy source", "fact"),
    ("vitamin D supports immune function", "fact"),
    ("bananas provide potassium", "fact"),
    ("water is essential for metabolic processes", "fact"),
    ("walking improves cardiovascular health", "fact"),
    ("strength training builds lean muscle", "fact"),
    ("breakfast is optional depending on personal needs", "fact"),
    ("nutrition needs vary from person to person", "fact"),
    ("hydration supports cognitive function", "fact")
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

userInputHistory = []  # Stores user's inputs

userInfomationDatabase = {
    "age": None,
    "height": None,
    "weight": None,
    "gender": None
}

# Check for user data
def ensureCheckUserInformation():
    if userInfomationDatabase["age"] is None:
        return "Before we continue, may I know your age?"
    if userInfomationDatabase["height"] is None:
        return "Got it! What's your height in cm?"
    if userInfomationDatabase["weight"] is None:
        return "Thanks! What's your weight in kg?"
    if userInfomationDatabase["gender"] is None:
        return "Lastly, may I know your gender?"
    return None  # everything collected

def ExtractUserData(user_message):
    # Age
    if userInfomationDatabase["age"] is None:
        if re.search(r"\b\d{1,2}\b", user_message):
            userInfomationDatabase["age"] = int(re.findall(r"\d+", user_message)[0])
            return "Age recorded! Please enter your height in cm (example: 170)."

        return "Please enter a valid age (example: 20)."

    # Height
    if userInfomationDatabase["height"] is None:
        if re.search(r"\b\d{2,3}\b", user_message):
            userInfomationDatabase["height"] = int(re.findall(r"\d+", user_message)[0])
            return "Height recorded! Please enter your weight in kg (example: 65)."
        return "Please enter your height in cm (example: 170)."

    # Weight
    if userInfomationDatabase["weight"] is None:
        if re.search(r"\b\d{2,3}\b", user_message):
            userInfomationDatabase["weight"] = int(re.findall(r"\d+", user_message)[0])
            return "Weight recorded! Please enter male / female."
        return "Please enter your weight in kg (example: 65)."

    # Gender
    if userInfomationDatabase["gender"] is None:
        if any(g in user_message.lower() for g in ["male", "female"]):
            userInfomationDatabase["gender"] = user_message.lower()
            return "Gender recorded!"
        return "Please enter male / female."

    return None  # nothing to record

def simple_tokenize(text):
    # Lowercase all input
    tokens = re.findall(r"\b\w+\b", text.lower())
    # Filters and remove common stop words using nltk 
    filtered = [t for t in tokens if t not in set(stopwords.words("english"))]

    return filtered

bot_started = False

def chatbot_reply(user_message):
    global bot_started
    userInputHistory.append(user_message)
    tokens = simple_tokenize(user_message)
    # First-time welcome
    # Check first missing user info
    missing_question = ensureCheckUserInformation()

    # First-time welcome
    if not bot_started:
        bot_started = True
        if missing_question:
            return f"👋 Welcome to NutriBot! {missing_question}"
        else:
            return "👋 Welcome to NutriBot!"

    # Collect User Data
    if missing_question:
        data_result = ExtractUserData(user_message)
        if data_result:
            return data_result
        return missing_question

    # Prediction 
    prediction = myth_model.predict([user_message])[0]  # "myth" or "fact"

    # Debugging
    print(userInfomationDatabase)
    print("Tokens:", tokens)

    # Greeting detection
    if any(greet in tokens for greet in ["hello", "hi", "hey"]):
        return "Hello! How can I help you today?"

    # Goodbye
    if any(bye in tokens for bye in ["bye", "goodbye", "end", "quit"]):
        return "Bye! Thank you for using the bot!"

    # Myth/Facts
    if prediction == "myth":
        return ("⚠️ That's a common myth! Here's the truth: "
                "Not all carbs make you fat, and detox teas don't remove toxins.")

    if prediction == "fact":
        return "✅ Correct! Good nutrition practice."

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
