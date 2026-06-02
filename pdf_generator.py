"""
pdf_generator.py — Dynamic PDF Report Generator using ReportLab
For India Benefits Finder Portal
"""

import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


def generate_benefits_pdf(profile: dict, matches: list) -> io.BytesIO:
    """
    Generates a beautifully formatted PDF report containing the user's profile
    and eligible benefits (schemes, loans, scholarships) grouped by type.
    """
    buffer = io.BytesIO()
    
    # ── Page setup ──
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # ── Color Palette ──
    PRIMARY = colors.HexColor("#1e3a8a")     # Indigo/navy
    SECONDARY = colors.HexColor("#d97706")   # Saffron/Amber
    TEXT_DARK = colors.HexColor("#1f2937")   # Off-black
    TEXT_LIGHT = colors.HexColor("#6b7280")  # Gray
    BG_LIGHT = colors.HexColor("#f3f4f6")    # Light gray
    BORDER_COLOR = colors.HexColor("#e5e7eb")
    
    # ── Custom Typography Styles ──
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=PRIMARY,
        spaceAfter=5
    )
    
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=10,
        leading=12,
        textColor=TEXT_LIGHT,
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=PRIMARY,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        "SubSectionHeader",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=SECONDARY,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=TEXT_DARK
    )

    bold_body_style = ParagraphStyle(
        "ReportBodyBold",
        parent=body_style,
        fontName="Helvetica-Bold"
    )

    profile_label_style = ParagraphStyle(
        "ProfileLabel",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=PRIMARY
    )

    benefit_val_style = ParagraphStyle(
        "BenefitValue",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#10b981") # Green
    )
    
    footer_style = ParagraphStyle(
        "ReportFooter",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=10,
        textColor=TEXT_LIGHT,
        alignment=1, # Center
        spaceBefore=20
    )

    story = []
    
    # ── 1. HEADER SECTION ──
    story.append(Paragraph("INDIA BENEFITS FINDER PORTAL", title_style))
    story.append(Paragraph("Personalized Citizen Welfare & Security Benefits Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceAfter=15))
    
    # ── 2. PERSONAL PROFILE SUMMARY ──
    story.append(Paragraph("CITIZEN PROFILE SUMMARY", h1_style))
    story.append(Spacer(1, 4))
    
    # Format income safely
    inc_val = profile.get("income")
    inc_str = f"Rs {inc_val:,}/year" if inc_val is not None else "Not Specified"
    
    # Prepare profile table data
    profile_data = [
        [
            Paragraph("📍 State:", profile_label_style), Paragraph(profile.get("state") or "All-India", body_style),
            Paragraph("🏢 District:", profile_label_style), Paragraph((profile.get("district") or "Not Specified").capitalize(), body_style)
        ],
        [
            Paragraph("🧑‍🌾 Livelihood:", profile_label_style), Paragraph((profile.get("occupation") or "Not Specified").replace("_", " ").capitalize(), body_style),
            Paragraph("💰 Annual Income:", profile_label_style), Paragraph(inc_str, body_style)
        ],
        [
            Paragraph("👨‍👩‍👧 Family Status:", profile_label_style), Paragraph((profile.get("family") or "Not Specified").replace("_", " ").capitalize(), body_style),
            Paragraph("🚻 Gender:", profile_label_style), Paragraph((profile.get("gender") or "Not Specified").capitalize(), body_style)
        ],
        [
            Paragraph("🎂 Age:", profile_label_style), Paragraph(str(profile.get("age")) if profile.get("age") is not None else "Not Specified", body_style),
            Paragraph("🎓 Education:", profile_label_style), Paragraph((profile.get("education") or "Not Specified").capitalize(), body_style)
        ],
        [
            Paragraph("🌟 Caste Category:", profile_label_style), Paragraph((profile.get("caste_category") or "Not Specified").upper(), body_style),
            Paragraph("👪 Priority Group:", profile_label_style), Paragraph((profile.get("special") or "Not Specified").capitalize(), body_style)
        ]
    ]
    
    profile_table = Table(profile_data, colWidths=[100, 160, 100, 160])
    profile_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(profile_table)
    story.append(Spacer(1, 15))
    
    # ── 3. MATCHED BENEFITS SUMMARY ──
    story.append(Paragraph("ELIGIBLE CITIZEN BENEFITS & SUPPORT", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceAfter=10))
    
    if not matches:
        story.append(Paragraph("No directly matched benefits were found for your current profile. Please update your details to search again.", body_style))
    else:
        # Group by type
        schemes = [m for m in matches if m.get("type") == "scheme"]
        loans = [m for m in matches if m.get("type") == "loan"]
        scholarships = [m for m in matches if m.get("type") == "scholarship"]
        
        running_idx = 1
        
        def render_section(items, section_title, section_icon):
            nonlocal running_idx
            if not items:
                return
            
            story.append(Paragraph(f"{section_icon} {section_title} ({len(items)} matched)", h2_style))
            story.append(Spacer(1, 5))
            
            for item in items:
                benefit_block = []
                
                # Title & Department
                dept_str = f" Dept: {item.get('ministry') or 'Government Agency'}"
                benefit_block.append(Paragraph(f"<b>{running_idx}. {item['name']}</b> ({item['level'].upper()})<font color='gray'> | {dept_str}</font>", bold_body_style))
                
                # Financial amount
                benefit_block.append(Paragraph(f"💰 <b>Welfare Benefit:</b> <font color='#10b981'><b>{item['benefit_amount']}</b></font>", body_style))
                
                # Why qualify
                reasons = ", ".join(item.get("match_reasons", []))
                benefit_block.append(Paragraph(f"✅ <b>Why You Qualify:</b> Matches your {reasons}", body_style))
                
                # About
                if item.get("benefit_description"):
                    benefit_block.append(Paragraph(f"📋 <b>About the Program:</b> {item['benefit_description']}", body_style))
                
                # Documents
                docs = item.get("documents_needed") or "Aadhaar card, Income certificate"
                benefit_block.append(Paragraph(f"📄 <b>Required Documents:</b> {docs}", body_style))
                
                # How to apply
                apply_desc = item.get("how_to_apply") or "Apply online at official portal."
                benefit_block.append(Paragraph(f"🏛️ <b>How to Apply:</b> {apply_desc}", body_style))
                
                # URL
                if item.get("url"):
                    benefit_block.append(Paragraph(f"🔗 <b>Official Portal:</b> <font color='#1e3a8a'><u>{item['url']}</u></font>", body_style))
                
                benefit_block.append(Spacer(1, 10))
                running_idx += 1
                
                # Pack it up inside a KeepTogether to avoid nasty pagebreaks in the middle of a benefit!
                story.append(KeepTogether(benefit_block))
        
        render_section(schemes, "Government Welfare Schemes", "🏛️")
        render_section(loans, "Concessional Financial Loans", "💰")
        render_section(scholarships, "Scholarships & Educational Aid", "🎓")
        
    # ── 4. DISCLAIMER FOOTER ──
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=TEXT_LIGHT, spaceAfter=8))
    story.append(Paragraph(
        "Disclaimer: This report is generated automatically based on citizen profile inputs. "
        "Eligible benefits listed here are for guidance only. Always confirm official rules, "
        "deadlines, and procedures directly at designated government portals.",
        footer_style
    ))
    
    # ── Build the document ──
    doc.build(story)
    
    # Reset buffer pointer
    buffer.seek(0)
    return buffer
