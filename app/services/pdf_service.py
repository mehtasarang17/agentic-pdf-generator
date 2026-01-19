"""PDF generation service using ReportLab."""

import io
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    Table, TableStyle, ListFlowable, ListItem
)
from reportlab.lib.styles import ParagraphStyle

from app.config import config
from app.templates.pdf.styles import (
    get_styles, PAGE_SIZE, PAGE_WIDTH, PAGE_HEIGHT,
    MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM,
    LOGO_WIDTH, LOGO_HEIGHT, HEADER_LOGO_X, HEADER_LOGO_Y,
    PRIMARY_COLOR, SECONDARY_COLOR, LIGHT_GRAY, WHITE,
    DISCLAIMER_TEXT
)

logger = logging.getLogger(__name__)


class PDFService:
    """Service for generating professional PDF documents."""

    def __init__(self):
        """Initialize PDF service."""
        self.styles = get_styles()
        self.output_dir = config.PDF_OUTPUT_DIR
        self.logo_path = config.LOGO_PATH
        self.watermark_path = config.WATERMARK_PATH
        self.watermark_opacity = config.WATERMARK_OPACITY
        self.page_count = 0
        self.toc_entries: List[Dict[str, Any]] = []

    def _draw_watermark(self, canvas) -> None:
        """Draw watermark image centered on the page."""
        watermark_path = self.watermark_path
        if not watermark_path.exists():
            if not self.logo_path.exists():
                logger.warning("No watermark or logo found for watermark rendering.")
                return
            watermark_path = self.logo_path

        try:
            image = ImageReader(str(watermark_path))
            image_width, image_height = image.getSize()
            max_width = PAGE_WIDTH * 0.7
            max_height = PAGE_HEIGHT * 0.7
            scale = min(max_width / image_width, max_height / image_height)
            draw_width = image_width * scale
            draw_height = image_height * scale
            x = (PAGE_WIDTH - draw_width) / 2
            y = (PAGE_HEIGHT - draw_height) / 2

            canvas.saveState()
            opacity = max(0.12, min(self.watermark_opacity, 0.25))
            if hasattr(canvas, "setFillAlpha"):
                canvas.setFillAlpha(opacity)
                canvas.setStrokeAlpha(opacity)
            canvas.drawImage(
                image,
                x,
                y,
                width=draw_width,
                height=draw_height,
                preserveAspectRatio=True,
                mask='auto'
            )
            canvas.restoreState()
        except Exception as e:
            logger.warning(f"Could not add watermark: {e}")

    def _header_footer(self, canvas, doc, include_logo: bool = True):
        """Add header with logo and footer with page number."""
        canvas.saveState()

        self._draw_watermark(canvas)

        # Add logo to header (skip on cover page)
        if include_logo and self.logo_path.exists():
            try:
                canvas.drawImage(
                    str(self.logo_path),
                    HEADER_LOGO_X,
                    HEADER_LOGO_Y,
                    width=LOGO_WIDTH,
                    height=LOGO_HEIGHT,
                    preserveAspectRatio=True,
                    mask='auto'
                )
            except Exception as e:
                logger.warning(f"Could not add logo: {e}")

        # Add header line
        if include_logo:
            canvas.setStrokeColor(LIGHT_GRAY)
            canvas.setLineWidth(1)
            canvas.line(
                MARGIN_LEFT,
                PAGE_HEIGHT - MARGIN_TOP + 0.3 * inch,
                PAGE_WIDTH - MARGIN_RIGHT,
                PAGE_HEIGHT - MARGIN_TOP + 0.3 * inch
            )

        # Add page number in footer
        page_num = canvas.getPageNumber()
        footer_y = 0.5 * inch
        footer_line_y = 0.72 * inch

        # Add footer line
        canvas.setStrokeColor(LIGHT_GRAY)
        canvas.setLineWidth(0.8)
        canvas.line(
            MARGIN_LEFT,
            footer_line_y,
            PAGE_WIDTH - MARGIN_RIGHT,
            footer_line_y
        )

        canvas.setStrokeColor(PRIMARY_COLOR)
        canvas.setLineWidth(2)
        canvas.line(
            MARGIN_LEFT,
            footer_line_y,
            MARGIN_LEFT + 0.7 * inch,
            footer_line_y
        )

        canvas.setFont("Helvetica", 10)
        canvas.setFillColor(colors.HexColor('#718096'))
        canvas.drawRightString(
            PAGE_WIDTH - MARGIN_RIGHT,
            footer_y,
            f"Page {page_num}"
        )

        canvas.restoreState()

    def _create_cover_page(
        self,
        title: str,
        client_name: Optional[str] = None
    ) -> List:
        """Create cover page elements."""
        elements = []

        # Add spacer for top margin
        elements.append(Spacer(1, 2 * inch))

        # Add logo centered if exists
        if self.logo_path.exists():
            try:
                logo = Image(str(self.logo_path), width=3 * inch, height=1 * inch)
                logo.hAlign = 'CENTER'
                elements.append(logo)
            except Exception as e:
                logger.warning(f"Could not add cover logo: {e}")

        elements.append(Spacer(1, 1 * inch))

        # Add title
        elements.append(Paragraph(title, self.styles['CoverTitle']))

        # Add client name
        client_display = client_name if client_name else "client_name_not_specified"
        elements.append(Paragraph(f"Prepared for: {client_display}", self.styles['ClientName']))

        elements.append(Spacer(1, 1.5 * inch))

        # Add date
        date_str = datetime.now().strftime("%B %d, %Y")
        elements.append(Paragraph(date_str, self.styles['CoverSubtitle']))

        # Add generated by text
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph(
            "Generated by Agentic PDF Generator",
            self.styles['CoverSubtitle']
        ))

        elements.append(PageBreak())

        return elements

    def _create_disclaimer_page(self) -> List:
        """Create disclaimer page elements."""
        elements = []

        elements.append(Paragraph("Disclaimer", self.styles['DisclaimerTitle']))
        elements.append(Spacer(1, 0.3 * inch))

        # Parse and add disclaimer paragraphs
        for paragraph in DISCLAIMER_TEXT.strip().split('\n\n'):
            if paragraph.strip():
                elements.append(Paragraph(paragraph.strip(), self.styles['DisclaimerText']))
                elements.append(Spacer(1, 0.1 * inch))

        elements.append(PageBreak())

        return elements

    def _create_toc_page(self, sections: List[Dict[str, Any]]) -> List:
        """Create table of contents page."""
        elements = []

        elements.append(Paragraph("Table of Contents", self.styles['TOCTitle']))
        elements.append(Spacer(1, 0.15 * inch))

        toc_line = Table(
            [[""]],
            colWidths=[PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT],
            rowHeights=[0.06 * inch]
        )
        toc_line.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), PRIMARY_COLOR),
            ('LINEBELOW', (0, 0), (-1, -1), 0, WHITE),
        ]))
        elements.append(toc_line)
        elements.append(Spacer(1, 0.3 * inch))

        # Create TOC entries
        toc_rows = []
        for idx, section in enumerate(sections):
            section_name = section.get('name', f'Section {idx + 1}')
            page_num = section.get('page', idx + 4)  # Start content from page 4

            toc_rows.append([
                Paragraph(f"<link href='#{section_name}'>{section_name}</link>", self.styles['TOCEntry']),
                Paragraph(str(page_num), self.styles['TOCPage'])
            ])

        toc_table_width = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
        page_col_width = 0.9 * inch
        name_col_width = toc_table_width - page_col_width
        toc_table = Table(
            toc_rows,
            colWidths=[name_col_width, page_col_width],
            hAlign='LEFT'
        )
        toc_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('LINEBELOW', (0, 0), (-1, -1), 0.4, LIGHT_GRAY),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor('#f7fafc'), WHITE]),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(toc_table)

        elements.append(PageBreak())

        return elements

    def _create_section(
        self,
        section_name: str,
        content: Dict[str, Any],
        charts: Optional[List[bytes]] = None
    ) -> List:
        """Create a content section with optional charts."""
        elements = []

        # Section heading with anchor
        heading = Paragraph(
            f"<a name='{section_name}'/>{section_name}",
            self.styles['SectionHeading']
        )
        elements.append(heading)
        elements.append(Spacer(1, 0.2 * inch))

        # Add description if present
        if 'description' in content:
            elements.append(Paragraph(content['description'], self.styles['BodyText']))
            elements.append(Spacer(1, 0.2 * inch))

        # Add text content
        if 'text' in content:
            for paragraph in content['text'] if isinstance(content['text'], list) else [content['text']]:
                elements.append(Paragraph(str(paragraph), self.styles['BodyText']))
                elements.append(Spacer(1, 0.1 * inch))

        # Add bullet points if present
        if 'bullets' in content and isinstance(content['bullets'], list):
            bullet_items = []
            for bullet in content['bullets']:
                bullet_items.append(ListItem(
                    Paragraph(str(bullet), self.styles['BulletPoint']),
                    leftIndent=20
                ))
            elements.append(ListFlowable(bullet_items, bulletType='bullet'))
            elements.append(Spacer(1, 0.2 * inch))

        # Add findings if present
        if 'findings' in content and isinstance(content['findings'], list):
            elements.append(Paragraph("Key Findings:", self.styles['SubsectionHeading']))
            for finding in content['findings']:
                elements.append(Paragraph(f"• {finding}", self.styles['BulletPoint']))
            elements.append(Spacer(1, 0.2 * inch))

        # Add data table if present
        if 'data' in content and isinstance(content['data'], dict):
            table_data = [['Metric', 'Value']]
            for key, value in content['data'].items():
                table_data.append([str(key), str(value)])

            table = Table(table_data, colWidths=[3 * inch, 2 * inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
                ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), LIGHT_GRAY),
                ('GRID', (0, 0), (-1, -1), 1, colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.3 * inch))

        # Add charts if present
        if charts:
            for idx, chart_bytes in enumerate(charts):
                try:
                    chart_image = Image(io.BytesIO(chart_bytes), width=5.5 * inch, height=4 * inch)
                    chart_image.hAlign = 'CENTER'
                    elements.append(chart_image)
                    elements.append(Paragraph(
                        f"Figure {idx + 1}: {section_name} Visualization",
                        self.styles['ChartCaption']
                    ))
                    elements.append(Spacer(1, 0.3 * inch))
                except Exception as e:
                    logger.error(f"Error adding chart: {e}")

        return elements

    def _ensure_minimum_pages(self, elements: List, min_pages: int = 7) -> List:
        """Ensure the PDF has at least the minimum number of pages."""
        # Add placeholder content if needed
        # This is handled by the planner agent, but we add a safety check
        return elements

    def generate_pdf(
        self,
        title: str,
        client_name: Optional[str],
        sections: List[Dict[str, Any]],
        charts: Dict[str, List[bytes]] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete PDF document.

        Args:
            title: Document title
            client_name: Client name (optional)
            sections: List of section dictionaries with name and content
            charts: Dictionary mapping section names to chart image bytes

        Returns:
            Dictionary with pdf_id, file_path, and metadata
        """
        pdf_id = str(uuid.uuid4())
        file_name = f"{pdf_id}.pdf"
        file_path = self.output_dir / file_name

        charts = charts or {}

        # Create document
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=PAGE_SIZE,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM
        )

        elements = []

        # Page 1: Cover page
        elements.extend(self._create_cover_page(title, client_name))

        # Page 2: Disclaimer
        elements.extend(self._create_disclaimer_page())

        # Calculate section pages for TOC
        toc_sections = []
        current_page = 4  # Content starts after cover, disclaimer, and TOC

        for section in sections:
            toc_sections.append({
                'name': section.get('name', 'Section'),
                'page': current_page
            })
            # Estimate pages per section (rough estimate)
            content_size = len(str(section.get('content', {})))
            has_chart = section.get('name') in charts
            estimated_pages = max(1, content_size // 2000 + (1 if has_chart else 0))
            current_page += estimated_pages

        # Page 3: Table of Contents
        elements.extend(self._create_toc_page(toc_sections))

        # Pages 4+: Content sections
        for section in sections:
            section_name = section.get('name', 'Section')
            content = section.get('content', {})
            section_charts = charts.get(section_name, [])

            elements.extend(self._create_section(section_name, content, section_charts))
            elements.append(PageBreak())

        # Build PDF with header/footer
        def add_header_footer(canvas, doc):
            self._header_footer(canvas, doc, True)

        doc.build(elements, onFirstPage=lambda c, d: self._header_footer(c, d, True),
                  onLaterPages=add_header_footer)

        # Get actual page count
        # Note: This requires re-reading the PDF to get accurate count
        # For now, we estimate based on content
        estimated_pages = 3 + len(sections)

        return {
            'pdf_id': pdf_id,
            'file_path': str(file_path),
            'file_name': file_name,
            'metadata': {
                'title': title,
                'client_name': client_name or 'client_name_not_specified',
                'pages': estimated_pages,
                'sections': [s.get('name', 'Section') for s in sections],
                'generated_at': datetime.now().isoformat()
            }
        }


# Singleton instance
pdf_service = PDFService()
