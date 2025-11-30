from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
import re
import os
import json
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


def get_user(db, user_name):
    return db.get("users", {}).get(user_name)


def create_user(db, user_name, password):
    if "users" not in db:
        db["users"] = {}
    if user_name in db["users"]:
        return False

    db["users"][user_name] = {
        "password": password,
        "profile": {
            "age": None,
            "height": None, 
            "weight": None,
            "gender": None,
            "completed": False,
            # Add new optional fields
            "email": "",
            "phone": "",
            "country": ""
        },
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

# Initialize the client once
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_gpt_reply(user_message):
    """Enhanced GPT prompt with user profile data"""
    
    # Get user profile data
    user_profile = None
    user_name = session.get("user_name")
    if user_name:
        db = load_db()
        user = get_user(db, user_name)
        if user and user["profile"]["completed"]:
            user_profile = user["profile"]
    
    # Build prompt with user data
    if user_profile:
        profile_info = f"""
USER PROFILE:
- Age: {user_profile['age']}
- Height: {user_profile['height']} cm
- Weight: {user_profile['weight']} kg  
- Gender: {user_profile['gender']}
"""
    else:
        profile_info = "USER PROFILE: No profile data available."
    
    prompt = f"""You are NutriBot, a friendly nutrition and health expert chatbot.

{profile_info}

USER QUESTION: "{user_message}"

IMPORTANT: 
- Only answer if this question is related to nutrition, diet, food, health, fitness, or healthy living
- If user profile is available, use it to provide personalized advice
- If the question is NOT related to these topics, politely decline and redirect back to nutrition/health topics
- Otherwise, provide a helpful, evidence-based response about nutrition and health

Your response:"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI API error:", e)
        return "Sorry, I couldn't generate a response at the moment."
    

bot_started = False

def ensure_user_profile(user):
    """Make sure user has the complete profile structure"""
    if "profile" not in user:
        user["profile"] = {}
    
    # Ensure all profile fields exist
    profile_fields = ["age", "height", "weight", "gender", "completed", "email", "phone", "country"]
    for field in profile_fields:
        if field not in user["profile"]:
            if field == "completed":
                user["profile"][field] = False
            else:
                user["profile"][field] = None if field in ["age", "height", "weight"] else ""
    
    return user

def chatbot_reply(user_message):
    # Use session to track if bot started for this user
    if 'bot_started' not in session:
        session['bot_started'] = False
    
    userInputHistory.append(user_message)
    
    # Check if user has completed profile
    user_name = session.get("user_name")
    if user_name:
        db = load_db()
        user = get_user(db, user_name)
        if user and not user["profile"]["completed"]:
            return "Please complete your profile setup first from the main menu! 🎯"
    
    # Welcome (only show if profile is complete and first message)
    if not session['bot_started']:
        session['bot_started'] = True
        return "👋 Welcome to NutriBot! I can see your profile is set up. Ask me anything about nutrition, diet, or healthy living! 🍎"
    
    tokens = simple_tokenize(user_message)

    # Greetings
    if any(greet in tokens for greet in ["hello", "hi", "hey"]):
        return "Hello! I'm NutriBot, your nutrition assistant! Ask me about food, diet, exercise, or healthy living. 🍎"
    
    # Goodbye
    if any(bye in tokens for bye in ["bye", "goodbye", "end", "quit"]):
        return "Bye! Stay healthy! 🥦"
    
    # Fallback to GPT
    return generate_gpt_reply(user_message)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "")
    reply = chatbot_reply(message)
    return jsonify({"reply": reply})

@app.route("/profile", methods=["GET", "POST"])
def profile():
    user_name = require_login()
    if not user_name:
        return redirect(url_for("login"))

    db = load_db()
    user = get_user(db, user_name)
    user = ensure_user_profile(user)  # Add this line
    
    if request.method == "POST":
        # Update profile information
        user["profile"]["email"] = request.form.get("email", "")
        user["profile"]["phone"] = request.form.get("phone", "")
        user["profile"]["country"] = request.form.get("country", "")
        
        save_db(db)
        flash("Profile updated successfully! ✅")
        return redirect(url_for("profile"))
    
    return render_template("profile.html", user=user, user_name=user_name)

@app.route("/profile-setup", methods=["GET", "POST"])
def profile_setup():
    user_name = require_login()
    if not user_name:
        return redirect(url_for("login"))
    
    db = load_db()
    user = get_user(db, user_name)
    
    if request.method == "POST":
        # Get form data
        age = request.form.get("age")
        height = request.form.get("height") 
        weight = request.form.get("weight")
        gender = request.form.get("gender")
        
        # Validate and save
        if age and height and weight and gender:
            user["profile"]["age"] = int(age)
            user["profile"]["height"] = int(height)
            user["profile"]["weight"] = int(weight)
            user["profile"]["gender"] = gender
            user["profile"]["completed"] = True
            
            save_db(db)
            flash("Profile setup complete! Welcome to NutriBot! 🎉")
            return redirect(url_for("menu"))
        else:
            flash("Please fill in all fields.")
    
    # Check if profile already completed
    if user["profile"]["completed"]:
        flash("Your profile is already set up!")
        return redirect(url_for("menu"))
    
    return render_template("profile_setup.html", user_name=user_name)

@app.route("/menu", methods=["GET"])
def menu():
    user_name = session.get("user_name")
    if not user_name:
        flash("Please log in first.")
        return redirect(url_for("login"))

    # Check if profile is complete
    db = load_db()
    user = get_user(db, user_name)
    if user and not user["profile"]["completed"]:
        return redirect(url_for("profile_setup"))

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
    if file.filename == "" or not allowed_file(file.filename):
        flash("File not allowed or empty.")
        return redirect(url_for("groceries_page"))
    
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

@app.route("/recipes", methods=["GET"])
def recipes_page():
    user_name = require_login()
    if not user_name:
        return redirect(url_for("login"))

    db = load_db()
    user = get_user(db, user_name)
    ingredients = sorted({item["name"] for item in user["groceries"]})
    recipes_text = "No ingredients found yet." if not ingredients else \
        "Future AI recipes using these ingredients:\n" + ", ".join(ingredients)
    return render_template("recipes.html", ingredients=ingredients, recipes_text=recipes_text)

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
        session["user_name"] = user_name  # Log them in
        flash("Account created! Please complete your profile.")
        return redirect(url_for("profile_setup"))

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
