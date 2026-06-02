"""
scheme_db.py — SQLite database setup + queries for India Benefits Finder
"""

import sqlite3
import os
import sys

# Force UTF-8 stdout/stderr on Windows to prevent UnicodeEncodeError
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

DATABASE_PATH = os.environ.get("DATABASE_PATH")
if not DATABASE_PATH:
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemes.db")


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the database tables and populate schemes, loans, and scholarships."""
    conn = get_connection()
    c = conn.cursor()

    # Drop old tables if the new profiling columns are missing
    try:
        c.execute("SELECT min_age FROM schemes LIMIT 1")
    except sqlite3.OperationalError:
        print("⚠️ Database schema is outdated. Dropping and recreating tables...")
        c.execute("DROP TABLE IF EXISTS schemes")
        c.execute("DROP TABLE IF EXISTS loans")
        c.execute("DROP TABLE IF EXISTS scholarships")

    # Define common schema SQL
    schema_sql = """
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

        eligibility_note TEXT,

        -- Advanced user profile filters (Phase 2)
        min_age INTEGER DEFAULT NULL,
        max_age INTEGER DEFAULT NULL,
        caste_category TEXT DEFAULT NULL, -- general, obc, sc, st (comma-separated allowed values)
        education TEXT DEFAULT NULL,      -- e.g. student, graduate, 10th, 12th
        districts TEXT DEFAULT NULL       -- comma-separated districts
    """

    c.execute(f"CREATE TABLE IF NOT EXISTS schemes ({schema_sql})")
    c.execute(f"CREATE TABLE IF NOT EXISTS loans ({schema_sql})")
    c.execute(f"CREATE TABLE IF NOT EXISTS scholarships ({schema_sql})")

    conn.commit()
    _populate_schemes(conn)
    _populate_loans(conn)
    _populate_scholarships(conn)
    conn.close()
    print(f"✅ Database initialised at {DATABASE_PATH}")


def _insert_entry(c, table, s):
    cols = [
        "name", "ministry", "level", "benefit_amount", "benefit_description",
        "how_to_apply", "url", "documents_needed", "states",
        "min_income", "max_income",
        "for_farmer", "for_daily_wage", "for_unemployed", "for_salaried",
        "for_self_employed", "for_any_occupation",
        "for_widow", "for_single_parent", "for_married", "for_single",
        "for_any_family",
        "for_disabled", "for_senior", "for_pregnant", "for_student",
        "for_any_special", "for_women", "eligibility_note",
        "min_age", "max_age", "caste_category", "education", "districts"
    ]
    values = [s.get(col, None) for col in cols]
    for i, col in enumerate(cols):
        if values[i] is None and col in ("states", "min_income", "max_income", "eligibility_note", 
                                        "min_age", "max_age", "caste_category", "education", "districts"):
            pass  # Keep NULL in DB
        elif values[i] is None:
            values[i] = 0

    placeholders = ", ".join(["?"] * len(cols))
    col_str = ", ".join(cols)
    c.execute(f"INSERT INTO {table} ({col_str}) VALUES ({placeholders})", values)


def _populate_schemes(conn):
    """Insert the 15 schemes. Safe to re-run (skips if exists)."""
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
            "min_age": 40,
            "max_age": 79,
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
            "min_age": 18,
            "max_age": 59,
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
            "caste_category": "sc,st",
            "eligibility_note": "SC/ST students studying in Class 11+ in Karnataka, income below Rs 2.5 lakh/year",
        },
        # 13. PM Mudra Loan (General)
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
            "min_age": 18,
            "max_age": 40,
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
            "caste_category": "sc,st",
            "eligibility_note": "SC/ST borrowers or women setting up a new (greenfield) enterprise",
        },
    ]

    for s in schemes:
        _insert_entry(c, "schemes", s)

    conn.commit()
    print(f"✅ {len(schemes)} schemes inserted.")


def _populate_loans(conn):
    """Insert 12 real Indian loans."""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM loans")
    if c.fetchone()[0] > 0:
        print("ℹ️  Loans already populated — skipping.")
        return

    loans = [
        # 1. PM SVANidhi
        {
            "name": "PM Street Vendor’s Atmanirbhar Nidhi (PM SVANidhi)",
            "ministry": "Ministry of Housing and Urban Affairs",
            "level": "central",
            "benefit_amount": "Rs 10,000 (first tranche) working capital loan",
            "benefit_description": "Collateral-free working capital loan up to Rs 10,000, interest subsidy of 7%, cashback on digital transactions",
            "how_to_apply": "Apply at any commercial bank or through standard portal pmsvanidhi.mohua.gov.in or CSC",
            "url": "https://pmsvanidhi.mohua.gov.in",
            "documents_needed": "Aadhaar card, Voter Identity Card, Certificate of Vending (COV) or Letter of Recommendation (LOR)",
            "states": None,
            "max_income": 200000,
            "for_daily_wage": 1,
            "for_self_employed": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "eligibility_note": "Street vendors active in urban areas",
        },
        # 2. PM Mudra Yojana - Shishu
        {
            "name": "PM Mudra Loan (PMMY) - Shishu Category",
            "ministry": "Ministry of Finance",
            "level": "central",
            "benefit_amount": "Collateral-free loan up to Rs 50,000",
            "benefit_description": "Concessional collateral-free loan up to Rs 50,000 for starting micro-businesses or shop expansions",
            "how_to_apply": "Apply online at udyamimitra.in or visit any public/private commercial bank",
            "url": "https://www.mudra.org.in",
            "documents_needed": "Aadhaar, PAN card, business address proof, bank account statement for past 6 months",
            "states": None,
            "for_self_employed": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "eligibility_note": "New or existing micro-entrepreneurs and retail traders",
        },
        # 3. PM Mudra Yojana - Kishore
        {
            "name": "PM Mudra Loan (PMMY) - Kishore Category",
            "ministry": "Ministry of Finance",
            "level": "central",
            "benefit_amount": "Loan from Rs 50,000 to Rs 5 Lakh",
            "benefit_description": "Concessional, collateral-free credit from Rs 50,000 up to Rs 5,00,000 for expanding micro-businesses",
            "how_to_apply": "Apply at any public sector bank or via udyamimitra.in",
            "url": "https://www.mudra.org.in",
            "documents_needed": "Aadhaar, PAN, business registration proof, quotation of machinery, balance sheet projections",
            "states": None,
            "for_self_employed": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "eligibility_note": "Established small business units needing working capital or equipment",
        },
        # 4. PMEGP
        {
            "name": "Prime Minister Employment Generation Programme (PMEGP)",
            "ministry": "Ministry of MSME",
            "level": "central",
            "benefit_amount": "Up to Rs 50 Lakh manufacturing loan with 15–35% subsidy",
            "benefit_description": "Credit-linked subsidy loan up to Rs 50 Lakh (manufacturing) or Rs 20 Lakh (service) with up to 35% government subsidy",
            "how_to_apply": "Apply online at kviconline.gov.in/pmegpeportal or visit district industry centres (DIC)",
            "url": "https://www.kviconline.gov.in/pmegpeportal/",
            "documents_needed": "Aadhaar, project report, education certificate (min 8th pass), caste certificate, PAN card",
            "states": None,
            "min_age": 18,
            "for_self_employed": 1,
            "for_unemployed": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "education": "8th, 10th, 12th, graduate",
            "eligibility_note": "Individuals aged 18+ to establish new micro-enterprises. Requires 8th class pass for projects above Rs 10L",
        },
        # 5. Stand Up India - Women & SC/ST Entrepreneurs
        {
            "name": "Stand Up India Scheme for Women & SC/ST",
            "ministry": "Ministry of Finance",
            "level": "central",
            "benefit_amount": "Rs 10 Lakh to Rs 1 Crore bank loan",
            "benefit_description": "Bank loans between Rs 10 Lakh and Rs 1 Crore for setting up new (greenfield) enterprises in manufacturing, services, or trading",
            "how_to_apply": "Apply at standupmitra.in or direct at any commercial bank branch",
            "url": "https://www.standupmitra.in",
            "documents_needed": "Aadhaar, PAN, business plan, caste certificate (if SC/ST), woman entrepreneur self-declaration, bank statement",
            "states": None,
            "min_age": 18,
            "for_self_employed": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "for_women": 1,
            "caste_category": "sc,st",
            "eligibility_note": "At least one SC/ST borrower or one Woman borrower per bank branch for new businesses",
        },
        # 6. PM Vishwakarma Concessional Loan
        {
            "name": "PM Vishwakarma Concessional Credit Support",
            "ministry": "Ministry of MSME",
            "level": "central",
            "benefit_amount": "Rs 3 Lakh business loan at 5% interest",
            "benefit_description": "Concessional loan support up to Rs 3 Lakh in two tranches (Rs 1 Lakh first, Rs 2 Lakh second) at a low interest rate of 5% p.a.",
            "how_to_apply": "Register on pmvishwakarma.gov.in or through nearest Common Service Centre (CSC)",
            "url": "https://pmvishwakarma.gov.in",
            "documents_needed": "Aadhaar, ration card, mobile linked with Aadhaar, bank passbook, trade-related declaration",
            "states": None,
            "for_self_employed": 1,
            "for_farmer": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "eligibility_note": "Artisans and craftspeople working in 18 traditional trades (e.g. weavers, carpenters, potters)",
        },
        # 7. NSKFDC Loan for Sanitation Workers
        {
            "name": "NSKFDC Concessional Self-Employment Loan",
            "ministry": "Ministry of Social Justice and Empowerment",
            "level": "central",
            "benefit_amount": "Up to Rs 15 Lakh business loan at 4–6% interest",
            "benefit_description": "Concessional loans up to Rs 15 Lakh for small self-employment ventures at low interest rates of 4% to 6% p.a. for sanitation workers",
            "how_to_apply": "Apply through State Channelising Agencies (SCA) of NSKFDC or designated regional rural banks",
            "url": "https://nskfdc.nic.in",
            "documents_needed": "Aadhaar, Sanitation Worker Identity Card, income certificate, BPL ration card",
            "states": None,
            "max_income": 300000,
            "for_daily_wage": 1,
            "for_unemployed": 1,
            "for_self_employed": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "eligibility_note": "Sanitation workers, manual scavengers, and their direct dependants",
        },
        # 8. NBCFDC Swarnima Scheme for OBC Women
        {
            "name": "NBCFDC Swarnima Scheme for OBC Women Entrepreneurs",
            "ministry": "Ministry of Social Justice and Empowerment",
            "level": "central",
            "benefit_amount": "Up to Rs 2 Lakh business loan at 5% interest",
            "benefit_description": "Concessional business loans up to Rs 2,00,000 for women from backward classes at low interest rates of 5% p.a. to prevent high-interest debts",
            "how_to_apply": "Apply through NBCFDC State Channelising Agencies (SCA) in respective states",
            "url": "http://www.nbcfdc.gov.in",
            "documents_needed": "Aadhaar, OBC caste certificate, income certificate (under Rs 3L), business proposal, bank details",
            "states": None,
            "min_age": 18,
            "max_age": 55,
            "max_income": 300000,
            "for_self_employed": 1,
            "for_unemployed": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "for_women": 1,
            "caste_category": "obc",
            "eligibility_note": "Women belonging to Backward Classes (OBC) aged 18–55 with household income under Rs 3 Lakh/year",
        },
        # 9. NSFDC Laghu Vyavasay Yojana
        {
            "name": "NSFDC Laghu Vyavasay Yojana (SC Small Business Loan)",
            "ministry": "Ministry of Social Justice and Empowerment",
            "level": "central",
            "benefit_amount": "Concessional loan up to Rs 3 Lakh at 6% interest",
            "benefit_description": "Financial assistance loan up to Rs 3,00,000 for SC community members to set up small business units at 6% p.a. interest rate",
            "how_to_apply": "Apply through State Channelising Agencies (SCA) of NSFDC in respective states",
            "url": "https://nsfdc.nic.in",
            "documents_needed": "Aadhaar, SC caste certificate, family income certificate, business space occupancy proof, bank account",
            "states": None,
            "min_age": 18,
            "max_income": 300000,
            "for_self_employed": 1,
            "for_unemployed": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "caste_category": "sc",
            "eligibility_note": "Scheduled Caste (SC) individuals aged 18+ with household income under Rs 3 Lakh/year",
        },
        # 10. Adivasi Mahila Sashaktikaran Yojana (NSTFDC)
        {
            "name": "Adivasi Mahila Sashaktikaran Yojana (AMSY)",
            "ministry": "Ministry of Tribal Affairs",
            "level": "central",
            "benefit_amount": "Concessional loan up to Rs 1 Lakh at 4% interest",
            "benefit_description": "Exclusive concessional business scheme for ST women to start small ventures, offering up to Rs 1 Lakh at extremely low interest of 4% p.a.",
            "how_to_apply": "Apply through NSTFDC State Channelising Agencies (SCA) or local tribal development corporations",
            "url": "https://nstfdc.tribal.gov.in",
            "documents_needed": "Aadhaar, ST caste certificate, family income certificate, bank passbook",
            "states": None,
            "min_age": 18,
            "max_income": 300000,
            "for_self_employed": 1,
            "for_farmer": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "for_women": 1,
            "caste_category": "st",
            "eligibility_note": "Scheduled Tribe (ST) women aged 18+ with household income under Rs 3 Lakh/year",
        },
        # 11. NHFDC Divyangjan Swavalamban Scheme
        {
            "name": "NHFDC Divyangjan Swavalamban Scheme (Disability Loan)",
            "ministry": "Ministry of Social Justice and Empowerment",
            "level": "central",
            "benefit_amount": "Concessional business loan up to Rs 5 Lakh at 4.5–8% interest",
            "benefit_description": "Collateral-free low-interest loans up to Rs 5 Lakh for disabled persons to set up self-employment ventures",
            "how_to_apply": "Apply through state channelising agencies or empanelled public sector banks (like PNB, SBI)",
            "url": "http://www.nhfdc.nic.in",
            "documents_needed": "Aadhaar, Disability Certificate (40%+), business plan, academic certificate (if applicable), bank passbook",
            "states": None,
            "min_age": 18,
            "max_age": 60,
            "for_disabled": 1,
            "for_self_employed": 1,
            "for_unemployed": 1,
            "for_any_family": 1,
            "eligibility_note": "Persons with 40%+ permanent disability aged 18–60 years who want to start a business",
        },
        # 12. Karnataka Devaraj Urs Self-Employment Loan
        {
            "name": "Karnataka Devaraj Urs Self-Employment Loan",
            "ministry": "Karnataka Backward Classes Welfare Dept",
            "level": "state",
            "benefit_amount": "Rs 2 Lakh business loan with 20% subsidy",
            "benefit_description": "Low interest self-employment loan up to Rs 2 Lakh with a 20% government capital subsidy (up to Rs 20,000) for starting small businesses in Karnataka",
            "how_to_apply": "Apply online at adb.karnataka.gov.in or through D. Devaraj Urs Backward Classes Development Corporation office",
            "url": "https://dbwd.karnataka.gov.in",
            "documents_needed": "Aadhaar card, Karnataka domicile proof, OBC caste certificate, income certificate, business project draft",
            "states": "Karnataka",
            "min_age": 18,
            "max_age": 45,
            "max_income": 150000,
            "for_self_employed": 1,
            "for_unemployed": 1,
            "for_any_family": 1,
            "for_any_special": 1,
            "caste_category": "obc",
            "eligibility_note": "Backward Classes (OBC Category 1, 2A, 3A, 3B) residents of Karnataka aged 18-45",
        },
    ]

    for l in loans:
        _insert_entry(c, "loans", l)

    conn.commit()
    print(f"✅ {len(loans)} loans inserted.")


def _populate_scholarships(conn):
    """Insert 12 real Indian scholarships."""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM scholarships")
    if c.fetchone()[0] > 0:
        print("ℹ️  Scholarships already populated — skipping.")
        return

    scholarships = [
        # 1. NMMSS
        {
            "name": "National Means-Cum-Merit Scholarship Scheme (NMMSS)",
            "ministry": "Ministry of Education",
            "level": "central",
            "benefit_amount": "Rs 12,000 per year",
            "benefit_description": "Financial assistance of Rs 12,000 per annum to student studying in classes 9 to 12 to arrest dropout rates",
            "how_to_apply": "Apply online on National Scholarship Portal scholarships.gov.in",
            "url": "https://scholarships.gov.in",
            "documents_needed": "Aadhaar, income certificate (under 3.5L), class 8 mark sheet (min 55%), school id card",
            "states": None,
            "max_income": 350000,
            "for_student": 1,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "education": "8th, 9th, 10th, student",
            "eligibility_note": "Students studying in government or local body schools in class 9 with family income under Rs 3.5 Lakh/year",
        },
        # 2. PM YASASVI Post-Matric Scholarship
        {
            "name": "PM Young Achievers Scholarship Scheme (PM YASASVI) for OBC/EBC",
            "ministry": "Ministry of Social Justice and Empowerment",
            "level": "central",
            "benefit_amount": "Up to Rs 75,000 per year",
            "benefit_description": "Financial support covering tuition fee and maintenance allowance up to Rs 75,000/year for Class 11-12 & higher education",
            "how_to_apply": "Apply online at scholarships.gov.in or through NTA YASASVI portal",
            "url": "https://yet.nta.ac.in",
            "documents_needed": "Aadhaar, OBC/EBC caste certificate, previous class mark sheet, family income certificate",
            "states": None,
            "max_income": 250000,
            "for_student": 1,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "caste_category": "obc",
            "education": "10th, 12th, student",
            "eligibility_note": "OBC, EBC and DNT students studying in class 11 or college with income below Rs 2.5 Lakh/year",
        },
        # 3. Begum Hazrat Mahal National Scholarship
        {
            "name": "Begum Hazrat Mahal National Scholarship for Minority Girls",
            "ministry": "Ministry of Minority Affairs",
            "level": "central",
            "benefit_amount": "Rs 5,000–6,000 per year",
            "benefit_description": "Scholarship for minority girl students (Muslim, Christian, Sikh, Buddhist, Jain, Parsi) for Class 9 to 12",
            "how_to_apply": "Apply online at National Scholarship Portal (NSP) scholarships.gov.in",
            "url": "https://scholarships.gov.in",
            "documents_needed": "Aadhaar, self-declaration of minority community, class 8/10 mark sheet, income certificate",
            "states": None,
            "max_income": 200000,
            "for_student": 1,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "for_women": 1,
            "education": "8th, 9th, 10th, 12th, student",
            "eligibility_note": "Girl students belonging to national minority communities studying in Class 9-12 with min 50% marks",
        },
        # 4. AICTE Pragati Scholarship Scheme
        {
            "name": "AICTE Pragati Scholarship Scheme for Girl Students (Technical Degree)",
            "ministry": "Ministry of Education",
            "level": "central",
            "benefit_amount": "Rs 50,000 per year",
            "benefit_description": "Tuition fee and contingency support of Rs 50,000/year for girls admitted to first-year technical degree (B.E/B.Tech) or diploma courses",
            "how_to_apply": "Apply online through National Scholarship Portal scholarships.gov.in",
            "url": "https://www.aicte-india.org/schemes/students-development-schemes",
            "documents_needed": "Class 10 and 12 mark sheets, fee receipt, college admission letter, income certificate (under 8L)",
            "states": None,
            "max_income": 800000,
            "for_student": 1,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "for_women": 1,
            "education": "12th, graduate, student",
            "eligibility_note": "Girl students admitted to AICTE approved technical degree/diploma courses, max 2 girls per family",
        },
        # 5. AICTE Saksham Scholarship
        {
            "name": "AICTE Saksham Scholarship for Specially Abled Students",
            "ministry": "Ministry of Education",
            "level": "central",
            "benefit_amount": "Rs 50,000 per year",
            "benefit_description": "Financial support of Rs 50,000 per annum for specially abled students pursuing technical education (degree/diploma)",
            "how_to_apply": "Apply online on National Scholarship Portal scholarships.gov.in",
            "url": "https://www.aicte-india.org",
            "documents_needed": "Disability certificate (min 40%), admission letter, academic transcripts, income certificate",
            "states": None,
            "max_income": 800000,
            "for_disabled": 1,
            "for_student": 1,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "education": "12th, graduate, student",
            "eligibility_note": "Specially-abled students (40%+ disability) admitted to first year of technical degree/diploma in approved institutes",
        },
        # 6. Central Sector Scheme of Scholarship (CSSS)
        {
            "name": "Central Sector Scheme of Scholarship for College and University Students",
            "ministry": "Ministry of Education",
            "level": "central",
            "benefit_amount": "Rs 12,000 to Rs 20,000 per year",
            "benefit_description": "Financial aid of Rs 12,000/year for graduation and Rs 20,000/year for post-graduate students to cover university boarding and fees",
            "how_to_apply": "Apply online on National Scholarship Portal scholarships.gov.in",
            "url": "https://scholarships.gov.in",
            "documents_needed": "Aadhaar card, class 12 mark sheet, income certificate, bank account details, college fee receipt",
            "states": None,
            "max_income": 450000,
            "for_student": 1,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "education": "12th, graduate, postgraduate, student",
            "eligibility_note": "Students above 80th percentile in respective Class 12 board, pursuing regular college courses",
        },
        # 7. Post Matric Scholarship for SC Students
        {
            "name": "Central Sector Post-Matric Scholarship for SC Students",
            "ministry": "Ministry of Social Justice and Empowerment",
            "level": "central",
            "benefit_amount": "Full fee reimbursement + Rs 13,500/year allowance",
            "benefit_description": "100% reimbursement of non-refundable tuition fee and academic/hostel maintenance allowance up to Rs 13,500/year for Scheduled Caste students",
            "how_to_apply": "Register and apply online on National Scholarship Portal or respective state portals",
            "url": "https://scholarships.gov.in",
            "documents_needed": "Aadhaar, SC caste certificate, family income certificate, college fee receipt, bank passbook",
            "states": None,
            "max_income": 250000,
            "for_student": 1,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "caste_category": "sc",
            "education": "10th, 12th, graduate, postgraduate, student",
            "eligibility_note": "Scheduled Caste (SC) students studying at post-matriculation or post-secondary levels",
        },
        # 8. Post Matric Scholarship for ST Students
        {
            "name": "Central Sector Post-Matric Scholarship for ST Students",
            "ministry": "Ministry of Tribal Affairs",
            "level": "central",
            "benefit_amount": "Full fee cover + Rs 12,000/year boarding stipend",
            "benefit_description": "Full compulsory fee reimbursement and boarding allowance up to Rs 12,000/year for Scheduled Tribe students studying in Class 11+ or college",
            "how_to_apply": "Apply through NSP scholarships.gov.in or respective state tribal welfare portals",
            "url": "https://scholarships.gov.in",
            "documents_needed": "Aadhaar, ST caste certificate, family income certificate, bank account details, college fee details",
            "states": None,
            "max_income": 250000,
            "for_student": 1,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "caste_category": "st",
            "education": "10th, 12th, graduate, postgraduate, student",
            "eligibility_note": "Scheduled Tribe (ST) students studying post-matric courses with family income under Rs 2.5 Lakh/year",
        },
        # 9. Post-Matric Scholarship for Minorities
        {
            "name": "Post-Matric Scholarship Scheme for Minorities",
            "ministry": "Ministry of Minority Affairs",
            "level": "central",
            "benefit_amount": "Up to Rs 10,000 per year",
            "benefit_description": "Tuition fee reimbursement and monthly maintenance stipend for minority students studying in class 11 up to PhD",
            "how_to_apply": "Apply online at National Scholarship Portal (NSP) scholarships.gov.in",
            "url": "https://scholarships.gov.in",
            "documents_needed": "Aadhaar card, self-certified minority community certificate, previous exam mark sheet (min 50%), income certificate",
            "states": None,
            "max_income": 200000,
            "for_student": 1,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "education": "10th, 12th, graduate, postgraduate, student",
            "eligibility_note": "Students from minority communities studying in Class 11/12, college, or technical courses",
        },
        # 10. National Overseas Scholarship for SC/ST
        {
            "name": "National Overseas Scholarship (NOS) for SC/ST Candidates",
            "ministry": "Ministry of Social Justice / Tribal Affairs",
            "level": "central",
            "benefit_amount": "Full tuition fee + USD 15,400/year living allowance",
            "benefit_description": "Fully-funded scholarship covering international tuition, return flights, and annual living allowance of USD 15,400 for Master's/PhD studies abroad",
            "how_to_apply": "Apply online at nosmsje.gov.in or tribal.nic.in during active application cycles (usually Feb-April)",
            "url": "https://nosmsje.gov.in",
            "documents_needed": "Aadhaar, SC/ST caste certificate, income certificate, foreign university unconditional offer letter, degree certificates",
            "states": None,
            "max_age": 35,
            "max_income": 800000,
            "for_student": 1,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "caste_category": "sc,st",
            "education": "graduate, postgraduate, student",
            "eligibility_note": "SC/ST candidates aged under 35 with at least 60% marks in graduation/master's, planning to study abroad",
        },
        # 11. Karnataka Vidyasiri (Food & Accommodation)
        {
            "name": "Karnataka Vidyasiri Scheme (Food & Accommodation)",
            "ministry": "Karnataka Dept of Backward Classes Welfare",
            "level": "state",
            "benefit_amount": "Rs 1,500 per month (Rs 15,000 per year)",
            "benefit_description": "Boarding and lodging assistance of Rs 1,500/month for 10 months for OBC/SC/ST students pursuing post-matric courses in Karnataka",
            "how_to_apply": "Apply online on State Scholarship Portal (SSP) ssp.postmatric.karnataka.gov.in",
            "url": "https://ssp.postmatric.karnataka.gov.in",
            "documents_needed": "Aadhaar card, SSP Student ID, income certificate, OBC caste certificate, hostel admission receipt",
            "states": "Karnataka",
            "max_income": 250000,
            "for_student": 1,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "caste_category": "obc,sc,st",
            "education": "10th, 12th, graduate, postgraduate, student",
            "eligibility_note": "Karnataka domicile students from backward classes studying post-matric courses and residing in non-government hostels",
        },
        # 12. Maharashtra Rajarshi Shahu Maharaj Fee Reimbursement
        {
            "name": "Maharashtra Rajarshi Chhatrapati Shahu Maharaj Fee Reimbursement",
            "ministry": "Maharashtra Dept of Higher & Technical Education",
            "level": "state",
            "benefit_amount": "50% tuition and exam fee reimbursement",
            "benefit_description": "Reimbursement of 50% of college tuition and exam fees for professional degree/diploma courses in Maharashtra",
            "how_to_apply": "Apply online on MahaDBT portal mahadbt.maharashtra.gov.in",
            "url": "https://mahadbt.maharashtra.gov.in",
            "documents_needed": "Aadhaar, Maharashtra domicile certificate, income certificate (under 8L), college fee structure, previous mark sheets",
            "states": "Maharashtra",
            "max_income": 800000,
            "for_student": 1,
            "for_any_occupation": 1,
            "for_any_family": 1,
            "caste_category": "general,obc",
            "education": "12th, graduate, postgraduate, student",
            "eligibility_note": "Maharashtra domicile students enrolled in professional/technical college courses through CAP rounds",
        },
    ]

    for s in scholarships:
        _insert_entry(c, "scholarships", s)

    conn.commit()
    print(f"✅ {len(scholarships)} scholarships inserted.")


def get_all_schemes():
    return get_all_benefits("schemes")


def get_all_benefits(table_name: str) -> list:
    if table_name not in ("schemes", "loans", "scholarships"):
        return []
    conn = get_connection()
    c = conn.cursor()
    c.execute(f"SELECT * FROM {table_name}")
    rows = c.fetchall()
    conn.close()
    return rows


def insert_scheme(s: dict) -> int:
    return insert_benefit("schemes", s)


def insert_benefit(table_name: str, s: dict) -> int:
    if table_name not in ("schemes", "loans", "scholarships"):
        return 0
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
        "for_women", "eligibility_note",
        "min_age", "max_age", "caste_category", "education", "districts"
    ]
    values = []
    for col in cols:
        val = s.get(col, None)
        if col.startswith("for_") or col == "for_women":
            if val is True or val == 1 or str(val).strip().lower() in ("1", "true", "yes"):
                val = 1
            else:
                val = 0
        elif col in ("min_income", "max_income", "min_age", "max_age"):
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
    c.execute(f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders})", values)
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def delete_scheme(scheme_id: int) -> bool:
    return delete_benefit("schemes", scheme_id)


def delete_benefit(table_name: str, benefit_id: int) -> bool:
    if table_name not in ("schemes", "loans", "scholarships"):
        return False
    conn = get_connection()
    c = conn.cursor()
    c.execute(f"DELETE FROM {table_name} WHERE id = ?", (benefit_id,))
    conn.commit()
    rows_affected = c.rowcount
    conn.close()
    return rows_affected > 0


if __name__ == "__main__":
    init_db()
    for t in ("schemes", "loans", "scholarships"):
        rows = get_all_benefits(t)
        print(f"\n📋 Total {t} in DB: {len(rows)}")
        for r in rows[:3]: # print first 3
            print(f"  {r['id']}. {r['name']} ({r['level']}) — {r['benefit_amount']}")