"""
cli.py — Interactive terminal interface to test the Scheme Finder matching engine.
No WhatsApp needed. Run: python cli.py
"""

import os
import sys

# Ensure we can import sibling modules
sys.path.insert(0, os.path.dirname(__file__))

from scheme_db import init_db
from matcher import match_schemes, format_results


STATES = [
    "Karnataka", "Maharashtra", "Tamil Nadu", "Andhra Pradesh",
    "Telangana", "Kerala", "Gujarat", "Rajasthan", "Uttar Pradesh",
    "Madhya Pradesh", "Bihar", "West Bengal", "Other"
]

OCCUPATIONS = {
    "1": ("farmer",        "Farmer / agricultural worker"),
    "2": ("daily_wage",    "Daily wage / labour"),
    "3": ("unemployed",    "Currently unemployed"),
    "4": ("salaried",      "Salaried employee"),
    "5": ("self_employed", "Self-employed / small business"),
    "6": ("other",         "Other"),
}

INCOME_RANGES = {
    "1": (0,       100000,  "Under Rs 1 lakh/year"),
    "2": (100001,  300000,  "Rs 1–3 lakh/year"),
    "3": (300001,  600000,  "Rs 3–6 lakh/year"),
    "4": (600001,  None,    "Above Rs 6 lakh/year"),
}

FAMILY_SITUATIONS = {
    "1": ("single",        "Single"),
    "2": ("married",       "Married"),
    "3": ("widow",         "Widow / Widower"),
    "4": ("single_parent", "Single parent"),
}

SPECIAL_SITUATIONS = {
    "1": ("disabled",  "Person with disability"),
    "2": ("senior",    "Senior citizen (60+)"),
    "3": ("pregnant",  "Pregnant"),
    "4": ("student",   "Student"),
    "5": ("none",      "None of these"),
}

GENDERS = {
    "1": ("female", "Female"),
    "2": ("male",   "Male"),
    "3": ("other",  "Prefer not to say"),
}


def pick(prompt: str, options: dict) -> str:
    """Print numbered options and return the chosen value."""
    print(f"\n{prompt}")
    for k, v in options.items():
        label = v[1] if isinstance(v, tuple) else v
        print(f"  {k}. {label}")
    while True:
        choice = input("  Your choice: ").strip()
        if choice in options:
            return options[choice][0] if isinstance(options[choice], tuple) else options[choice]
        print(f"  ⚠️  Please enter a number between 1 and {max(options.keys())}")


def pick_state() -> str:
    print("\n📍 Question 1 of 5 — Which state are you from?")
    for i, s in enumerate(STATES, 1):
        print(f"  {i:2}. {s}")
    while True:
        c = input("  Your choice (number): ").strip()
        try:
            idx = int(c) - 1
            if 0 <= idx < len(STATES):
                return STATES[idx]
        except ValueError:
            pass
        print("  ⚠️  Please enter a valid number.")


def pick_income() -> int:
    """Return the midpoint of the chosen income band as a representative integer."""
    print("\n💰 Question 3 of 5 — Approximate annual household income?")
    for k, (lo, hi, label) in INCOME_RANGES.items():
        print(f"  {k}. {label}")
    while True:
        c = input("  Your choice: ").strip()
        if c in INCOME_RANGES:
            lo, hi, _ = INCOME_RANGES[c]
            # Use midpoint; if no upper bound use lo + buffer
            return (lo + hi) // 2 if hi else lo + 100000
        print(f"  ⚠️  Please enter 1–{len(INCOME_RANGES)}")


def ask_details(scheme: dict) -> None:
    """Print full details for a single scheme."""
    s = scheme
    print(f"\n{'='*60}")
    print(f"📋 {s['name']}")
    print(f"{'='*60}")
    print(f"  Ministry    : {s['ministry']}")
    print(f"  Level       : {s['level'].upper()}")
    print(f"  Benefit     : {s['benefit_amount']}")
    print(f"  Description : {s['benefit_description']}")
    print(f"  Eligibility : {s['eligibility_note']}")
    print(f"  How to apply: {s['how_to_apply']}")
    print(f"  Documents   : {s['documents_needed']}")
    print(f"  Official URL: {s['url']}")
    print()


def run():
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║   🇮🇳  Government Scheme Finder — India               ║")
    print("║   Free tool to find welfare schemes you qualify for   ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    # Initialise DB silently if needed
    if not os.path.exists(os.environ.get("DATABASE_PATH", "schemes.db")):
        print("⚙️  Setting up database for first run…")
        init_db()
    else:
        init_db()   # safe — skips if already populated

    while True:
        print("\n" + "─"*54)
        print("Answer 5 quick questions to find schemes you qualify for.")
        print("─"*54)

        state      = pick_state()
        occupation = pick(
            "🧑‍🌾 Question 2 of 5 — What is your occupation?",
            OCCUPATIONS
        )
        income     = pick_income()
        family     = pick(
            "👨‍👩‍👧 Question 4 of 5 — What is your family situation?",
            FAMILY_SITUATIONS
        )
        special    = pick(
            "🌟 Question 5 of 5 — Any special situation?",
            SPECIAL_SITUATIONS
        )
        gender     = pick(
            "🚻 One more — Gender (helps match women-only schemes)?",
            GENDERS
        )

        profile = {
            "state":      state,
            "occupation": occupation,
            "income":     income,
            "family":     family,
            "special":    special,
            "gender":     gender,
        }

        print("\n⏳ Matching schemes…\n")
        matches = match_schemes(profile)
        print(format_results(matches, verbose=False))

        if matches:
            print()
            while True:
                choice = input(
                    "Enter a scheme number for full details, or press Enter to search again: "
                ).strip()
                if choice == "":
                    break
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(matches):
                        ask_details(matches[idx])
                    else:
                        print(f"  ⚠️  Please enter a number between 1 and {len(matches)}")
                except ValueError:
                    print("  ⚠️  Please enter a valid number or press Enter.")

        again = input("\n🔄 Check for another person? (y/n): ").strip().lower()
        if again != "y":
            print("\n🙏 Thank you for using the Scheme Finder.")
            print("   Every query is a person getting information they were entitled to.\n")
            break


if __name__ == "__main__":
    run()
