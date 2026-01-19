"""PDF styling constants and configurations."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.units import inch, cm


# Page settings
PAGE_SIZE = A4
PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE
MARGIN_LEFT = 1 * inch
MARGIN_RIGHT = 1 * inch
MARGIN_TOP = 1.2 * inch
MARGIN_BOTTOM = 1 * inch

# Colors
PRIMARY_COLOR = colors.HexColor('#1a365d')  # Dark blue
SECONDARY_COLOR = colors.HexColor('#2b6cb0')  # Medium blue
ACCENT_COLOR = colors.HexColor('#ed8936')  # Orange
TEXT_COLOR = colors.HexColor('#2d3748')  # Dark gray
LIGHT_GRAY = colors.HexColor('#e2e8f0')  # Light gray for backgrounds
WHITE = colors.white

# Font settings
FONT_FAMILY = 'Helvetica'
FONT_FAMILY_BOLD = 'Helvetica-Bold'
FONT_FAMILY_ITALIC = 'Helvetica-Oblique'

# Logo settings
LOGO_WIDTH = 2.8 * inch
LOGO_HEIGHT = 0.45 * inch
HEADER_LOGO_X = PAGE_WIDTH - MARGIN_RIGHT - LOGO_WIDTH
HEADER_LOGO_Y = PAGE_HEIGHT - 0.7 * inch


def get_styles():
    """Get custom paragraph styles for PDF generation."""
    styles = getSampleStyleSheet()

    # Title style for cover page
    styles.add(ParagraphStyle(
        name='CoverTitle',
        parent=styles['Title'],
        fontName=FONT_FAMILY_BOLD,
        fontSize=28,
        textColor=PRIMARY_COLOR,
        alignment=TA_CENTER,
        spaceAfter=30,
        spaceBefore=50,
    ))

    # Subtitle style
    styles.add(ParagraphStyle(
        name='CoverSubtitle',
        parent=styles['Normal'],
        fontName=FONT_FAMILY,
        fontSize=16,
        textColor=SECONDARY_COLOR,
        alignment=TA_CENTER,
        spaceAfter=20,
    ))

    # Client name style
    styles.add(ParagraphStyle(
        name='ClientName',
        parent=styles['Normal'],
        fontName=FONT_FAMILY_BOLD,
        fontSize=20,
        textColor=PRIMARY_COLOR,
        alignment=TA_CENTER,
        spaceBefore=40,
        spaceAfter=20,
    ))

    # Section heading
    styles.add(ParagraphStyle(
        name='SectionHeading',
        parent=styles['Heading1'],
        fontName=FONT_FAMILY_BOLD,
        fontSize=18,
        textColor=PRIMARY_COLOR,
        alignment=TA_LEFT,
        spaceBefore=20,
        spaceAfter=12,
        borderPadding=10,
    ))

    # Subsection heading
    styles.add(ParagraphStyle(
        name='SubsectionHeading',
        parent=styles['Heading2'],
        fontName=FONT_FAMILY_BOLD,
        fontSize=14,
        textColor=SECONDARY_COLOR,
        alignment=TA_LEFT,
        spaceBefore=15,
        spaceAfter=8,
    ))

    # Body text - update existing style
    styles['BodyText'].fontName = FONT_FAMILY
    styles['BodyText'].fontSize = 11
    styles['BodyText'].textColor = TEXT_COLOR
    styles['BodyText'].alignment = TA_JUSTIFY
    styles['BodyText'].spaceBefore = 6
    styles['BodyText'].spaceAfter = 6
    styles['BodyText'].leading = 16

    # Disclaimer text
    styles.add(ParagraphStyle(
        name='DisclaimerText',
        parent=styles['Normal'],
        fontName=FONT_FAMILY,
        fontSize=10,
        textColor=TEXT_COLOR,
        alignment=TA_JUSTIFY,
        spaceBefore=4,
        spaceAfter=4,
        leading=14,
    ))

    # Disclaimer title
    styles.add(ParagraphStyle(
        name='DisclaimerTitle',
        parent=styles['Heading1'],
        fontName=FONT_FAMILY_BOLD,
        fontSize=20,
        textColor=PRIMARY_COLOR,
        alignment=TA_CENTER,
        spaceBefore=30,
        spaceAfter=30,
    ))

    # TOC Entry
    styles.add(ParagraphStyle(
        name='TOCEntry',
        parent=styles['Normal'],
        fontName=FONT_FAMILY,
        fontSize=12,
        textColor=TEXT_COLOR,
        alignment=TA_LEFT,
        spaceBefore=2,
        spaceAfter=2,
        leftIndent=0,
    ))

    # TOC Page Number
    styles.add(ParagraphStyle(
        name='TOCPage',
        parent=styles['Normal'],
        fontName=FONT_FAMILY_BOLD,
        fontSize=11,
        textColor=SECONDARY_COLOR,
        alignment=TA_RIGHT,
    ))

    # TOC Title
    styles.add(ParagraphStyle(
        name='TOCTitle',
        parent=styles['Heading1'],
        fontName=FONT_FAMILY_BOLD,
        fontSize=22,
        textColor=PRIMARY_COLOR,
        alignment=TA_CENTER,
        spaceBefore=20,
        spaceAfter=30,
    ))

    # Page number style
    styles.add(ParagraphStyle(
        name='PageNumber',
        parent=styles['Normal'],
        fontName=FONT_FAMILY,
        fontSize=10,
        textColor=TEXT_COLOR,
        alignment=TA_CENTER,
    ))

    # Bullet point
    styles.add(ParagraphStyle(
        name='BulletPoint',
        parent=styles['Normal'],
        fontName=FONT_FAMILY,
        fontSize=11,
        textColor=TEXT_COLOR,
        alignment=TA_LEFT,
        spaceBefore=4,
        spaceAfter=4,
        leftIndent=30,
        bulletIndent=15,
    ))

    # Chart caption
    styles.add(ParagraphStyle(
        name='ChartCaption',
        parent=styles['Normal'],
        fontName=FONT_FAMILY_ITALIC,
        fontSize=10,
        textColor=SECONDARY_COLOR,
        alignment=TA_CENTER,
        spaceBefore=8,
        spaceAfter=15,
    ))

    return styles


# Disclaimer text (fixed content)
DISCLAIMER_TEXT = """
<b>CONFIDENTIALITY NOTICE</b>

This document contains confidential and proprietary information. The information contained herein is intended solely for the use of the individual or entity to whom it is addressed.

<b>DISCLAIMER</b>

The information provided in this report is for general informational purposes only. While we strive to provide accurate and up-to-date information, we make no representations or warranties of any kind, express or implied, about the completeness, accuracy, reliability, suitability, or availability of the information contained in this document.

Any reliance you place on such information is strictly at your own risk. In no event will we be liable for any loss or damage including without limitation, indirect or consequential loss or damage, or any loss or damage whatsoever arising from loss of data or profits arising out of, or in connection with, the use of this document.

<b>INTELLECTUAL PROPERTY</b>

All content, trademarks, logos, and intellectual property contained in this document are the property of Infopercept Consulting Pvt. Ltd. and are protected by applicable intellectual property laws. Unauthorized use, reproduction, or distribution of this material is strictly prohibited.

<b>CONTACT INFORMATION</b>

For questions regarding this document, please contact:
Infopercept Consulting Pvt. Ltd.
Email: info@infopercept.com
Website: www.infopercept.com

<b>VERSION CONTROL</b>

This document is subject to periodic updates and revisions. Please ensure you are referencing the most current version.

Generated by Agentic PDF Generator - Powered by AI
"""
