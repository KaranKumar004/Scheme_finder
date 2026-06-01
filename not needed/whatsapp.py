"""
whatsapp.py — Twilio WhatsApp webhook handler

Receives WhatsApp messages and routes them through the scheme matching engine.

Add to app.py:
    from whatsapp import whatsapp_webhook
    app.register_blueprint(whatsapp_webhook)
"""

from flask import Blueprint, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
import re
import json

# Import our existing engine
import sys
sys.path.insert(0, os.path.dirname(__file__))
from scheme_db import init_db
import gemini_handler as nlp
from matcher import match_schemes

whatsapp_webhook = Blueprint("whatsapp", __name__)

# In-memory session store (per phone number)
# Stores last matched schemes so user can type "1" for details
sessions = {}


def send_whatsapp(to: str, body: str):
    """Send a WhatsApp message via Twilio REST API."""
    client = Client(
        os.environ.get("TWILIO_ACCOUNT_SID"),
        os.environ.get("TWILIO_AUTH_TOKEN")
    )
    client.messages.create(
        from_=os.environ.get("TWILIO_WHATSAPP_NUMBER"),
        to=to,
        body=body
    )


def format_for_whatsapp(matches: list) -> str:
    """Format matched schemes for WhatsApp (plain text, no HTML)."""
    if not matches:
        return (
            "❌ No matching schemes found for your profile.\n\n"
            "Please check:\n"
            "• pmjay.gov.in (health cover)\n"
            "• scholarships.gov.in (education)\n"
            "• nsap.nic.in (pension schemes)\n\n"
            "Type *START* to try again with different details."
        )

    lines = [f"🙏 Namaste! You may qualify for *{len(matches)} scheme(s)*:\n"]

    for i, s in enumerate(matches, 1):
        reasons = ", ".join(s.get("match_reasons", []))
        # ── FIX 1: include scheme URL / apply link ──────────────────
        scheme_url = s.get("url", "").strip()
        url_line = f"🔗 {scheme_url}\n" if scheme_url else ""
        # ────────────────────────────────────────────────────────────
        lines.append(
            f"*{i}. {s['name']}*\n"
            f"💰 {s['benefit_amount']}\n"
            f"✅ Because: {reasons}\n"
            f"📌 Apply: {s['how_to_apply'][:80]}...\n"
            f"{url_line}"
        )
        lines.append("─────────────────────")

    lines.append("Reply with a *number* (1, 2...) for full details.")
    lines.append("Type *START* to check for someone else.")
    lines.append("\n⚠️ For information only. Verify at official government websites.")
    return "\n".join(lines)


def format_detail_for_whatsapp(scheme: dict) -> str:
    """Format single scheme detail for WhatsApp."""
    s = scheme
    return (
        f"📋 *{s['name']}*\n\n"
        f"🏛 Ministry: {s['ministry']}\n"
        f"💰 Benefit: {s['benefit_amount']}\n"
        f"📝 About: {s['benefit_description']}\n\n"
        f"✅ Eligibility: {s['eligibility_note']}\n\n"
        f"📌 How to apply:\n{s['how_to_apply']}\n\n"
        f"📄 Documents needed:\n{s['documents_needed']}\n\n"
        f"🔗 {s['url']}\n\n"
        f"─────────────────────\n"
        f"Type *START* to check schemes for someone else."
    )


