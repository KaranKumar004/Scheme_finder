"""
whatsapp.py — Twilio WhatsApp webhook handler
Receives WhatsApp messages and routes them through the India Benefits Finder engine.
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


def format_for_whatsapp(matches: list, sender: str) -> str:
    """Format matched schemes, loans, and scholarships for WhatsApp (plain text, no HTML)."""
    if not matches:
        return (
            "❌ No matching benefits found for your profile.\n\n"
            "Please check:\n"
            "• pmjay.gov.in (health cover)\n"
            "• scholarships.gov.in (education)\n"
            "• mudra.org.in (micro business loans)\n\n"
            "Type *START* to try again with different details."
        )

    # Group by type
    schemes = [m for m in matches if m.get("type") == "scheme"]
    loans = [m for m in matches if m.get("type") == "loan"]
    scholarships = [m for m in matches if m.get("type") == "scholarship"]

    lines = [f"🙏 *Namaste! You may qualify for {len(matches)} benefit(s)*:\n"]

    running_idx = 1
    
    def append_section(items, title, icon):
        nonlocal running_idx
        if not items:
            return
        lines.append(f"{icon} *{title}* ({len(items)} matched):")
        for s in items:
            reasons = ", ".join(s.get("match_reasons", []))
            lines.append(
                f"  *{running_idx}. {s['name']}*\n"
                f"   💰 Benefit: {s['benefit_amount']}\n"
                f"   ✅ Why: {reasons}\n"
                f"   🏛 Apply: {s['how_to_apply'][:80]}...\n"
            )
            running_idx += 1
        lines.append("")

    append_section(schemes, "Welfare Schemes", "🏛️")
    append_section(loans, "Concessional Loans", "💰")
    append_section(scholarships, "Scholarships & Aid", "🎓")

    # Dynamic PDF Download URL
    phone_clean = sender.replace("whatsapp:", "").strip()
    pdf_url = f"{request.host_url}api/download_pdf/whatsapp/{phone_clean}"

    lines.append("─────────────────────")
    lines.append(f"📄 *Download Personalized PDF Report*:")
    lines.append(pdf_url)
    lines.append("─────────────────────")
    lines.append("Reply with a *number* (1, 2...) for full details.")
    lines.append("Type *START* to check for someone else.")
    lines.append("\n⚠️ For information only. Verify at official government websites.")

    return "\n".join(lines).strip()


def format_detail_for_whatsapp(scheme: dict) -> str:
    """Format single benefit detail for WhatsApp."""
    s = scheme
    benefit_type = s.get("type", "scheme").upper()
    return (
        f"📋 *[{benefit_type}] {s['name']}*\n\n"
        f"🏛 Ministry: {s.get('ministry', 'Welfare Dept')}\n"
        f"💰 Benefit: {s['benefit_amount']}\n"
        f"📝 About: {s.get('benefit_description', 'N/A')}\n\n"
        f"✅ Eligibility: {s.get('eligibility_note', 'Matches your filters')}\n\n"
        f"📌 How to apply:\n{s.get('how_to_apply', 'Visit block development office')}\n\n"
        f"📄 Documents needed:\n{s.get('documents_needed', 'Aadhaar card')}\n\n"
        f"🔗 Portal: {s.get('url', 'N/A')}\n\n"
        f"─────────────────────\n"
        f"Type *START* to check benefits for someone else."
    )


@whatsapp_webhook.route("/whatsapp", methods=["POST"])
def webhook():
    """Main WhatsApp webhook — receives all incoming messages from Twilio."""
    
    init_db()

    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From", "")  # e.g. whatsapp:+919876543210

    resp = MessagingResponse()
    msg = resp.message()

    if not incoming_msg:
        msg.body("🙏 Namaste! Please describe your situation to find government welfare benefits, loans, and scholarships you qualify for.\n\nExample: 'I am a 22 year old OBC student in Mysuru, Karnataka with family income under 1.5 lakhs'")
        return str(resp)

    # ── RESET command ─────────────────────────────────────────────
    if incoming_msg.upper() in ("START", "RESET", "HI", "HELLO", "NAMASTE", "ನಮಸ್ಕಾರ", "नमस्ते", "வணக்கம்", "నమస్కారం", "नमस्कार"):
        sessions.pop(sender, None)
        msg.body(
            "🙏 *Welcome to India Benefits Finder!*\n\n"
            "I help you find government welfare schemes, loans, and scholarships you qualify for — "
            "free of charge.\n\n"
            "Just describe your situation in any language:\n\n"
            "• *English:* 'I am a widow farmer in Karnataka, income under 1 lakh'\n"
            "• *Hindi:* 'Main Karnataka mein rehti hoon, widow hoon, khet hai'\n"
            "• *Kannada:* 'ನಾನು ಕರ್ನಾಟಕದ ರೈತ, ವಿಧವೆ'\n"
            "• *Tamil:* 'நான் தமிழ்நாட்டில் விவசாயி, வருமானம் 1 லட்சத்திற்கு கீழ்'\n"
            "• *Telugu:* 'నేను ఆంధ్రప్రదేశ్‌లో రైతును, నా ఆదాయం 1 లక్ష లోపు'\n"
            "• *Marathi:* 'मी महाराष्ट्रातील शेतकरी आहे, उत्पन्न १ लाखापेक्षा कमी'\n\n"
            "What is your situation?"
        )
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
                "and I'll find benefits for you."
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
                "'I am a 25 year old OBC student in Mysuru with income below 2 lakhs'"
            )
            return str(resp)

        lang = profile.pop("language", "english")

        # Clean numeric fields
        for field in ("income", "age"):
            if field in profile and profile[field] is not None:
                try:
                    profile[field] = int(profile[field])
                except (ValueError, TypeError):
                    profile[field] = None

        # Match schemes, loans, and scholarships
        matches = match_schemes(profile)

        # Save to session for follow-up detail requests and PDF lookups
        sessions[sender] = {
            "matches": matches,
            "language": lang,
            "profile": profile
        }

        # Generate natural language reply in user's language
        reply = nlp.generate_reply(matches, incoming_msg, language=lang)

        # Append WhatsApp-specific PDF link and detail instructions
        if matches:
            phone_clean = sender.replace("whatsapp:", "").strip()
            pdf_url = f"{request.host_url}api/download_pdf/whatsapp/{phone_clean}"
            
            # Select localized PDF report prompt
            pdf_label = "📄 Download your personalized PDF benefits report"
            if lang == "hindi":
                pdf_label = "📄 अपनी व्यक्तिगत पीडीएफ रिपोर्ट डाउनलोड करें"
            elif lang == "kannada":
                pdf_label = "📄 ನಿಮ್ಮ ವೈಯಕ್ತಿಕ ಪಿಡಿಎಫ್ ವರದಿಯನ್ನು ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ"
            elif lang == "tamil":
                pdf_label = "📄 உங்கள் தனிப்பயனாக்கப்பட்ட PDF அறிக்கையைப் பதிவிறக்கவும்"
            elif lang == "telugu":
                pdf_label = "📄 మీ వ్యక్తిగతీకరించిన PDF నివేదికను డౌన్‌లోడ్ చేయండి"
            elif lang == "marathi":
                pdf_label = "📄 आपला वैयक्तिकृत पीडीएफ अहवाल डाउनलोड करा"

            reply += f"\n\n─────────────────────\n{pdf_label}:\n{pdf_url}\n\nReply with a *number* for full details. Type *START* to check again."

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
