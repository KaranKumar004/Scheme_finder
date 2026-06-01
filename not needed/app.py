from flask import Flask, render_template, request, jsonify
import os
import sys
import re

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(__file__))

from scheme_db import init_db, get_all_schemes, insert_scheme, delete_scheme
from matcher import match_schemes
import gemini_handler as nlp

app = Flask(__name__)

from whatsapp import whatsapp_webhook
app.register_blueprint(whatsapp_webhook)


@app.route("/")
def home():
    init_db()
    return render_template("index.html")


# ── DEBUG ENDPOINT — visit in browser to diagnose Gemini ─────────────────────
@app.route("/debug/gemini")
def debug_gemini():
    import os as _os
    key = _os.environ.get("GEMINI_API_KEY", "")
    key_preview = (key[:6] + "..." + key[-4:]) if len(key) > 10 else ("SET but short" if key else "NOT SET")

    result = {"api_key_preview": key_preview}

    try:
        test_msg = "I am a widow farmer in Karnataka, income below 1 lakh"
        profile = nlp.extract_profile(test_msg)
        result["extract_profile_result"] = profile
        result["status"] = "OK" if profile else "RETURNED_NONE"
    except Exception as e:
        result["extract_profile_error"] = str(e)
        result["status"] = "ERROR"

    return jsonify(result)
# ─────────────────────────────────────────────────────────────────────────────


@app.route("/api/match", methods=["POST"])
def api_match():
    try:
        profile = request.json or {}
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

        if re.match(r"^\s*\d+\s*$", user_message) and last_matches:
            num = int(user_message.strip())
            reply = nlp.generate_reply(last_matches, user_message, detail_request=num)
            return jsonify({"success": True, "reply": reply, "is_detail": True})

        profile = nlp.extract_profile(user_message)

        # FIX: profile can be None if Gemini fails — handle gracefully
        if not profile:
            return jsonify({
                "success": False,
                "error": "Could not extract profile from message"
            }), 400

        lang = profile.get("language", "english")
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
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)


@app.route("/debug/gemini/raw")
def debug_gemini_raw():
    """Returns the exact raw text Gemini sends back — for diagnosing parse failures."""
    import os as _os
    from google import genai as _genai
    import re as _re

    key = _os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return jsonify({"error": "GEMINI_API_KEY not set"})

    try:
        _client = _genai.Client(api_key=key)
        test_msg = "I am a widow farmer in Karnataka, income below 1 lakh"

        prompt = (
            "You are helping a Government Scheme Finder for India.\n"
            "Extract eligibility info from the user message.\n"
            "Return ONLY valid JSON with NO markdown fences and NO explanation.\n\n"
            'Example: {"state":"karnataka","occupation":"farmer","income":100000,"family":"widow","special":null,"gender":null,"language":"english"}\n\n'
            f"User message:\n{test_msg}"
        )

        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        raw = response.text.strip() if response.text else "(empty response)"

        # Try parsing
        cleaned = _re.sub(r"```json", "", raw)
        cleaned = _re.sub(r"```", "", cleaned).strip()

        try:
            import json as _json
            parsed = _json.loads(cleaned)
            parse_status = "OK"
        except Exception as pe:
            parsed = None
            parse_status = f"PARSE_ERROR: {pe}"

        return jsonify({
            "raw_response": raw,
            "cleaned": cleaned,
            "parse_status": parse_status,
            "parsed": parsed,
        })

    except Exception as e:
        return jsonify({"error": str(e)})