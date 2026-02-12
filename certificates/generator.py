"""Certificate PDF generator using ReportLab."""
import os
from io import BytesIO
from django.conf import settings
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def generate_certificate_pdf(certificate):
    """Generate a professional certificate PDF."""
    buffer = BytesIO()
    width, height = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    # Colors
    dark_blue = HexColor('#0a1628')
    gold = HexColor('#c8a84e')
    light_blue = HexColor('#1a56db')
    white = HexColor('#ffffff')
    gray = HexColor('#6b7280')

    # Background
    c.setFillColor(white)
    c.rect(0, 0, width, height, fill=True)

    # Border
    c.setStrokeColor(dark_blue)
    c.setLineWidth(3)
    c.rect(30, 30, width - 60, height - 60)

    # Inner border
    c.setStrokeColor(gold)
    c.setLineWidth(1.5)
    c.rect(40, 40, width - 80, height - 80)

    # Decorative corners
    corner_size = 30
    for x, y in [(45, 45), (width - 75, 45), (45, height - 75), (width - 75, height - 75)]:
        c.setStrokeColor(gold)
        c.setLineWidth(2)
        c.line(x, y, x + corner_size, y)
        c.line(x, y, x, y + corner_size)

    # Gold line accent
    c.setStrokeColor(gold)
    c.setLineWidth(2)
    y_line = height - 130
    c.line(width / 2 - 120, y_line, width / 2 + 120, y_line)

    # Title
    c.setFillColor(dark_blue)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 100, "MULTITION EDUCATION")

    c.setFillColor(gold)
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 118, "— AI Learning Platform —")

    # Certificate of Completion
    c.setFillColor(dark_blue)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(width / 2, height - 180, "Certificate of Completion")

    # "This is to certify that"
    c.setFillColor(gray)
    c.setFont("Helvetica", 13)
    c.drawCentredString(width / 2, height - 220, "This is to certify that")

    # Student name
    student_name = certificate.student.get_full_name() or certificate.student.username
    c.setFillColor(dark_blue)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2, height - 260, student_name)

    # Underline for name
    name_width = c.stringWidth(student_name, "Helvetica-Bold", 28)
    c.setStrokeColor(gold)
    c.setLineWidth(1)
    c.line(width / 2 - name_width / 2 - 20, height - 268,
           width / 2 + name_width / 2 + 20, height - 268)

    # "has successfully completed"
    c.setFillColor(gray)
    c.setFont("Helvetica", 13)
    c.drawCentredString(width / 2, height - 298, "has successfully completed the course")

    # Course name
    c.setFillColor(light_blue)
    c.setFont("Helvetica-Bold", 20)
    course_title = certificate.course.title
    if len(course_title) > 50:
        course_title = course_title[:47] + "..."
    c.drawCentredString(width / 2, height - 330, course_title)

    # Category and level
    c.setFillColor(gray)
    c.setFont("Helvetica", 11)
    details = f"{certificate.course.get_category_display()} • {certificate.course.get_level_display()} • {certificate.course.duration_hours} Hours"
    c.drawCentredString(width / 2, height - 355, details)

    # Date and ID
    c.setFillColor(gray)
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, 90, f"Issued on {certificate.issued_at.strftime('%B %d, %Y')}")
    cert_id = str(certificate.certificate_id).upper()
    c.drawCentredString(width / 2, 72, f"Certificate ID: {cert_id}")
    c.setFillColor(light_blue)
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 57, f"Verify at: http://localhost:8000/certificates/verify/{certificate.certificate_id}/")

    # Signatures area
    sig_y = 130
    # Left signature - Mentor
    if certificate.approved_by:
        c.setStrokeColor(gray)
        c.line(width / 4 - 70, sig_y, width / 4 + 70, sig_y)
        c.setFillColor(dark_blue)
        c.setFont("Helvetica-Bold", 11)
        mentor_name = certificate.approved_by.get_full_name() or certificate.approved_by.username
        c.drawCentredString(width / 4, sig_y + 10, mentor_name)
        c.setFillColor(gray)
        c.setFont("Helvetica", 9)
        c.drawCentredString(width / 4, sig_y - 15, "Course Mentor")

    # Right signature - Platform
    c.setStrokeColor(gray)
    c.line(3 * width / 4 - 70, sig_y, 3 * width / 4 + 70, sig_y)
    c.setFillColor(dark_blue)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(3 * width / 4, sig_y + 10, "MultiTion Education")
    c.setFillColor(gray)
    c.setFont("Helvetica", 9)
    c.drawCentredString(3 * width / 4, sig_y - 15, "Platform Administrator")

    c.save()
    buffer.seek(0)

    # Save to certificate model
    filename = f"cert_{certificate.certificate_id}.pdf"
    certificate.pdf_file.save(filename, ContentFile(buffer.getvalue()), save=True)

    return certificate
