"""
matcher.py — Eligibility matching logic for India Benefits Finder

User profile keys:
    state           : str  e.g. "Karnataka"
    district        : str  e.g. "Mysuru" (Phase 2)
    occupation      : str  farmer | daily_wage | unemployed | salaried | self_employed | other
    income          : int  annual household income in Rs
    family          : str  single | married | widow | single_parent
    special         : str  disabled | senior | pregnant | student | none
    gender          : str  male | female | other
    age             : int  user's age (Phase 2)
    education       : str  e.g. "12th", "graduate", "student" (Phase 2)
    caste_category  : str  general | obc | sc | st (Phase 2)
"""

import sqlite3
from scheme_db import get_connection


def match_schemes(profile: dict) -> list[dict]:
    """
    Returns a list of matching benefits (schemes, loans, scholarships) for the given user profile.
    Each dict has all columns plus a 'match_reasons' list and a 'type' tag.
    """
    state          = (profile.get("state") or "").strip()
    district       = (profile.get("district") or "").strip().lower()
    occupation     = (profile.get("occupation") or "").strip().lower()
    income         = profile.get("income")          # int Rs/year or None
    family         = (profile.get("family") or "").strip().lower()
    special        = (profile.get("special") or "").strip().lower()
    gender         = (profile.get("gender") or "").strip().lower()
    
    # Phase 2 keys
    age            = profile.get("age")             # int or None
    education      = (profile.get("education") or "").strip().lower()
    caste_category = (profile.get("caste_category") or "").strip().lower()

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # ── Fetch from all three tables ──────────────────────────────────────────
    all_benefits = []
    
    c.execute("SELECT * FROM schemes")
    for row in c.fetchall():
        item = dict(row)
        item["type"] = "scheme"
        all_benefits.append(item)
        
    c.execute("SELECT * FROM loans")
    for row in c.fetchall():
        item = dict(row)
        item["type"] = "loan"
        all_benefits.append(item)
        
    c.execute("SELECT * FROM scholarships")
    for row in c.fetchall():
        item = dict(row)
        item["type"] = "scholarship"
        all_benefits.append(item)
        
    conn.close()

    results = []
    for s in all_benefits:
        reasons = []

        # ── State filter ────────────────────────────────────────────────────────
        if s["states"]:
            allowed = [st.strip().lower() for st in s["states"].split(",")]
            if state and state.lower() not in allowed:
                continue   # state-specific and user is from another state

        # ── District filter (Phase 2) ────────────────────────────────────────────
        if s.get("districts"):
            allowed_districts = [d.strip().lower() for d in s["districts"].split(",")]
            if district and district not in allowed_districts:
                continue

        # ── Income filter ───────────────────────────────────────────────────────
        if s["min_income"] is not None and income is not None:
            if income < s["min_income"]:
                continue
        if s["max_income"] is not None and income is not None:
            if income > s["max_income"]:
                continue

        # ── Age filter (Phase 2) ─────────────────────────────────────────────────
        if s.get("min_age") is not None and age is not None:
            if age < s["min_age"]:
                continue
        if s.get("max_age") is not None and age is not None:
            if age > s["max_age"]:
                continue

        # ── Caste Category filter (Phase 2) ──────────────────────────────────────
        if s.get("caste_category"):
            allowed_castes = [c.strip().lower() for c in s["caste_category"].split(",")]
            if caste_category and caste_category not in allowed_castes:
                continue

        # ── Education filter (Phase 2) ───────────────────────────────────────────
        if s.get("education"):
            allowed_edu = [e.strip().lower() for e in s["education"].split(",")]
            if education and education not in allowed_edu:
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
            reasons.append("widowed family status")
        if family == "single_parent" and s["for_single_parent"]:
            reasons.append("single parent status")
        if occupation == "farmer" and (s["for_farmer"] or s["for_any_occupation"]):
            reasons.append("farming livelihood")
        if special == "disabled" and s["for_disabled"]:
            reasons.append("special needs / disability cover")
        if special == "senior" and s["for_senior"]:
            reasons.append("senior citizen category (60+)")
        if special == "pregnant" and s["for_pregnant"]:
            reasons.append("maternity / infant welfare")
        if special == "student" and s["for_student"]:
            reasons.append("student status")
        if occupation in ("self_employed", "daily_wage", "unemployed") and s["for_self_employed"]:
            reasons.append("self-employment eligibility")
        if income is not None and s["max_income"] and income <= s["max_income"]:
            reasons.append(f"household income under Rs {s['max_income']:,}")
        
        # Phase 2 Reasons
        if age is not None and (s.get("min_age") or s.get("max_age")):
            reasons.append(f"age within eligible range ({s.get('min_age') or 0}-{s.get('max_age') or 'unlimited'})")
        if caste_category and s.get("caste_category"):
            reasons.append(f"caste category ({caste_category.upper()})")
        if education and s.get("education"):
            reasons.append(f"education level ({education.capitalize()})")
        if district and s.get("districts"):
            reasons.append(f"district location ({district.capitalize()})")

        if not reasons:
            reasons.append("profile matching criteria")

        s["match_reasons"] = reasons
        results.append(s)

    # ── Sort matches by type so they are naturally grouped ───────────────────────
    type_priority = {"scheme": 0, "loan": 1, "scholarship": 2}
    results.sort(key=lambda x: type_priority.get(x.get("type", "scheme"), 0))

    return results


