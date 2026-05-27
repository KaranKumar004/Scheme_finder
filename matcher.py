"""
matcher.py — Eligibility matching logic for Government Scheme Finder

User profile keys:
    state       : str  e.g. "Karnataka"
    occupation  : str  farmer | daily_wage | unemployed | salaried | self_employed | other
    income      : int  annual household income in Rs
    family      : str  single | married | widow | single_parent
    special     : str  disabled | senior | pregnant | student | none
    gender      : str  male | female | other  (optional — defaults to None = all)
"""

import sqlite3
from scheme_db import get_connection


def match_schemes(profile: dict) -> list[dict]:
    """
    Returns a list of matching scheme dicts for the given user profile.
    Each dict has all scheme columns plus a 'match_reasons' list.
    """
    state      = (profile.get("state") or "").strip()
    occupation = (profile.get("occupation") or "").strip().lower()
    income     = profile.get("income")          # int Rs/year or None
    family     = (profile.get("family") or "").strip().lower()
    special    = (profile.get("special") or "").strip().lower()
    gender     = (profile.get("gender") or "").strip().lower()

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM schemes")
    all_schemes = c.fetchall()
    conn.close()

    results = []
    for s in all_schemes:
        reasons = []

        # ── State filter ────────────────────────────────────────────────────────
        if s["states"]:
            allowed = [st.strip() for st in s["states"].split(",")]
            if state and state not in allowed:
                continue   # scheme is state-specific and user is from another state

        # ── Income filter ───────────────────────────────────────────────────────
        if s["min_income"] is not None and income is not None:
            if income < s["min_income"]:
                continue
        if s["max_income"] is not None and income is not None:
            if income > s["max_income"]:
                continue

        # ── Occupation match ────────────────────────────────────────────────────
        occ_match = False
        if s["for_any_occupation"]:
            occ_match = True
        elif occupation == "farmer"       and s["for_farmer"]:        occ_match = True
        elif occupation == "daily_wage"   and s["for_daily_wage"]:    occ_match = True
        elif occupation == "unemployed"   and s["for_unemployed"]:    occ_match = True
        elif occupation == "salaried"     and s["for_salaried"]:      occ_match = True
        elif occupation == "self_employed"and s["for_self_employed"]: occ_match = True
        elif occupation == "other"        and s["for_any_occupation"]:occ_match = True

        if not occ_match:
            # Allow schemes that have at least one occupation gate to be skipped;
            # but don't skip if ALL occ flags are 0 (means occupation is irrelevant)
            occ_flags = [
                s["for_farmer"], s["for_daily_wage"], s["for_unemployed"],
                s["for_salaried"], s["for_self_employed"], s["for_any_occupation"]
            ]
            if any(occ_flags):
                continue

        # ── Family match ─────────────────────────────────────────────────────────
        fam_match = False
        if s["for_any_family"]:
            fam_match = True
        elif family == "widow"       and s["for_widow"]:        fam_match = True
        elif family == "single_parent" and s["for_single_parent"]: fam_match = True
        elif family == "married"     and s["for_married"]:      fam_match = True
        elif family == "single"      and s["for_single"]:       fam_match = True

        if not fam_match:
            fam_flags = [
                s["for_widow"], s["for_single_parent"], s["for_married"],
                s["for_single"], s["for_any_family"]
            ]
            if any(fam_flags):
                continue

        # ── Special situation match ──────────────────────────────────────────────
        sp_match = False
        if s["for_any_special"]:
            sp_match = True
        elif special == "disabled"  and s["for_disabled"]:   sp_match = True
        elif special == "senior"    and s["for_senior"]:     sp_match = True
        elif special == "pregnant"  and s["for_pregnant"]:   sp_match = True
        elif special == "student"   and s["for_student"]:    sp_match = True
        elif special == "none"      and s["for_any_special"]:sp_match = True

        if not sp_match:
            sp_flags = [
                s["for_disabled"], s["for_senior"], s["for_pregnant"],
                s["for_student"], s["for_any_special"]
            ]
            if any(sp_flags):
                continue

        # ── Gender filter ────────────────────────────────────────────────────────
        if s["for_women"] and gender and gender not in ("female", "woman", "f"):
            continue

        # ── Build match reasons ──────────────────────────────────────────────────
        if family == "widow" and s["for_widow"]:
            reasons.append("widow")
        if family == "single_parent" and s["for_single_parent"]:
            reasons.append("single parent")
        if occupation == "farmer" and (s["for_farmer"] or s["for_any_occupation"]):
            reasons.append("farmer")
        if special == "disabled" and s["for_disabled"]:
            reasons.append("person with disability")
        if special == "senior" and s["for_senior"]:
            reasons.append("senior citizen (60+)")
        if special == "pregnant" and s["for_pregnant"]:
            reasons.append("pregnant")
        if special == "student" and s["for_student"]:
            reasons.append("student")
        if occupation in ("self_employed", "daily_wage", "unemployed") and s["for_self_employed"]:
            reasons.append("self-employed / small business owner")
        if income is not None and s["max_income"] and income <= s["max_income"]:
            reasons.append(f"household income under Rs {s['max_income']:,}")
        if not reasons:
            reasons.append("your profile matches this scheme")

        scheme_dict = dict(s)
        scheme_dict["match_reasons"] = reasons
        results.append(scheme_dict)

    return results


