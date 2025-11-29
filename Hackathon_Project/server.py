from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
import re, os, json
from uuid import uuid4
from datetime import datetime
import nltk
from nltk.corpus import stopwords
import openai
from dotenv import load_dotenv
from openai import OpenAI

# =========================
# Setup
# =========================
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

nltk.download("stopwords")

app = Flask(__name__)
app.secret_key = "super-secret-key"

# =========================
# JSON DB config
# =========================
DB_FILE = "db_groceries.json"
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
USER_ID = "demo_user"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# JSON DB functions
# =========================
def load_db():
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
        db["users"][user_id] = {"groceries": [], "images": []}
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

# =========================
# User info collection
# =========================
userInputHistory = []
userInformationDatabase = {"age": None, "height": None, "weight": None, "gender": None}

def ensureCheckUserInformation():
    if userInformationDatabase["age"] is None:
        return "Before we continue, may I know your age?"
    if userInformationDatabase["height"] is None:
        return "Got it! What's your height in cm?"
    if userInformationDatabase["weight"] is None:
        return "Thanks! What's your weight in kg?"
    if userInformationDatabase["gender"] is None:
        return "Lastly, may I know your gender?"
    return None

def ExtractUserData(user_message):
    # Age
    if userInformationDatabase["age"] is None:
        if re.search(r"\b\d{1,2}\b", user_message):
            userInformationDatabase["age"] = int(re.findall(r"\d+", user_message)[0])
            return "Age recorded! Please enter your height in cm (example: 170)."
        return "Please enter a valid age (example: 20)."
    
    # Height
    if userInformationDatabase["height"] is None:
        if re.search(r"\b\d{2,3}\b", user_message):
            userInformationDatabase["height"] = int(re.findall(r"\d+", user_message)[0])
            return "Height recorded! Please enter your weight in kg (example: 65)."
        return "Please enter your height in cm (example: 170)."
    
    # Weight
    if userInformationDatabase["weight"] is None:
        if re.search(r"\b\d{2,3}\b", user_message):
            userInformationDatabase["weight"] = int(re.findall(r"\d+", user_message)[0])
            return "Weight recorded! Please enter male / female."
        return "Please enter your weight in kg (example: 65)."
    
    # Gender
    if userInformationDatabase["gender"] is None:
        if any(g in user_message.lower() for g in ["male", "female"]):
            userInformationDatabase["gender"] = user_message.lower()
            return "Gender recorded!"
        return "Please enter male / female."
    
    return None

# =========================
# Preprocessing
# =========================
def simple_tokenize(text):
    tokens = re.findall(r"\b\w+\b", text.lower())
    filtered = [t for t in tokens if t not in set(stopwords.words("english"))]
    return filtered

# =========================
# Explicit myths for safety
# =========================
MYTH_PATTERNS = [
    "starve myself",
    "detox juice cleanse",
    "all carbs should be avoided",
    "drinking coffee dehydrates",
]

def is_myth(message):
    msg = message.lower()
    for pattern in MYTH_PATTERNS:
        if pattern in msg:
            return True
    return False

# =========================
# GPT integration
# =========================
from openai import OpenAI

# Initialize the client once
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_gpt_reply(user_message):
    tokens = simple_tokenize(user_message)
    preprocessed_message = " ".join(tokens)
    prompt = f"You are a friendly nutrition expert chatbot. Answer clearly and safely:\n{preprocessed_message}"

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI API error:", e)
        return "Sorry, I couldn't generate a response at the moment."

# =========================
# Chatbot logic
# =========================
bot_started = False
def chatbot_reply(user_message):
    global bot_started
    userInputHistory.append(user_message)
    
    # Welcome
    missing_question = ensureCheckUserInformation()
    if not bot_started:
        bot_started = True
        return f"👋 Welcome to NutriBot! {missing_question}" if missing_question else "👋 Welcome to NutriBot!"
    
    # Collect missing info
    if missing_question:
        data_result = ExtractUserData(user_message)
        return data_result if data_result else missing_question

    tokens = simple_tokenize(user_message)

    # Greetings
    if any(greet in tokens for greet in ["hello", "hi", "hey"]):
        return "Hello! How can I help you today?"
    
    # Goodbye
    if any(bye in tokens for bye in ["bye", "goodbye", "end", "quit"]):
        return "Bye! Thank you for using the bot!"
    
    # Explicit myth safety
    if is_myth(user_message):
        return "⚠️ That's a common myth! Not all carbs make you fat, and detox teas don't remove toxins."
    
    # Fallback to GPT
    return generate_gpt_reply(user_message)

# =========================
# Flask endpoints
# =========================
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "")
    reply = chatbot_reply(message)
    return jsonify({"reply": reply})

@app.route("/groceries", methods=["GET"])
def groceries_page():
    db = load_db()
    user = get_user(db, USER_ID)
    return render_template("groceries.html", groceries=user["groceries"], images=user["images"])

@app.route("/upload_grocery", methods=["POST"])
def upload_grocery():
    if "photo" not in request.files:
        flash("No file uploaded.")
        return redirect(url_for("groceries_page"))
    
    file = request.files["photo"]
    if file.filename == "" or not allowed_file(file.filename):
        flash("File not allowed or empty.")
        return redirect(url_for("groceries_page"))
    
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid4()}.{ext}"
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)

    ingredients = ["tomato", "cheese", "spinach"]  # placeholder
    db = load_db()
    user = get_user(db, USER_ID)
    add_image_record(user, save_path, ingredients)
    add_grocery_items(user, ingredients)
    save_db(db)

    flash(f"Temporary ingredients saved: {', '.join(ingredients)}")
    return redirect(url_for("groceries_page"))

@app.route("/recipes", methods=["GET"])
def recipes_page():
    db = load_db()
    user = get_user(db, USER_ID)
    ingredients = sorted({item["name"] for item in user["groceries"]})
    recipes_text = "No ingredients found yet." if not ingredients else \
        "Future AI recipes using these ingredients:\n" + ", ".join(ingredients)
    return render_template("recipes.html", ingredients=ingredients, recipes_text=recipes_text)

@app.route("/", methods=["GET"])
def index():
    return render_template("menu.html")

if __name__ == "__main__":
    app.run(debug=True)
