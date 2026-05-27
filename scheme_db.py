"""
scheme_db.py — SQLite database setup + queries for Government Scheme Finder
"""

import sqlite3
import os
import sys

# Force UTF-8 stdout/stderr on Windows to prevent UnicodeEncodeError
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

DATABASE_PATH = os.environ.get("DATABASE_PATH", "schemes.db")


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the database tables and populate with 15 Karnataka schemes."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS schemes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ministry TEXT,
            level TEXT,              -- central / state
            benefit_amount TEXT,
            benefit_description TEXT,
            how_to_apply TEXT,
            url TEXT,
            documents_needed TEXT,

            -- Eligibility filters (NULL = applies to all)
            states TEXT,             -- comma-separated or NULL for all-India
            min_income INTEGER,      -- NULL = no min
            max_income INTEGER,      -- NULL = no max (in Rs/year)

            -- Occupation flags
            for_farmer INTEGER DEFAULT 0,
            for_daily_wage INTEGER DEFAULT 0,
            for_unemployed INTEGER DEFAULT 0,
            for_salaried INTEGER DEFAULT 0,
            for_self_employed INTEGER DEFAULT 0,
            for_any_occupation INTEGER DEFAULT 0,

            -- Family situation flags
            for_widow INTEGER DEFAULT 0,
            for_single_parent INTEGER DEFAULT 0,
            for_married INTEGER DEFAULT 0,
            for_single INTEGER DEFAULT 0,
            for_any_family INTEGER DEFAULT 0,

            -- Special situation flags
            for_disabled INTEGER DEFAULT 0,
            for_senior INTEGER DEFAULT 0,
            for_pregnant INTEGER DEFAULT 0,
            for_student INTEGER DEFAULT 0,
            for_any_special INTEGER DEFAULT 0,

            -- Gender
            for_women INTEGER DEFAULT 0,  -- 0 = all genders, 1 = women only

            -- Notes shown to user
            eligibility_note TEXT
        )
    """)

    conn.commit()
    _populate_schemes(conn)
    conn.close()
    print(f"✅ Database initialised at {DATABASE_PATH}")


def _populate_schemes(conn):
    """Insert the 15 Karnataka/central schemes. Safe to re-run (skips if exists)."""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM schemes")
    if c.fetchone()[0] > 0:
        print("ℹ️  Schemes already populated — skipping.")
        return

    schemes = [
        # 1. Indira Gandhi National Widow Pension
        {
            "name": "Indira Gandhi National Widow Pension Scheme (IGNWPS)",
            "ministry": "Ministry of Rural Development",
            "level": "central",
            "benefit_amount": "Rs 300/month",
            "benefit_description": "Monthly pension for widows below poverty line",
            "how_to_apply": "Apply at Gram Panchayat / Block Development Office / Nadakacheri (Karnataka)",
            "url": "https://nsap.nic.in",
            "documents_needed": "Aadhaar card, husband's death certificate, BPL card / income certificate, bank passbook",
            "states": None,
            "max_income": 150000,
            "for_widow": 1,
            "for_any_occupation": 1,
            "for_any_special": 1,
            "eligibility_note": "Widow aged 40–79, below poverty line",
        },
        # 2. Karnataka Sandhya Suraksha Yojana
        {
            "name": "Karnataka Sandhya Suraksha Yojana (Widow Pension)",
            "ministry": "Karnataka Dept of Social Welfare",
            "level": "state",
            "benefit_amount": "Rs 1,000/month",
            "benefit_description": "State-level monthly pension for widows in Karnataka",
            "how_to_apply": "Apply at Nadakacheri or Gram Panchayat. Online at sevasindhu.karnataka.gov.in",
            "url": "https://sevasindhu.karnataka.gov.in",
            "documents_needed": "Aadhaar, husband's death certificate, income certificate, Karnataka domicile proof, bank passbook",
            "states": "Karnataka",
            "max_income": 150000,
            "for_widow": 1,
            "for_any_occupation": 1,
            "for_any_special": 1,
            "eligibility_note": "Widow residing in Karnataka, income below Rs 1.5 lakh/year",
        },
        # 3. PM-KISAN
        {
            "name": "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
            "ministry": "Ministry of Agriculture & Farmers Welfare",
            "level": "central",
            "benefit_amount": "Rs 6,000/year",
            "benefit_description": "Annual income support in 3 instalments of Rs 2,000 for small & marginal farmers",
            "how_to_apply": "Register at pmkisan.gov.in or nearest Common Service Centre (CSC) or Gram Panchayat",
            "url": "https://pmkisan.gov.in",
            "documents_needed": "Aadhaar, land records / Khasra-Khatauni, bank passbook",
            "states": None,
            "max_income": None,
            "for_farmer": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "eligibility_note": "Small & marginal farmers who own cultivable land",
        },
        # 4. Ayushman Bharat PMJAY
        {
            "name": "Ayushman Bharat – PM Jan Arogya Yojana (PMJAY)",
            "ministry": "Ministry of Health & Family Welfare",
            "level": "central",
            "benefit_amount": "Rs 5 lakh/year health cover",
            "benefit_description": "Free hospitalisation cover of Rs 5 lakh per family per year at empanelled hospitals",
            "how_to_apply": "Check eligibility at pmjay.gov.in or visit nearest Ayushman Mitra / CSC centre",
            "url": "https://pmjay.gov.in",
            "documents_needed": "Aadhaar, ration card, SECC 2011 data (auto-eligible if in list)",
            "states": None,
            "max_income": 300000,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "eligibility_note": "BPL and low-income families as per SECC 2011 data",
        },
        # 5. PM Awas Yojana – Gramin
        {
            "name": "Pradhan Mantri Awas Yojana – Gramin (PMAY-G)",
            "ministry": "Ministry of Rural Development",
            "level": "central",
            "benefit_amount": "Rs 1.2–1.3 lakh subsidy",
            "benefit_description": "Financial assistance to construct a pucca house for houseless / kutcha house families",
            "how_to_apply": "Apply through Gram Panchayat. Online at pmayg.nic.in",
            "url": "https://pmayg.nic.in",
            "documents_needed": "Aadhaar, BPL/SECC data, bank account",
            "states": None,
            "max_income": 300000,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "eligibility_note": "Homeless or kutcha/dilapidated house owner, rural area, as per SECC 2011 list",
        },
        # 6. National Scholarship Portal – Post-Matric
        {
            "name": "National Scholarship Portal – Post-Matric Scholarship",
            "ministry": "Ministry of Education / Social Justice",
            "level": "central",
            "benefit_amount": "Rs 3,000–10,000/year (varies by course)",
            "benefit_description": "Scholarships for students from minority, SC/ST, OBC, and economically weaker sections",
            "how_to_apply": "Apply online at scholarships.gov.in before deadline (usually Aug–Oct)",
            "url": "https://scholarships.gov.in",
            "documents_needed": "Aadhaar, income certificate, caste certificate (if applicable), mark sheet, bank passbook",
            "states": None,
            "max_income": 250000,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "for_student": 1,
            "eligibility_note": "Students in Class 11+ or college, income below Rs 2.5 lakh/year",
        },
        # 7. NSAP Disability Pension
        {
            "name": "National Social Assistance Programme – Disability Pension (NSAP)",
            "ministry": "Ministry of Rural Development",
            "level": "central",
            "benefit_amount": "Rs 300–500/month",
            "benefit_description": "Monthly pension for persons with severe disability below poverty line",
            "how_to_apply": "Apply at Gram Panchayat / Block Office / Nadakacheri",
            "url": "https://nsap.nic.in",
            "documents_needed": "Aadhaar, disability certificate (40%+ disability), BPL/income certificate, bank passbook",
            "states": None,
            "max_income": 150000,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "for_disabled": 1,
            "eligibility_note": "Person with 80%+ disability, BPL, aged 18–59",
        },
        # 8. Karnataka Disability Pension
        {
            "name": "Karnataka Disability Pension Scheme",
            "ministry": "Karnataka Dept of Social Welfare",
            "level": "state",
            "benefit_amount": "Rs 1,400/month",
            "benefit_description": "State monthly pension for persons with disability in Karnataka",
            "how_to_apply": "Apply at Nadakacheri or online at sevasindhu.karnataka.gov.in",
            "url": "https://sevasindhu.karnataka.gov.in",
            "documents_needed": "Aadhaar, disability certificate (40%+), Karnataka domicile, income certificate, bank passbook",
            "states": "Karnataka",
            "max_income": 200000,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "for_disabled": 1,
            "eligibility_note": "Person with 40%+ disability residing in Karnataka, income below Rs 2 lakh/year",
        },
        # 9. Janani Suraksha Yojana
        {
            "name": "Janani Suraksha Yojana (JSY)",
            "ministry": "Ministry of Health & Family Welfare",
            "level": "central",
            "benefit_amount": "Rs 1,400 (rural) / Rs 1,000 (urban)",
            "benefit_description": "Cash assistance to pregnant women for institutional delivery to reduce maternal and infant mortality",
            "how_to_apply": "Register at nearest Government hospital / PHC / ASHA worker. Get JSY card.",
            "url": "https://nhm.gov.in/index1.php?lang=1&level=3&sublinkid=841&lid=309",
            "documents_needed": "Aadhaar, MCH card / ANC registration, bank passbook",
            "states": None,
            "max_income": None,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "for_pregnant": 1,
            "for_women": 1,
            "eligibility_note": "Pregnant women for institutional delivery; BPL or SC/ST women get priority but all eligible",
        },
        # 10. Karnataka Raitha Siri
        {
            "name": "Karnataka Raitha Siri Scheme",
            "ministry": "Karnataka Dept of Agriculture",
            "level": "state",
            "benefit_amount": "Rs 2,000/acre (up to 2 acres)",
            "benefit_description": "Input subsidy to support small and marginal farmers in Karnataka",
            "how_to_apply": "Apply at Raitha Samparka Kendra or through local agriculture officer",
            "url": "https://raitamitra.karnataka.gov.in",
            "documents_needed": "Aadhaar, land records (RTC), bank passbook, Karnataka farmer registration",
            "states": "Karnataka",
            "max_income": 250000,
            "for_farmer": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "eligibility_note": "Small & marginal farmers in Karnataka owning up to 2 acres",
        },
        # 11. PM Ujjwala Yojana
        {
            "name": "Pradhan Mantri Ujjwala Yojana (PMUY)",
            "ministry": "Ministry of Petroleum & Natural Gas",
            "level": "central",
            "benefit_amount": "Free LPG connection + first refill",
            "benefit_description": "Free LPG connection and first cylinder refill for BPL / SC/ST women",
            "how_to_apply": "Apply at nearest LPG distributor (HP/Indane/Bharat Gas) or pmuy.gov.in",
            "url": "https://www.pmuy.gov.in",
            "documents_needed": "Aadhaar, BPL ration card or SECC data, bank passbook",
            "states": None,
            "max_income": 150000,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "for_women": 1,
            "eligibility_note": "Women from BPL households, no existing LPG connection at home",
        },
        # 12. SC/ST Post-Matric Scholarship Karnataka
        {
            "name": "Karnataka SC/ST Post-Matric Scholarship",
            "ministry": "Karnataka Dept of Backward Classes Welfare",
            "level": "state",
            "benefit_amount": "Full tuition fee + maintenance allowance",
            "benefit_description": "Scholarship covering tuition fee and hostel/maintenance for SC/ST students in Karnataka",
            "how_to_apply": "Apply online at karepass.cgg.gov.in or through school/college",
            "url": "https://karepass.cgg.gov.in",
            "documents_needed": "Aadhaar, caste certificate, income certificate, mark sheet, fee receipt, bank passbook",
            "states": "Karnataka",
            "max_income": 250000,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "for_student": 1,
            "eligibility_note": "SC/ST students studying in Class 11+ in Karnataka, income below Rs 2.5 lakh/year",
        },
        # 13. PM Mudra Loan
        {
            "name": "PM Mudra Yojana (PMMY)",
            "ministry": "Ministry of Finance",
            "level": "central",
            "benefit_amount": "Rs 50,000 – Rs 10 lakh loan",
            "benefit_description": "Collateral-free loans for non-farm micro/small enterprises — Shishu (50K), Kishore (5L), Tarun (10L)",
            "how_to_apply": "Apply at any bank, MFI, or online at udyamimitra.in",
            "url": "https://www.mudra.org.in",
            "documents_needed": "Aadhaar, PAN, business proof / plan, bank statement",
            "states": None,
            "max_income": None,
            "for_self_employed": 1,
            "for_daily_wage": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "eligibility_note": "Anyone starting or expanding a small non-farm business",
        },
        # 14. Atal Pension Yojana
        {
            "name": "Atal Pension Yojana (APY)",
            "ministry": "Ministry of Finance / PFRDA",
            "level": "central",
            "benefit_amount": "Rs 1,000–5,000/month pension after age 60",
            "benefit_description": "Guaranteed pension scheme for unorganised sector workers — government co-contributes 50% for eligible subscribers",
            "how_to_apply": "Open at any bank with savings account or at nearest CSC",
            "url": "https://www.npscra.nsdl.co.in/scheme-details.php",
            "documents_needed": "Aadhaar, savings bank account, mobile number",
            "states": None,
            "max_income": None,
            "for_farmer": 1,
            "for_daily_wage": 1,
            "for_self_employed": 1,
            "for_unemployed": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "eligibility_note": "Indian citizens aged 18–40, not covered under any statutory social security scheme",
        },
        # 15. Stand Up India
        {
            "name": "Stand Up India Scheme",
            "ministry": "Ministry of Finance / SIDBI",
            "level": "central",
            "benefit_amount": "Rs 10 lakh – Rs 1 crore loan",
            "benefit_description": "Bank loans for SC/ST and women entrepreneurs to set up greenfield enterprises",
            "how_to_apply": "Apply at standupmitra.in or nearest bank branch",
            "url": "https://www.standupmitra.in",
            "documents_needed": "Aadhaar, PAN, business plan, caste/gender certificate as applicable, bank account",
            "states": None,
            "max_income": None,
            "for_self_employed": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "for_women": 1,
            "eligibility_note": "SC/ST borrowers or women setting up a new (greenfield) enterprise",
        },
    ]

    for s in schemes:
        # Build column list dynamically
        cols = [
            "name", "ministry", "level", "benefit_amount", "benefit_description",
            "how_to_apply", "url", "documents_needed", "states",
            "min_income", "max_income",
            "for_farmer", "for_daily_wage", "for_unemployed", "for_salaried",
            "for_self_employed", "for_any_occupation",
            "for_widow", "for_single_parent", "for_married", "for_single",
            "for_any_family",
            "for_disabled", "for_senior", "for_pregnant", "for_student",
            "for_any_special",
            "for_women", "eligibility_note",
        ]
        values = [s.get(col, 0) for col in cols]
        # Text defaults
        for i, col in enumerate(cols):
            if values[i] is None and col in ("states", "min_income", "max_income", "eligibility_note"):
                pass  # keep None (NULL in DB)
            elif values[i] is None:
                values[i] = 0

        placeholders = ", ".join(["?"] * len(cols))
        col_str = ", ".join(cols)
        c.execute(f"INSERT INTO schemes ({col_str}) VALUES ({placeholders})", values)

    conn.commit()
    print(f"✅ {len(schemes)} schemes inserted.")


def get_all_schemes():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM schemes")
    rows = c.fetchall()
    conn.close()
    return rows


def insert_scheme(s: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    cols = [
        "name", "ministry", "level", "benefit_amount", "benefit_description",
        "how_to_apply", "url", "documents_needed", "states",
        "min_income", "max_income",
        "for_farmer", "for_daily_wage", "for_unemployed", "for_salaried",
        "for_self_employed", "for_any_occupation",
        "for_widow", "for_single_parent", "for_married", "for_single",
        "for_any_family",
        "for_disabled", "for_senior", "for_pregnant", "for_student",
        "for_any_special",
        "for_women", "eligibility_note"
    ]
    values = []
    for col in cols:
        val = s.get(col, None)
        if col.startswith("for_") or col == "for_women":
            if val is True or val == 1 or str(val).strip().lower() in ("1", "true", "yes"):
                val = 1
            else:
                val = 0
        elif col in ("min_income", "max_income"):
            if val == "" or val is None:
                val = None
            else:
                try:
                    val = int(val)
                except ValueError:
                    val = None
        else:
            if val is not None:
                val = str(val).strip()
            if val == "":
                val = None
        values.append(val)

    placeholders = ", ".join(["?"] * len(cols))
    col_str = ", ".join(cols)
    c.execute(f"INSERT INTO schemes ({col_str}) VALUES ({placeholders})", values)
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def delete_scheme(scheme_id: int) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM schemes WHERE id = ?", (scheme_id,))
    conn.commit()
    rows_affected = c.rowcount
    conn.close()
    return rows_affected > 0


if __name__ == "__main__":
    init_db()
    rows = get_all_schemes()
    print(f"\n📋 Total schemes in DB: {len(rows)}")
    for r in rows:
        print(f"  {r['id']}. {r['name']} ({r['level']}) — {r['benefit_amount']}")

def insert_scheme(data: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    cols = [k for k in data if data[k] not in (None, "")]
    vals = [data[k] for k in cols]
    placeholders = ", ".join(["?"] * len(cols))
    col_str = ", ".join(cols)
    c.execute(f"INSERT INTO schemes ({col_str}) VALUES ({placeholders})", vals)
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id

def delete_scheme(scheme_id: int) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM schemes WHERE id = ?", (scheme_id,))
    conn.commit()
    affected = c.rowcount
    conn.close()
    return affected > 0