"""
claude_handler.py — Gemini API version (free tier)
Replaces Claude API — same interface, drop-in swap.

Get free key at: https://aistudio.google.com
Add to .env:  GEMINI_API_KEY=your_key_here
"""

import os
import json
import re
import google.generativeai as genai

# Load .env manually (no dotenv dependency needed)
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
model = genai.GenerativeModel("gemini-1.5-flash")   # free tier model

EXTRACTION_PROMPT = """You are helping a Government Scheme Finder for India.
Extract eligibility info from the user message (may be English, Hindi, Kannada, or any Indian language).

Return ONLY a JSON object, no explanation, no markdown:
{{
  "state":      string or null,
  "occupation": string or null,   // farmer | daily_wage | unemployed | salaried | self_employed | other
  "income":     integer or null,  // annual Rs e.g. 80000
  "family":     string or null,   // single | married | widow | single_parent
  "special":    string or null,   // disabled | senior | pregnant | student | none
  "gender":     string or null,   // female | male | other
  "language":   string            // english | hindi | kannada | tamil | telugu | marathi | other
}}

Mappings:
- widow/vidhwa/vidhave/ವಿಧವೆ → family=widow
- farmer/kisan/raitha/ರೈತ → occupation=farmer
- disabled/viklang/ಅಂಗವಿಕಲ → special=disabled
- pregnant/garbhwati/ಗರ್ಭಿಣಿ → special=pregnant
- student/vidyarthi/ವಿದ್ಯಾರ್ಥಿ → special=student
- BPL/garib/poor → income=80000
- "1 lakh"/"ek lakh" → income=100000

User message: {message}"""


REPLY_PROMPT = """You are a warm helpful assistant for a Government Scheme Finder for India.
Users are rural/semi-urban Indians, many first-time phone users. Keep language simple.

IMPORTANT: Reply in the SAME language as the user's message.
Use 🙏 to start. Use ✅ 💰 for schemes. Keep sentences short.
End with: ⚠️ Yeh sirf jaankari ke liye hai. (translated to user's language)

User message: {message}

Situation: {situation}"""


def extract_profile(user_message: str) -> dict:
    try:
        prompt = EXTRACTION_PROMPT.format(message=user_message)
        response = model.generate_content(prompt)
        raw = response.text.strip()
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"⚠️  Gemini extraction error: {e}")
        return {}


def generate_reply(matches: list, user_message: str, language: str = "english",
                   detail_request: int = None) -> str:
    if not matches:
        situation = (
            "No schemes matched. Gently explain, suggest pmjay.gov.in "
            "and scholarships.gov.in, ask if they want to try again."
        )
    elif detail_request is not None:
        idx = detail_request - 1
        if 0 <= idx < len(matches):
            s = matches[idx]
            situation = (
                f"User wants details about: {s['name']}\n"
                f"Benefit: {s['benefit_amount']} — {s['benefit_description']}\n"
                f"Eligibility: {s['eligibility_note']}\n"
                f"How to apply: {s['how_to_apply']}\n"
                f"Documents: {s['documents_needed']}\n"
                f"URL: {s['url']}"
            )
        else:
            situation = f"User asked for scheme {detail_request} but only {len(matches)} exist."
    else:
        lines = []
        for i, s in enumerate(matches, 1):
            reasons = ", ".join(s.get("match_reasons", []))
            lines.append(
                f"{i}. {s['name']} — {s['benefit_amount']}\n"
                f"   Qualifies because: {reasons}\n"
                f"   Apply: {s['how_to_apply'][:80]}"
            )
        situation = (
            f"{len(matches)} schemes found:\n\n" + "\n\n".join(lines) +
            "\n\nTell user to reply with a number for full details."
        )
    try:
        prompt = REPLY_PROMPT.format(message=user_message, situation=situation)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"⚠️ Error: {e}"


def run_nlp_cli():
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from scheme_db import init_db
    from matcher import match_schemes

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  🇮🇳  Scheme Finder — Natural Language Mode (Gemini)  ║")
    print("║  Type in English, Hindi, Kannada — anything works    ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()
    init_db()

    last_matches = []
    while True:
        print("─" * 54)
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "bye"):
            print("\n🙏 Thank you. Jai Hind!\n")
            break

        # Scheme detail request (user types just a number)
        if re.match(r"^\s*\d+\s*$", user_input) and last_matches:
            n = int(user_input.strip())
            reply = generate_reply(last_matches, user_input, detail_request=n)
            print(f"\nBot: {reply}\n")
            continue

        print("\n⏳ Understanding your message…")
        profile = extract_profile(user_input)
        if not profile:
            print("Bot: Sorry, could not understand. Please try again.\n")
            continue

        lang = profile.pop("language", "english")
        print(f"     Language : {lang}")
        print(f"     Profile  : {json.dumps(profile, ensure_ascii=False)}")

        matches = match_schemes(profile)
        last_matches = matches

        print("\n⏳ Generating response…\n")
        reply = generate_reply(matches, user_input, language=lang)
        print(f"Bot: {reply}\n")


if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY not set.")
        print("   Add to .env file:  GEMINI_API_KEY=your_key_here")
        print("   Get free key at:   https://aistudio.google.com")
        exit(1)
    run_nlp_cli()
