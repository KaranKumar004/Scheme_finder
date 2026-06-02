"""
gemini_handler.py — Gemini API version (India Benefits Finder)
Works with latest google-genai SDK
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
     print("⚠️ GEMINI_API_KEY not found. NLP features will not work.")
    

# =========================================================
# GEMINI CLIENT
# =========================================================

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-2.5-flash"

# =========================================================
# EXTRACTION PROMPT
# =========================================================

EXTRACTION_PROMPT = """
You are helping a welfare benefits portal called India Benefits Finder.

Extract eligibility info from the user message.
The message may be in English, Hindi, Kannada, Tamil, Telugu, Marathi, or mixed languages.

Return ONLY valid JSON.
No markdown.
No explanation.

{{
  "state": null,
  "district": null,
  "occupation": null,
  "income": null,
  "family": null,
  "special": null,
  "gender": null,
  "age": null,
  "education": null,
  "caste_category": null,
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

Allowed caste_category:
general
obc
sc
st

Language values:
english
hindi
kannada
tamil
telugu
marathi
other

Allowed education (extract closest fit):
10th
12th
graduate
postgraduate
student

Mappings & Vocab Guidance:
- state: extract state name (e.g. Karnataka, Maharashtra, Tamil Nadu, Andhra Pradesh, Telangana, Uttar Pradesh)
- district: extract local district if mentioned (e.g. Mysuru, Pune, Bangalore, Madurai, Thane, Hyderabad)
- caste_category: general/samanya -> general, OBC/pichda varg/backward -> obc, SC/scheduled caste/harijan -> sc, ST/scheduled tribe/adivasi -> st
- age: extract integers (e.g. "I am 22 years old" -> 22)
- income: BPL / poor / garib -> income=80000, 1 lakh -> income=100000, 2 lakhs -> income=200000
- widow / vidhwa / ವಿಧವೆ / விதவை (vithavai) / విధవ (vidhava) -> widow
- farmer / kisan / ರೈತ / விவசாயி (vivasayi) / రైతు (raitu) / शेतकरी (shetkari) -> farmer
- disabled / viklang / ಅಂಗವಿಕल / மாற்றுத்திறனாளி (matrutiranali) / వికలాంగుడు (vikalangudu) / दिव्यांग (divyang) -> disabled
- pregnant / garbhwati / గర్భిణీ (garbhini) / கர்ப்பிணி (karppini) / गर्भवती (garbhawati) -> pregnant
- student / vidyarthi / ವಿದ್ಯಾರ್ಥಿ / மாணவர் (manavar) / విద్యార్థి (vidyarthi) / विद्यार्थी (vidyarthi) -> student

User message:
{message}
"""

# =========================================================
# REPLY PROMPT
# =========================================================

REPLY_PROMPT = """
You are a warm helpful assistant for India Benefits Finder.

Users may be rural or semi-urban Indians.
Keep language SIMPLE.

IMPORTANT:
Reply in the SAME language as the user (English, Hindi, Kannada, Tamil, Telugu, or Marathi).

Group the matched benefits in your response by type: Schemes, Loans, and Scholarships, using appropriate headings and emojis:
🏛️ Schemes
💰 Loans
🎓 Scholarships

Use emojis: 🙏 ✅ 💰 🎓 🏛️

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
        return {}

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
            "No benefits, schemes, loans, or scholarships matched. "
            "Suggest checking pmjay.gov.in, scholarships.gov.in, and PM Mudra (mudra.org.in). "
            "Ask the user to try again with more details."
        )

    elif detail_request is not None:
        idx = detail_request - 1

        if 0 <= idx < len(matches):
            s = matches[idx]
            benefit_type = s.get("type", "scheme").upper()

            situation = f"""
User wants details about this specific benefit:

Type: {benefit_type}
Name: {s['name']}
Ministry: {s.get('ministry', 'Welfare Dept')}
Benefit: {s['benefit_amount']}
Description: {s.get('benefit_description', 'No description')}
Eligibility: {s.get('eligibility_note', 'Matching profile filters')}
Apply: {s.get('how_to_apply', 'Visit block office')}
Documents: {s.get('documents_needed', 'Aadhaar, income certificate')}
Website: {s.get('url', 'N/A')}
"""
        else:
            situation = (
                f"User requested benefit {detail_request} "
                f"but only {len(matches)} benefits exist."
            )

    else:
        # Group matches by type for prompt feeding
        schemes = [m for m in matches if m.get("type") == "scheme"]
        loans = [m for m in matches if m.get("type") == "loan"]
        scholarships = [m for m in matches if m.get("type") == "scholarship"]

        sections = []
        running_idx = 1
        
        def format_section(items, title, icon):
            nonlocal running_idx
            if not items:
                return
            sec_lines = [f"{icon} {title}:"]
            for s in items:
                reasons = ", ".join(s.get("match_reasons", []))
                sec_lines.append(
                    f"{running_idx}. {s['name']}\n"
                    f"   Benefit: {s['benefit_amount']}\n"
                    f"   Reason: {reasons}\n"
                    f"   Apply: {s['how_to_apply'][:80]}...\n"
                )
                running_idx += 1
            sections.append("\n".join(sec_lines))

        format_section(schemes, "Government Schemes", "🏛️")
        format_section(loans, "Concessional Loans", "💰")
        format_section(scholarships, "Scholarships & Educational Aid", "🎓")

        situation = (
            f"{len(matches)} benefits found:\n\n"
            + "\n\n".join(sections)
            + "\n\nTell the user they can reply with a number (e.g. 1, 2...) for full details."
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
    print("║ 🇮🇳 India Benefits Finder — AI Assistant Mode         ║")
    print("║ English, Hindi, Kannada, Tamil, Telugu, Marathi     ║")
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
        print("\n⏳ Parsing message...")
        profile = extract_profile(user_input)

        if not profile:
            print("Bot: Sorry, could not parse profile. Try again.\n")
            continue

        lang = profile.pop("language", "english")

        print(f"     Language : {lang}")
        print(f"     Profile  : {json.dumps(profile, ensure_ascii=False)}")

        # Clean income and age
        if "income" in profile and profile["income"] is not None:
            try:
                profile["income"] = int(profile["income"])
            except (ValueError, TypeError):
                profile["income"] = None
        if "age" in profile and profile["age"] is not None:
            try:
                profile["age"] = int(profile["age"])
            except (ValueError, TypeError):
                profile["age"] = None

        # =====================================================
        # MATCH SCHEMES
        # =====================================================
        matches = match_schemes(profile)
        last_matches = matches

        # =====================================================
        # GENERATE RESPONSE
        # =====================================================
        print("\n⏳ Generating reply...\n")
        reply = generate_reply(
            matches,
            user_input,
            language=lang
        )
        print(f"Bot: {reply}\n")


if __name__ == "__main__":
    run_nlp_cli()