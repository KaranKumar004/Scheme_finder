from flask import Flask, render_template, request, jsonify
import os
import sys
import re

# Force UTF-8 stdout/stderr on Windows to prevent UnicodeEncodeError
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure we can import siblings
sys.path.insert(0, os.path.dirname(__file__))

from scheme_db import init_db, get_all_schemes, insert_scheme, delete_scheme
from matcher import match_schemes
import test as nlp

app = Flask(__name__)

@app.route("/")
def home():
    # Make sure DB is populated
    init_db()
    return render_template("index.html")

@app.route("/api/match", methods=["POST"])
def api_match():
    try:
        profile = request.json or {}
        # Ensure income is an integer
        if "income" in profile and profile["income"] is not None:
            try:
                profile["income"] = int(profile["income"])
            except ValueError:
                profile["income"] = None
        matches = match_schemes(profile)
        return jsonify({"success": True, "matches": matches})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        data = request.json or {}
        user_message = data.get("message", "").strip()
        last_matches = data.get("last_matches", [])
        
        if not user_message:
            return jsonify({"success": False, "error": "Message is required"}), 400

        # Check if it's a detail request (a plain number)
        if re.match(r"^\s*\d+\s*$", user_message) and last_matches:
            num = int(user_message.strip())
            reply = nlp.generate_reply(last_matches, user_message, detail_request=num)
            return jsonify({
                "success": True,
                "reply": reply,
                "is_detail": True
            })

        # Otherwise, perform full profile extraction and matching
        profile = nlp.extract_profile(user_message)
        lang = profile.get("language", "english")
        
        # Clean language and other attributes
        clean_profile = {k: v for k, v in profile.items() if k != "language"}
        if "income" in clean_profile and clean_profile["income"] is not None:
            try:
                clean_profile["income"] = int(clean_profile["income"])
            except ValueError:
                clean_profile["income"] = None

        matches = match_schemes(clean_profile)
        reply = nlp.generate_reply(matches, user_message, language=lang)

        return jsonify({
            "success": True,
            "reply": reply,
            "profile": clean_profile,
            "matches": matches,
            "language": lang,
            "is_detail": False
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/schemes", methods=["GET", "POST"])
def api_schemes():
    if request.method == "POST":
        try:
            scheme_data = request.json or {}
            if not scheme_data.get("name"):
                return jsonify({"success": False, "error": "Scheme name is required"}), 400
            new_id = insert_scheme(scheme_data)
            return jsonify({"success": True, "id": new_id, "message": "Scheme added successfully"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400
    else:
        try:
            schemes = [dict(row) for row in get_all_schemes()]
            return jsonify({"success": True, "schemes": schemes})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/schemes/<int:scheme_id>", methods=["DELETE"])
def api_delete_scheme(scheme_id):
    try:
        success = delete_scheme(scheme_id)
        if success:
            return jsonify({"success": True, "message": "Scheme deleted successfully"})
        else:
            return jsonify({"success": False, "error": "Scheme not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
