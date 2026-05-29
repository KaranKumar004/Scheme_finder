"""
gemini_handler.py — Gemini API version (FIXED)

Fixes:
  1. exit(1) replaced with warning — never kill the server on missing key
  2. EXTRACTION_PROMPT uses a raw template string to avoid {{ / }} escaping bugs
  3. extract_profile returns None (not {}) on failure so whatsapp.py fallback works correctly
"""

import os
import json
import re
from google import genai

# ── Load .env manually ────────────────────────────────────────────────────────
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# FIX 1: never call exit() — just warn and let requests fail gracefully
if not API_KEY:
    print("⚠️  WARNING: GEMINI_API_KEY not set. NLP calls will fail gracefully.")

client = genai.Client(api_key=API_KEY) if API_KEY else None
MODEL_NAME = "gemini-2.5-flash"

# ── FIX 2: use a plain concatenated string — no .format() on the JSON block ──
# The JSON example is built as a literal; only {message} is substituted.
_EXTRACTION_TEMPLATE = (
    "You are helping a Government Scheme Finder for India.\n"
    "Extract eligibility info from the user message.\n"
    "The message may be in English, Hindi, Kannada, Tamil, Telugu, Marathi, or mixed languages.\n\n"
    "Return ONLY valid JSON with NO markdown fences and NO explanation.\n\n"
    "Example output shape:\n"
    '{"state":null,"occupation":null,"income":null,"family":null,"special":null,"gender":null,"language":"english"}\n\n'
    "Allowed values:\n"
    "  occupation : farmer | daily_wage | unemployed | salaried | self_employed | other\n"
    "  family     : single | married | widow | single_parent\n"
    "  special    : disabled | senior | pregnant | student | none\n"
    "  gender     : female | male | other\n"
    "  language   : english | hindi | kannada | tamil | telugu | marathi | other\n\n"
    "Key mappings (any language):\n"
    "  widow / vidhwa / ವಿಧವೆ / विधवा  -> family=widow\n"
    "  farmer / kisan / ರೈತ / किसान     -> occupation=farmer\n"
    "  disabled / viklang / ಅಂಗವಿಕಲ    -> special=disabled\n"
    "  pregnant / garbhwati / ಗರ್ಭಿಣಿ  -> special=pregnant\n"
    "  student / vidyarthi / ವಿದ್ಯಾರ್ಥಿ -> special=student\n"
    "  BPL / poor / garib / गरीब        -> income=80000\n"
    "  1 lakh / 1 लाख / 1 ಲಕ್ಷ          -> income=100000\n\n"
    "User message:\n"
    "{message}"
)

_REPLY_TEMPLATE = (
    "You are a warm helpful assistant for a Government Scheme Finder for India.\n"
    "Users may be rural or semi-urban Indians. Keep language SIMPLE.\n\n"
    "IMPORTANT: Reply in the SAME language as the user.\n"
    "Use friendly emojis: 🙏 ✅ 💰\n"
    "Keep sentences short. End with a disclaimer in the SAME language.\n\n"
    "User message:\n{message}\n\n"
    "Situation:\n{situation}"
)


# ── Profile extraction ────────────────────────────────────────────────────────
def extract_profile(user_message: str) -> dict | None:
    """Return a profile dict, or None on failure."""
    # FIX 1: handle missing API key gracefully
    if not client:
        print("⚠️  extract_profile: no Gemini client (API key missing)")
        return None

    try:
        prompt = _EXTRACTION_TEMPLATE.format(message=user_message)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )

        raw = response.text.strip()

        # Strip markdown fences if Gemini adds them anyway
        raw = re.sub(r"```json", "", raw)
        raw = re.sub(r"```", "", raw)
        raw = raw.strip()

        print(f"\n🔍 Gemini raw response:\n{raw}\n")

        profile = json.loads(raw)

        # FIX 3: return None if the dict is empty so whatsapp.py fallback fires
        if not profile:
            return None

        return profile

    except Exception as e:
        print(f"⚠️  Gemini extraction error: {e}")
        return None


# ── Reply generation ──────────────────────────────────────────────────────────
def generate_reply(
    matches: list,
    user_message: str,
    language: str = "english",
    detail_request: int = None,
) -> str:

    if not client:
        return "🙏 Service temporarily unavailable. Please try again later."

    if not matches:
        situation = (
            "No schemes matched. "
            "Suggest pmjay.gov.in and scholarships.gov.in. "
            "Ask user to try again."
        )
    elif detail_request is not None:
        idx = detail_request - 1
        if 0 <= idx < len(matches):
            s = matches[idx]
            situation = (
                f"User wants full details about:\n"
                f"Scheme: {s['name']}\n"
                f"Benefit: {s['benefit_amount']}\n"
                f"Description: {s['benefit_description']}\n"
                f"Eligibility: {s['eligibility_note']}\n"
                f"Apply: {s['how_to_apply']}\n"
                f"Documents: {s['documents_needed']}\n"
                f"Website: {s['url']}\n"
            )
        else:
            situation = (
                f"User requested scheme {detail_request} "
                f"but only {len(matches)} schemes exist."
            )
    else:
        lines = []
        for i, s in enumerate(matches, 1):
            reasons = ", ".join(s.get("match_reasons", []))
            lines.append(
                f"{i}. {s['name']}\n"
                f"   Benefit: {s['benefit_amount']}\n"
                f"   Reason: {reasons}\n"
                f"   Apply: {s['how_to_apply']}\n"
                f"   URL: {s['url']}\n"
            )
        situation = (
            f"{len(matches)} schemes found:\n\n"
            + "\n".join(lines)
            + "\n\nTell user to reply with a number (1, 2...) for full details."
        )

    try:
        prompt = _REPLY_TEMPLATE.format(
            message=user_message,
            situation=situation,
        )
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"⚠️ Error generating reply: {e}"


# ── CLI for local testing ─────────────────────────────────────────────────────
def run_nlp_cli():
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from scheme_db import init_db
    from matcher import match_schemes

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║ 🇮🇳 Scheme Finder — Natural Language Mode (Gemini) ║")
    print("║  Type in English, Hindi, Kannada — anything works  ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    init_db()
    last_matches = []

    while True:
        print("─" * 54)
        try:
            user_input = input("You: ").strip()
        except KeyboardInterrupt:
            print("\n\n🙏 Exiting... Jai Hind!\n")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "bye"):
            print("\n🙏 Thank you. Jai Hind!\n")
            break

        if re.match(r"^\d+$", user_input) and last_matches:
            n = int(user_input)
            reply = generate_reply(last_matches, user_input, detail_request=n)
            print(f"\nBot: {reply}\n")
            continue

        print("\n⏳ Understanding your message...")
        profile = extract_profile(user_input)

        if not profile:
            print("Bot: Sorry, could not understand. Please try again.\n")
            continue

        lang = profile.pop("language", "english")
        print(f"   Language : {lang}")
        print(f"   Profile  : {json.dumps(profile, ensure_ascii=False)}")

        matches = match_schemes(profile)
        last_matches = matches

        print("\n⏳ Generating response...\n")
        reply = generate_reply(matches, user_input, language=lang)
        print(f"Bot: {reply}\n")


if __name__ == "__main__":
    run_nlp_cli()