def format_results(matches: list[dict], verbose: bool = False) -> str:
    """
    Format matched schemes into human-readable output.
    verbose=True gives full details, False gives a short summary list.
    """
    if not matches:
        return (
            "❌ No matching schemes found based on your profile.\n"
            "This may be because:\n"
            "  • No state-specific schemes exist yet for your state\n"
            "  • Your income is above eligibility thresholds\n\n"
            "Please check the National Scholarship Portal (scholarships.gov.in),\n"
            "Ayushman Bharat (pmjay.gov.in), and your state welfare portal directly."
        )

    lines = [
        f"🙏 Namaste! Based on what you told me, you may qualify for {len(matches)} scheme(s):\n"
    ]

    for i, s in enumerate(matches, 1):
        reasons_str = ", ".join(s["match_reasons"])
        lines.append(f"{'─'*50}")
        lines.append(f"{i}. {s['name']}")
        lines.append(f"   💰 Benefit : {s['benefit_amount']}")
        lines.append(f"   ✅ You qualify because : {reasons_str}")
        if verbose:
            lines.append(f"   📋 About   : {s['benefit_description']}")
            lines.append(f"   🏛️  Apply at : {s['how_to_apply']}")
            lines.append(f"   📄 Documents: {s['documents_needed']}")
            lines.append(f"   🔗 URL      : {s['url']}")
        else:
            lines.append(f"   🏛️  Apply at : {s['how_to_apply'][:80]}...")

    lines.append(f"\n{'─'*50}")
    lines.append("⚠️  This is for information only. Always verify at official government websites.")

    if not verbose:
        lines.append("\nReply with a number (1, 2, …) to get full details about any scheme.")

    return "\n".join(lines)


# ─── Quick terminal test ───────────────────────────────────────────────────────
if __name__ == "__main__":
    from scheme_db import init_db
    init_db()

    test_profiles = [
        {
            "label": "Widow farmer in Karnataka, income 80K",
            "state": "Karnataka", "occupation": "farmer",
            "income": 80000, "family": "widow", "special": "none", "gender": "female"
        },
        {
            "label": "Disabled daily wage worker in Karnataka, income 60K",
            "state": "Karnataka", "occupation": "daily_wage",
            "income": 60000, "family": "married", "special": "disabled", "gender": "male"
        },
        {
            "label": "Pregnant woman, any state, income 1.2L",
            "state": "Karnataka", "occupation": "unemployed",
            "income": 120000, "family": "married", "special": "pregnant", "gender": "female"
        },
        {
            "label": "Student, SC/ST, Karnataka, income 2L",
            "state": "Karnataka", "occupation": "unemployed",
            "income": 200000, "family": "single", "special": "student", "gender": "male"
        },
        {
            "label": "Small business woman, any income",
            "state": "Karnataka", "occupation": "self_employed",
            "income": 400000, "family": "single", "special": "none", "gender": "female"
        },
    ]

    for p in test_profiles:
        print(f"\n{'='*60}")
        print(f"TEST: {p['label']}")
        print(f"{'='*60}")
        profile = {k: v for k, v in p.items() if k != "label"}
        matches = match_schemes(profile)
        print(format_results(matches, verbose=True))