# ── FIX 2: Improved trilingual welcome message ──────────────────────────────
WELCOME_MESSAGE = (
    "🙏 *Scheme Finder में आपका स्वागत है!*\n"
    "🙏 *Scheme Finder ಗೆ ಸ್ವಾಗತ!*\n"
    "🙏 *Welcome to Scheme Finder!*\n\n"
    "I find free government welfare schemes you qualify for.\n"
    "ಸರ್ಕಾರಿ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಲು ನಿಮ್ಮ ಪರಿಸ್ಥಿತಿ ಹೇಳಿ.\n"
    "अपनी स्थिति बताएं और मैं आपके लिए सही योजनाएं ढूंढूंगा।\n\n"
    "─────────────────────\n"
    "💬 *Type in any language — examples:*\n\n"
    "🇮🇳 *Hindi:*\n"
    "_मैं कर्नाटक में किसान हूँ, विधवा हूँ, आय 80,000 रुपये है_\n\n"
    "🇮🇳 *Kannada:*\n"
    "_ನಾನು ಕರ್ನಾಟಕದ ರೈತ, ವಿಧವೆ, ವಾರ್ಷಿಕ ಆದಾಯ 80,000 ರೂ_\n\n"
    "🇬🇧 *English:*\n"
    "_I am a widow farmer in Karnataka, income 80,000 per year_\n\n"
    "─────────────────────\n"
    "Include: *state, occupation, income, family situation*\n"
    "What is your situation?"
)
# ────────────────────────────────────────────────────────────────────────────


@whatsapp_webhook.route("/whatsapp", methods=["POST"])
def webhook():
    """Main WhatsApp webhook — receives all incoming messages from Twilio."""
    init_db()

    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From", "")   # e.g. whatsapp:+919876543210

    resp = MessagingResponse()
    msg = resp.message()

    if not incoming_msg:
        msg.body(
            "🙏 Namaste! Please describe your situation to find government schemes.\n\n"
            "Type *START* to see examples."
        )
        return str(resp)

    # ── RESET command ─────────────────────────────────────────────
    if incoming_msg.upper() in (
        "START", "RESET", "HI", "HELLO", "NAMASTE",
        "ನಮಸ್ಕಾರ", "नमस्ते"
    ):
        sessions.pop(sender, None)
        msg.body(WELCOME_MESSAGE)
        return str(resp)

    # ── Detail request (user types a number) ──────────────────────
    if re.match(r"^\s*\d+\s*$", incoming_msg):
        n = int(incoming_msg.strip())
        last_matches = sessions.get(sender, {}).get("matches", [])

        if last_matches:
            idx = n - 1
            if 0 <= idx < len(last_matches):
                reply = format_detail_for_whatsapp(last_matches[idx])
            else:
                reply = f"⚠️ Please enter a number between 1 and {len(last_matches)}."
        else:
            # No session — treat as new message
            reply = (
                "🙏 Type *START* to begin, then describe your situation "
                "and I'll find schemes for you."
            )

        msg.body(reply)
        return str(resp)

    # ── New profile message ────────────────────────────────────────
    try:
        # Extract profile using Gemini
        profile = nlp.extract_profile(incoming_msg)

        if not profile:
            msg.body(
                "🙏 Sorry, I couldn't understand that.\n\n"
                "Please try describing your situation like:\n"
                "'I am a widow in Karnataka with farming land and income below 1 lakh'\n\n"
                "Type *START* to see more examples."
            )
            return str(resp)

        lang = profile.pop("language", "english")

        # Clean income
        if "income" in profile and profile["income"] is not None:
            try:
                profile["income"] = int(profile["income"])
            except (ValueError, TypeError):
                profile["income"] = None

        # Match schemes
        matches = match_schemes(profile)

        # Save to session for follow-up detail requests
        sessions[sender] = {
            "matches": matches,
            "language": lang,
            "profile": profile
        }

        # Generate natural language reply in user's language
        reply = nlp.generate_reply(matches, incoming_msg, language=lang)

        # Append WhatsApp-specific instructions
        if matches:
            reply += (
                "\n\n─────────────────────\n"
                "Reply with a *number* for full details + apply link.\n"
                "Type *START* to check again."
            )

        msg.body(reply)

    except Exception as e:
        print(f"WhatsApp webhook error: {e}")
        msg.body(
            "🙏 Something went wrong on our end. Please try again.\n"
            "Type *START* to begin fresh."
        )

    return str(resp)


@whatsapp_webhook.route("/whatsapp/status", methods=["POST"])
def status_callback():
    """Twilio delivery status callback — just acknowledge."""
    return "", 204
