"""
claude_handler.py — Gemini API version (UPDATED)
Works with latest google-genai SDK

Install:
pip install -U google-genai

Add to .env:
GEMINI_API_KEY=your_key_here
"""

import os
import json
import re
from google import genai

# =========================================================
# LOAD .ENV MANUALLY
# =========================================================

_env_path = os.path.join(os.path.dirname(__file__), ".env")

if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

if not API_KEY:
    print("❌ GEMINI_API_KEY not found.")
    print("Create .env file with:")
    print("GEMINI_API_KEY=your_key_here")
    print("⚠️  WARNING: GEMINI_API_KEY not set. NLP calls will fail gracefully.")

# =========================================================
# GEMINI CLIENT
# =========================================================

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-2.5-flash"

# =========================================================
# EXTRACTION PROMPT
# =========================================================

EXTRACTION_PROMPT = """
You are helping a Government Scheme Finder for India.

Extract eligibility info from the user message.
The message may be in English, Hindi, Kannada,
Tamil, Telugu, Marathi, or mixed languages.

Return ONLY valid JSON.
No markdown.
No explanation.

{{
  "state": null,
  "occupation": null,
  "income": null,
  "family": null,
  "special": null,
  "gender": null,
  "language": "english"
}}

Allowed occupation:
farmer
daily_wage
unemployed
salaried
self_employed
other

Allowed family:
single
married
widow
single_parent

Allowed special:
disabled
senior
pregnant
student
none

Allowed gender:
female
male
other

Language values:
english
hindi
kannada
tamil
telugu
marathi
other

Mappings:
- widow / vidhwa / ವಿಧವೆ -> widow
- farmer / kisan / ರೈತ -> farmer
- disabled / viklang / ಅಂಗವಿಕಲ -> disabled
- pregnant / garbhwati / ಗರ್ಭಿಣಿ -> pregnant
- student / vidyarthi / ವಿದ್ಯಾರ್ಥಿ -> student
- BPL / poor / garib -> income=80000
- 1 lakh -> income=100000

User message:
{message}
"""

# =========================================================
# REPLY PROMPT
# =========================================================

REPLY_PROMPT = """
You are a warm helpful assistant for a Government Scheme Finder for India.

Users may be rural or semi-urban Indians.
Keep language SIMPLE.

IMPORTANT:
Reply in the SAME language as the user.

Use:
🙏 ✅ 💰

Keep sentences short.

End with a warning/disclaimer in the SAME language.

User message:
{message}

Situation:
{situation}
"""

# =========================================================
# PROFILE EXTRACTION
# =========================================================

def extract_profile(user_message: str) -> dict:

    try:

        prompt = EXTRACTION_PROMPT.format(
            message=user_message
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )

        raw = response.text.strip()

        # Cleanup markdown if Gemini adds it
        raw = re.sub(r"```json", "", raw)
        raw = re.sub(r"```", "", raw)
        raw = raw.strip()

        # DEBUG
        print("\n🔍 Raw Gemini Response:")
        print(raw)

        return json.loads(raw)

    except Exception as e:
        print(f"⚠️ Gemini extraction error: {e}")
        return None

# =========================================================
# GENERATE USER RESPONSE
# =========================================================

def generate_reply(
    matches: list,
    user_message: str,
    language: str = "english",
    detail_request: int = None
) -> str:

    if not matches:

        situation = (
            "No schemes matched. "
            "Suggest pmjay.gov.in and scholarships.gov.in "
            "Ask user to try again."
        )

    elif detail_request is not None:

        idx = detail_request - 1

        if 0 <= idx < len(matches):

            s = matches[idx]

            situation = f"""
User wants details about:

Scheme: {s['name']}
Benefit: {s['benefit_amount']}
Description: {s['benefit_description']}
Eligibility: {s['eligibility_note']}
Apply: {s['how_to_apply']}
Documents: {s['documents_needed']}
Website: {s['url']}
"""

        else:

            situation = (
                f"User requested scheme {detail_request} "
                f"but only {len(matches)} schemes exist."
            )

    else:

        lines = []

        for i, s in enumerate(matches, 1):

            reasons = ", ".join(
                s.get("match_reasons", [])
            )

            lines.append(
                f"""
{i}. {s['name']}
Benefit: {s['benefit_amount']}
Reason: {reasons}
Apply: {s['how_to_apply']}
"""
            )

        situation = (
            f"{len(matches)} schemes found:\n\n"
            + "\n".join(lines)
            + "\n\nTell user to reply with a number for full details."
        )

    try:

        prompt = REPLY_PROMPT.format(
            message=user_message,
            situation=situation
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )

        return response.text.strip()

    except Exception as e:

        return f"⚠️ Error generating reply: {e}"

# =========================================================
# MAIN CLI
# =========================================================

def run_nlp_cli():

    import sys

    sys.path.insert(0, os.path.dirname(__file__))

    from scheme_db import init_db
    from matcher import match_schemes

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║ 🇮🇳 Scheme Finder — Natural Language Mode (Gemini)  ║")
    print("║ Type in English, Hindi, Kannada — anything works   ║")
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

        if user_input.lower() in (
            "exit",
            "quit",
            "bye"
        ):
            print("\n🙏 Thank you. Jai Hind!\n")
            break

        # =====================================================
        # DETAIL REQUEST
        # =====================================================

        if re.match(r"^\d+$", user_input) and last_matches:

            n = int(user_input)

            reply = generate_reply(
                last_matches,
                user_input,
                detail_request=n
            )

            print(f"\nBot: {reply}\n")

            continue

        # =====================================================
        # PROFILE EXTRACTION
        # =====================================================

        print("\n⏳ Understanding your message...")

        profile = extract_profile(user_input)

        if not profile:
            print(
                "Bot: Sorry, could not understand. "
                "Please try again.\n"
            )
            continue

        lang = profile.pop(
            "language",
            "english"
        )

        print(f"     Language : {lang}")

        print(
            f"     Profile  : "
            f"{json.dumps(profile, ensure_ascii=False)}"
        )

        # =====================================================
        # MATCH SCHEMES
        # =====================================================

        matches = match_schemes(profile)

        last_matches = matches

        # =====================================================
        # GENERATE RESPONSE
        # =====================================================

        print("\n⏳ Generating response...\n")

        reply = generate_reply(
            matches,
            user_input,
            language=lang
        )

        print(f"Bot: {reply}\n")

# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    run_nlp_cli()