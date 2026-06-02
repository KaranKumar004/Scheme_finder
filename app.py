from flask import Flask, render_template, request, jsonify, send_file
import os
import sys
import re

# Force UTF-8 stdout/stderr on Windows to prevent UnicodeEncodeError
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure we can import siblings
sys.path.insert(0, os.path.dirname(__file__))

from scheme_db import init_db, get_all_benefits, insert_benefit, delete_benefit
from matcher import match_schemes
import gemini_handler as nlp
from whatsapp import whatsapp_webhook, sessions
from pdf_generator import generate_benefits_pdf

app = Flask(__name__)

# Register Twilio WhatsApp webhook blueprint
app.register_blueprint(whatsapp_webhook)

@app.route("/")
def home():
    # Make sure DB is populated
    init_db()
    return render_template("index.html")

@app.route("/api/match", methods=["POST"])
def api_match():
    try:
        profile = request.json or {}
        # Clean numeric fields
        for field in ("income", "age"):
            if field in profile and profile[field] is not None:
                try:
                    profile[field] = int(profile[field])
                except (ValueError, TypeError):
                    profile[field] = None
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
        for field in ("income", "age"):
            if field in clean_profile and clean_profile[field] is not None:
                try:
                    clean_profile[field] = int(clean_profile[field])
                except (ValueError, TypeError):
                    clean_profile[field] = None

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
    table_type = request.args.get("type", "scheme").strip().lower()
    table_name = "schemes"
    if table_type == "loan":
        table_name = "loans"
    elif table_type == "scholarship":
        table_name = "scholarships"

    if request.method == "POST":
        try:
            scheme_data = request.json or {}
            if not scheme_data.get("name"):
                return jsonify({"success": False, "error": "Welfare title is required"}), 400
            new_id = insert_benefit(table_name, scheme_data)
            return jsonify({"success": True, "id": new_id, "message": "Benefit entry added successfully"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400
    else:
        try:
            benefits = [dict(row) for row in get_all_benefits(table_name)]
            return jsonify({"success": True, "schemes": benefits})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/schemes/<int:scheme_id>", methods=["DELETE"])
def api_delete_scheme(scheme_id):
    table_type = request.args.get("type", "scheme").strip().lower()
    table_name = "schemes"
    if table_type == "loan":
        table_name = "loans"
    elif table_type == "scholarship":
        table_name = "scholarships"

    try:
        success = delete_benefit(table_name, scheme_id)
        if success:
            return jsonify({"success": True, "message": "Welfare entry deleted successfully"})
        else:
            return jsonify({"success": False, "error": "Entry not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ─── PDF REPORT GENERATION ROUTES ─────────────────────────────────────────────

@app.route("/api/download_pdf", methods=["POST"])
def download_pdf():
    try:
        data = request.json or {}
        profile = data.get("profile", {})
        
        # Re-evaluate matches to ensure 100% consistency and accuracy
        clean_profile = {k: v for k, v in profile.items() if k != "language"}
        for field in ("income", "age"):
            if field in clean_profile and clean_profile[field] is not None:
                try:
                    clean_profile[field] = int(clean_profile[field])
                except (ValueError, TypeError):
                    clean_profile[field] = None

        matches = match_schemes(clean_profile)
        pdf_buf = generate_benefits_pdf(clean_profile, matches)
        
        return send_file(
            pdf_buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="India_Benefits_Finder_Report.pdf"
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/download_pdf/whatsapp/<phone>")
def download_pdf_whatsapp(phone):
    try:
        session_data = None
        # Look up phone number in the active in-memory WhatsApp sessions
        for key, val in sessions.items():
            if phone in key or key in phone:
                session_data = val
                break
                
        if not session_data:
            # Fallback to an empty profile and matches if session not found
            profile = {}
            matches = []
        else:
            profile = session_data.get("profile", {})
            matches = session_data.get("matches", [])
            
        # Clean profile
        clean_profile = {k: v for k, v in profile.items() if k != "language"}
        for field in ("income", "age"):
            if field in clean_profile and clean_profile[field] is not None:
                try:
                    clean_profile[field] = int(clean_profile[field])
                except (ValueError, TypeError):
                    clean_profile[field] = None
                    
        pdf_buf = generate_benefits_pdf(clean_profile, matches)
        
        return send_file(
            pdf_buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"India_Benefits_Finder_Report_{phone}.pdf"
        )
    except Exception as e:
        return f"⚠️ Error compiling PDF report: {e}", 500

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
