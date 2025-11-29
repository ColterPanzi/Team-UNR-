from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
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


def get_user(db, user_name):
    return db.get("users", {}).get(user_name)


def create_user(db, user_name, password):
    if "users" not in db:
        db["users"] = {}
    if user_name in db["users"]:
        return False

    db["users"][user_name] = {
        "password": password,  # plain text for hackathon only
        "groceries": [],
        "images": []
    }
    return True


def require_login():
    user_name = session.get("user_name")
    if not user_name:
        flash("Please log in first.")
        return None
    return user_name

def format_time(dt=None):
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%d/%m %H:%M")


def add_image_record(user, image_path, ingredients):
    user["images"].append({
        "id": str(uuid4()),
        "image_path": image_path,
        "detected_items": ingredients,
        "uploaded_at": format_time()
    })


def add_grocery_items(user, ingredients):
    now = format_time()
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
# MENU PAGE
# ================================
@app.route("/menu", methods=["GET"])
def menu():
    user_name = session.get("user_name")
    if not user_name:
        flash("Please log in first.")
        return redirect(url_for("login"))

    return render_template("menu.html", user_name=user_name)


# ================================
# GROCERIES
# ================================
@app.route("/groceries", methods=["GET"])
def groceries_page():
    user_name = require_login()
    if not user_name:
        return redirect(url_for("login"))

    db = load_db()
    user = get_user(db, user_name)
    if not user:
        flash("User not found in database. Please log in again.")
        return redirect(url_for("login"))

    groceries = user["groceries"]
    images = user["images"]
    return render_template(
        "groceries.html",
        groceries=groceries,
        images=images,
        user_name=user_name
    )

@app.route("/delete_grocery/<item_id>", methods=["POST"])
def delete_grocery(item_id):
    user_name = require_login()
    if not user_name:
        return redirect(url_for("login"))

    db = load_db()
    user = get_user(db, user_name)

    # filter out the item by id
    user["groceries"] = [g for g in user["groceries"] if g["id"] != item_id]
    save_db(db)

    flash("Ingredient removed.")
    return redirect(url_for("groceries_page"))

@app.route("/delete_image/<image_id>", methods=["POST"])
def delete_image(image_id):
    user_name = require_login()
    if not user_name:
        return redirect(url_for("login"))

    db = load_db()
    user = get_user(db, user_name)

    remaining_images = []
    for img in user["images"]:
        if img["id"] == image_id:
            # Try to remove the actual file from disk
            try:
                if os.path.exists(img["image_path"]):
                    os.remove(img["image_path"])
            except Exception:
                # Ignore file delete errors for now (hackathon life)
                pass
        else:
            remaining_images.append(img)

    user["images"] = remaining_images
    save_db(db)

    flash("Image removed.")
    return redirect(url_for("groceries_page"))


@app.route("/upload_grocery", methods=["POST"])
def upload_grocery():
    user_name = require_login()
    if not user_name:
        return redirect(url_for("login"))

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

    # Temporary dummy ingredients (no AI yet)
    ingredients = ["banana"]

    db = load_db()
    user = get_user(db, user_name)
    add_image_record(user, save_path, ingredients)
    add_grocery_items(user, ingredients)
    save_db(db)

    flash(f"Temporary ingredients saved for {user_name}: {', '.join(ingredients)} (no AI yet)")
    return redirect(url_for("groceries_page"))


# ================================
# GENERATE RECIPES
# ================================
@app.route("/recipes", methods=["GET"])
def recipes_page():
    user_name = require_login()
    if not user_name:
        return redirect(url_for("login"))

    db = load_db()
    user = get_user(db, user_name)
    ingredients = sorted({item["name"] for item in user["groceries"]})

    if ingredients:
        recipes_text = (
            f"In the future, this page will show AI-generated recipes for {user_name} "
            f"using these ingredients:\n\n"
            + ", ".join(ingredients)
        )
    else:
        recipes_text = "No ingredients found yet. Please upload a grocery photo first."

    return render_template(
        "recipes.html",
        ingredients=ingredients,
        recipes_text=recipes_text,
        user_name=user_name
    )
    
    
# ================================
# AUTH HELPERS 
# ================================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        user_name = request.form.get("user_name", "").strip()
        password = request.form.get("password", "").strip()

        if not user_name or not password:
            flash("Username and password are required.")
            return redirect(url_for("signup"))

        db = load_db()
        ok = create_user(db, user_name, password)
        if not ok:
            flash("Username already taken. Please choose another one.")
            return redirect(url_for("signup"))

        save_db(db)
        flash("Account created! Please log in.")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_name = request.form.get("user_name", "").strip()
        password = request.form.get("password", "").strip()

        db = load_db()
        user = get_user(db, user_name)

        if not user or user.get("password") != password:
            flash("Invalid username or password.")
            return redirect(url_for("login"))

        session["user_name"] = user_name
        flash(f"Welcome back, {user_name}!")
        return redirect(url_for("menu"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_name", None)
    flash("You have been logged out.")
    return redirect(url_for("index"))


# ================
# LOAD MAIN PAGE
# ================
@app.route("/", methods=["GET"])
def index():
    return render_template("login.html")


if __name__ == "__main__":
    app.run(debug=True)