def format_results(matches: list[dict], verbose: bool = False) -> str:
    """
    Format matched benefits into human-readable output grouped by type.
    """
    if not matches:
        return (
            "❌ No matching benefits found based on your profile.\n"
            "This may be because:\n"
            "  • No state-specific programs exist yet for your state\n"
            "  • Your income is above eligibility thresholds\n\n"
            "Please check the National Scholarship Portal (scholarships.gov.in),\n"
            "Ayushman Bharat (pmjay.gov.in), and your state welfare portal directly."
        )

    # Group by type
    schemes = [m for m in matches if m.get("type") == "scheme"]
    loans = [m for m in matches if m.get("type") == "loan"]
    scholarships = [m for m in matches if m.get("type") == "scholarship"]

    lines = [
        f"🙏 Namaste! Based on what you told me, you may qualify for *{len(matches)} benefit(s)*:\n"
    ]

    running_idx = 1

    def add_section(items, title, icon):
        nonlocal running_idx
        if not items:
            return
        lines.append(f"{icon} *{title}* ({len(items)} matched):")
        for s in items:
            reasons_str = ", ".join(s["match_reasons"])
            lines.append(f"  {running_idx}. {s['name']}")
            lines.append(f"     💰 Benefit : {s['benefit_amount']}")
            lines.append(f"     ✅ You qualify because : {reasons_str}")
            if verbose:
                lines.append(f"     📋 About   : {s['benefit_description']}")
                lines.append(f"     🏛️  Apply at : {s['how_to_apply']}")
                lines.append(f"     📄 Documents: {s['documents_needed']}")
                lines.append(f"     🔗 URL      : {s['url']}")
            else:
                lines.append(f"     🏛️  Apply at : {s['how_to_apply'][:80]}...")
            running_idx += 1
        lines.append("")

    add_section(schemes, "Government Welfare Schemes", "🏛️")
    add_section(loans, "Concessional Financial Loans", "💰")
    add_section(scholarships, "Scholarships & Educational Aid", "🎓")

    lines.append("─────────────────────")
    lines.append("⚠️  This is for information only. Always verify at official government websites.")

    if not verbose:
        lines.append("\nReply with a number (1, 2, …) to get full details about any benefit.")

    return "\n".join(lines).strip()


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
            "income": 60000, "family": "married", "special": "disabled", "gender": "male",
            "age": 25, "education": "10th"
        },
        {
            "label": "Pregnant woman, any state, income 1.2L",
            "state": "Karnataka", "occupation": "unemployed",
            "income": 120000, "family": "married", "special": "pregnant", "gender": "female"
        },
        {
            "label": "Student, SC/ST, Karnataka, income 2L",
            "state": "Karnataka", "occupation": "unemployed",
            "income": 200000, "family": "single", "special": "student", "gender": "male",
            "caste_category": "sc"
        },
    ]

    for p in test_profiles:
        print(f"\n{'='*60}")
        print(f"TEST: {p['label']}")
        print(f"{'='*60}")
        profile = {k: v for k, v in p.items() if k != "label"}
        matches = match_schemes(profile)
        print(format_results(matches, verbose=True))
