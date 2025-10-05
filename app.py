######################################################################################################################
######################################################################################################################

import json
import os
from flask import Flask, render_template, request, jsonify
import logging
from chatbot.process import   start_process , hybrid_search
from chatbot.chat_groq import chat_llm
from config.config_file import LOGS_DIR ,DATABASE_DIR
from scraping.scrap import start_scrap
import time
import re
from flask import Flask, render_template, request, redirect, url_for, flash, session
from dotenv import load_dotenv
######################################################################################################################
######################################################################################################################


load_dotenv()

app = Flask(__name__)
USER_DETAILS_FILE = os.path.join(DATABASE_DIR,"user_details.json")
app.secret_key=os.getenv("SECRET_KEY")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "master.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

######################################################################################################################
######################################################################################################################

def load_user_details():
    logger.info(f"Loading user details")
    try:
        if os.path.exists(USER_DETAILS_FILE):
            with open(USER_DETAILS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.info(f"Failed to load user details: {e}")
        return {}


######################################################################################################################
######################################################################################################################

def save_user_details(details):
    logger.info(f"Saving user details")
    try:
        with open(USER_DETAILS_FILE, "w", encoding="utf-8") as f:
            json.dump(details, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.info(f"Failed to save user details: {e}")
        raise


######################################################################################################################
######################################################################################################################




def is_valid_phone(phone: str) -> bool:
    """
    Validates phone numbers:
    - Allows 10 digits
    - Allows optional +91 country code
    - Rejects all-same-digit numbers (e.g., 1111111111)
    """
    pattern = r"^(?:\+91[-\s]?)?(?!([0-9])\1{9}$)[0-9]{10}$"
    return bool(re.fullmatch(pattern, phone.strip()))


######################################################################################################################
######################################################################################################################

def is_valid_email(email: str) -> bool:
    """
    Validates emails:
    - Proper format with @ and domain
    - Restrict domain names to common providers (gmail, yahoo, outlook, hotmail, icloud, etc.)
    """
    allowed_domains = [
        "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
        "icloud.com", "protonmail.com", "live.com", "aol.com"
    ]
    
    # Basic format check
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.fullmatch(pattern, email.strip()):
        return False

    # Check domain restriction
    domain = email.split("@")[-1].lower()
    return domain in allowed_domains


######################################################################################################################
######################################################################################################################

@app.route("/onboard", methods=["POST"])
def onboard_user():
    index, model, chunks, embeddings = start_process()
    logger.info("Taking user details for onboarding")
    data = request.json

    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip().lower()

    # Check required fields
    if not all([name, phone, email]):
        return jsonify({"status": "error", "message": "All fields are required"}), 400

    # Validate phone
    if not is_valid_phone(phone):
        return jsonify({"status": "error", "message": "Invalid phone number"}), 400

    # Validate email
    if not is_valid_email(email):
        return jsonify({"status": "error", "message": "Invalid email address"}), 400

    # Load existing details
    user_details = load_user_details()

    # Check duplicates by email
    if email in user_details:
        return jsonify({"status": "error", "message": "Email already exist."}), 400

    # Check duplicates by phone
    for user in user_details.values():
        if user["phone"] == phone:
            return jsonify({"status": "error", "message": "Phone number already exists."}), 400

    # Save user
    user_details[email] = {"name": name, "phone": phone, "email": email}
    save_user_details(user_details)

    return jsonify({"status": "success", "message": "Thank you! Your details have been saved."}), 200


######################################################################################################################
######################################################################################################################


# --- Global initialization ---
logger.info("Initializing model and index...")
# Global
index = model = corpus = embeddings = None

def initialize():
    global index, model, corpus, embeddings
    if index is None:
        logger.info("Initializing model and index...")
        index, model, corpus, embeddings = start_process()

# Initialize once
initialize()

######################################################################################################################
######################################################################################################################


@app.route("/", methods=["GET", "POST"])
def chat():
    # logger.info("In the main chat screen")

    if request.method == "POST":
        question = request.form.get("question", "").strip()
        if not question:
            return jsonify({"response": "Please enter a question."}), 400

        # Use the preloaded index/model/embeddings
        knowledge = hybrid_search(question, index, model, corpus, embeddings, k=3)
        answer = chat_llm(question, knowledge)

        return jsonify({"response": answer})
    else:
        return render_template("chat.html")
    

######################################################################################################################
######################################################################################################################

@app.route("/logout", methods=["POST"])
def logout():
    return jsonify({"status": "success", "message": "Logged out successfully"})


######################################################################################################################
######################################################################################################################

if __name__ == "__main__":
    logger.info("Starting Flask app...")
    app.run(debug=True)

######################################################################################################################
######################################################################################################################