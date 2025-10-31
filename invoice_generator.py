from database import add_invoice
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


def remove_white_background(logo_path, output_path="temp_logo_transparent.png"):
    """Remove white background from logo"""
    try:
        img = Image.open(logo_path)
        img = img.convert('RGBA')
        datas = img.getdata()
        newData = []

        for item in datas:
            r, g, b = item[0], item[1], item[2]
            if r > 230 and g > 230 and b > 230:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)

        img.putdata(newData)
        img.save(output_path, "PNG")
        return True
    except Exception as e:
        print(f"Error processing logo: {e}")
        return False


def create_invoice_pdf(data, output_path, logo_path="image.jpg"):
    """Create PDF invoice"""
    LOGO_BOTTOM_WIDTH = 220
    LOGO_BOTTOM_HEIGHT = 195

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    cream = HexColor('#F5F2E8')
    dark_brown = HexColor('#4A1E1E')
    burgundy = HexColor('#5C2E2E')

    c.setFillColor(cream)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    temp_logo = "temp_logo_transparent.png"
    logo_processed = remove_white_background(logo_path, temp_logo)

    # Company details
    c.setFillColor(dark_brown)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 40, "VELVET LAVENDER")
    c.setFont("Helvetica", 9)
    c.drawString(40, height - 55, "Oriadon 12, Strovolos, 2037")
    c.drawString(40, height - 68, "Nicosia, Cyprus")

    # Title
    c.setFont("Helvetica-Bold", 36)
    title = "I N V O I C E"
    title_width = c.stringWidth(title, "Helvetica-Bold", 36)
    c.drawString((width - title_width) / 2, height - 140, title)

    # Client info
    left_x, right_x, y_start = 40, 380, height - 200
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, y_start, "Issued to:")
    c.setFont("Helvetica", 10)
    y = y_start - 15
    c.drawString(left_x, y, data['client_name'])
    y -= 13
    if data.get('client_address_2'):
        c.drawString(left_x, y, data['client_address_2'])
        y -= 13
    if data.get('client_address_3'):
        c.drawString(left_x, y, data['client_address_3'])
        y -= 13
    if data.get('client_address_4'):
        c.drawString(left_x, y, data['client_address_4'])

    # Invoice details
    c.setFont("Helvetica-Bold", 10)
    c.drawString(right_x, y_start, "Issued by:")
    c.setFont("Helvetica", 9)
    y = y_start - 15
    c.drawString(right_x, y, "Velvet Lavender")
    y -= 13
    c.drawString(right_x, y, f"VAT Number: {data['vat_number']}")
    y -= 13
    c.drawString(right_x, y, f"Invoice No: {data['invoice_number']}")
    y -= 13
    c.drawString(right_x, y, f"Date Issued: {data['date_issued']}")

    # Table
    table_y = height - 340
    c.setFillColor(burgundy)
    c.rect(40, table_y, width - 80, 30, fill=1, stroke=0)
    c.setFillColor(cream)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, table_y + 10, "Description")
    c.drawCentredString(330, table_y + 10, "Quantity")
    c.drawCentredString(420, table_y + 10, "Month")
    c.drawRightString(width - 50, table_y + 10, "Total")

    c.setFillColor(dark_brown)
    c.setFont("Helvetica", 10)
    row_y = table_y - 22
    c.drawString(50, row_y, data['description'])
    c.drawCentredString(330, row_y, str(data['quantity']))
    c.drawCentredString(420, row_y, data['month'])
    c.drawRightString(width - 50, row_y, str(data['total']))

    c.setStrokeColor(dark_brown)
    c.setLineWidth(1)
    c.line(40, table_y - 42, width - 40, table_y - 42)

    # Footer
    footer_y = 280
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, footer_y, "PAYMENT INFO")
    c.setFont("Helvetica", 8)
    payment_y = footer_y - 15
    c.drawString(40, payment_y, "Alpha Bank Cy Ltd.")
    payment_y -= 12
    c.drawString(40, payment_y, "Account Name: Anastasia Mouskou Trading As Velvet Lavender")
    payment_y -= 12
    c.drawString(40, payment_y, "IBAN: CY69009002020002021001571029")
    payment_y -= 12
    c.drawString(40, payment_y, "Bank BIC: ABKLCY2N")
    payment_y -= 15
    c.drawString(40, payment_y, "Revolut: @anastasiamouskou")

    # Totals
    totals_x, totals_y = width - 50, footer_y
    c.setFont("Helvetica", 11)
    c.drawRightString(totals_x, totals_y, f"Subtotal: €{data['subtotal']}")
    totals_y -= 20
    c.drawRightString(totals_x, totals_y, f"Tax (19%): €{data['tax']}")
    totals_y -= 10
    c.setStrokeColor(dark_brown)
    c.line(totals_x - 120, totals_y, totals_x, totals_y)
    totals_y -= 15
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(totals_x, totals_y, f"TOTAL: €{data['total_amount']}")

    # Logo
    try:
        if logo_processed and os.path.exists(temp_logo):
            logo_bottom = ImageReader(temp_logo)
        else:
            logo_bottom = ImageReader(logo_path)
        c.drawImage(logo_bottom, (width - LOGO_BOTTOM_WIDTH) / 2, 20,
                    width=LOGO_BOTTOM_WIDTH, height=LOGO_BOTTOM_HEIGHT,
                    preserveAspectRatio=True, mask='auto')
    except:
        pass

    c.save()
    if os.path.exists(temp_logo):
        try:
            os.remove(temp_logo)
        except:
            pass


def create_invoice_modern(data, output_path, logo_path="image.jpg"):
    """Ultra Modern Template - Vibrant Gradients & Clean Lines"""
    LOGO_WIDTH = 140
    LOGO_HEIGHT = 120

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    # Modern vibrant colors
    white = HexColor('#FFFFFF')
    off_white = HexColor('#FAFAFA')
    purple = HexColor('#8B5CF6')
    pink = HexColor('#EC4899')
    cyan = HexColor('#06B6D4')
    dark = HexColor('#1F2937')
    gray = HexColor('#6B7280')
    light_gray = HexColor('#F3F4F6')

    # White background
    c.setFillColor(white)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Gradient effect simulation (top accent)
    for i in range(80):
        alpha = 1 - (i / 80)
        c.setFillColorRGB(0.54, 0.36, 0.96, alpha=alpha * 0.1)
        c.rect(0, height - i, width, 1, fill=1, stroke=0)

    # Top left brand section with colored accent
    c.setFillColor(purple)
    c.rect(35, height - 90, 6, 60, fill=1, stroke=0)  # Vertical accent bar

    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(50, height - 50, "VELVET LAVENDER")

    c.setFillColor(gray)
    c.setFont("Helvetica", 9)
    c.drawString(50, height - 68, "Oriadon 12, Strovolos 2037")
    c.drawString(50, height - 82, "Nicosia, Cyprus")

    # Modern "INVOICE" with gradient-like effect
    c.setFillColor(purple)
    c.setFont("Helvetica-Bold", 48)
    c.drawRightString(width - 40, height - 60, "INVOICE")

    # Invoice details in modern card style
    card_x = width - 240
    card_y = height - 180

    # Card shadow effect
    c.setFillColorRGB(0, 0, 0, alpha=0.05)
    c.roundRect(card_x + 3, card_y - 3, 220, 95, 12, fill=1, stroke=0)

    # Main card
    c.setFillColor(light_gray)
    c.roundRect(card_x, card_y, 220, 95, 12, fill=1, stroke=0)

    # Colored top strip on card
    c.setFillColor(purple)
    c.roundRect(card_x, card_y + 85, 220, 10, 12, fill=1, stroke=0)

    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(card_x + 15, card_y + 65, "INVOICE NUMBER")
    c.drawString(card_x + 15, card_y + 45, "DATE ISSUED")
    c.drawString(card_x + 15, card_y + 25, "VAT NUMBER")
    c.drawString(card_x + 15, card_y + 5, "PERIOD")

    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(card_x + 205, card_y + 65, data['invoice_number'])
    c.drawRightString(card_x + 205, card_y + 45, data['date_issued'])
    c.setFont("Helvetica", 9)
    c.drawRightString(card_x + 205, card_y + 25, data['vat_number'])
    c.drawRightString(card_x + 205, card_y + 5, data['month'])

    # Client info with modern style
    client_y = height - 160
    c.setFillColor(purple)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, client_y, "BILLED TO")

    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, client_y - 22, data['client_name'])

    c.setFillColor(gray)
    c.setFont("Helvetica", 9)
    client_y -= 38
    if data.get('client_address_2'):
        c.drawString(40, client_y, data['client_address_2'])
        client_y -= 14
    if data.get('client_address_3'):
        c.drawString(40, client_y, data['client_address_3'])

    # Modern table with rounded corners
    table_y = height - 380

    # Table header with gradient simulation
    c.setFillColor(purple)
    c.roundRect(35, table_y, width - 70, 35, 8, fill=1, stroke=0)

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, table_y + 13, "DESCRIPTION")
    c.drawCentredString(width - 200, table_y + 13, "QTY")
    c.drawCentredString(width - 130, table_y + 13, "MONTH")
    c.drawRightString(width - 50, table_y + 13, "AMOUNT")

    # Table row with subtle background
    c.setFillColor(off_white)
    c.rect(35, table_y - 35, width - 70, 30, fill=1, stroke=0)

    c.setFillColor(dark)
    c.setFont("Helvetica", 10)
    c.drawString(50, table_y - 22, data['description'])
    c.drawCentredString(width - 200, table_y - 22, str(data['quantity']))
    c.drawCentredString(width - 130, table_y - 22, data['month'])
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - 50, table_y - 22, f"€{data['total']}")

    # Totals section with modern alignment
    totals_y = table_y - 100
    totals_x = width - 50

    c.setFillColor(gray)
    c.setFont("Helvetica", 10)
    c.drawRightString(totals_x - 100, totals_y, "Subtotal")
    c.drawRightString(totals_x, totals_y, f"€{data['subtotal']}")

    totals_y -= 20
    c.drawRightString(totals_x - 100, totals_y, "Tax (19%)")
    c.drawRightString(totals_x, totals_y, f"€{data['tax']}")

    # Modern divider line
    totals_y -= 8
    c.setStrokeColor(light_gray)
    c.setLineWidth(2)
    c.line(totals_x - 120, totals_y, totals_x, totals_y)

    # Total with colored accent
    totals_y -= 20
    c.setFillColor(purple)
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(totals_x - 100, totals_y, "TOTAL")
    c.drawRightString(totals_x, totals_y, f"€{data['total_amount']}")

    # Payment info in modern card
    payment_y = 180
    c.setFillColor(light_gray)
    c.roundRect(35, payment_y - 45, width - 70, 50, 8, fill=1, stroke=0)

    c.setFillColor(purple)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(45, payment_y - 10, "PAYMENT INFORMATION")

    c.setFillColor(dark)
    c.setFont("Helvetica", 7)
    c.drawString(45, payment_y - 25, "Bank: Alpha Bank Cyprus  •  IBAN: CY69009002020002021001571029  •  BIC: ABKLCY2N")
    c.drawString(45, payment_y - 38, "Revolut: @anastasiamouskou")

    # Logo at bottom
    try:
        temp_logo = "temp_logo_transparent.png"
        logo_processed = remove_white_background(logo_path, temp_logo)
        if logo_processed and os.path.exists(temp_logo):
            logo_img = ImageReader(temp_logo)
        else:
            logo_img = ImageReader(logo_path)
        c.drawImage(logo_img, (width - LOGO_WIDTH) / 2, 25,
                    width=LOGO_WIDTH, height=LOGO_HEIGHT,
                    preserveAspectRatio=True, mask='auto')
        if os.path.exists(temp_logo):
            os.remove(temp_logo)
    except:
        pass

    c.save()


def create_invoice_dark(data, output_path, logo_path="image.jpg"):
    """Minimalist Futuristic Template - Ultra Clean & Spacious"""
    LOGO_WIDTH = 130
    LOGO_HEIGHT = 110

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    # Minimalist color palette
    white = HexColor('#FFFFFF')
    near_white = HexColor('#FEFEFE')
    accent = HexColor('#0EA5E9')  # Bright cyan
    dark = HexColor('#0F172A')
    medium = HexColor('#334155')
    light = HexColor('#E2E8F0')
    ultra_light = HexColor('#F8FAFC')

    # Clean white background
    c.setFillColor(white)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Minimal accent line at very top
    c.setFillColor(accent)
    c.rect(0, height - 3, width, 3, fill=1, stroke=0)

    # Ultra minimalist header
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(40, height - 55, "VELVET LAVENDER")

    c.setFillColor(medium)
    c.setFont("Helvetica", 8)
    c.drawString(40, height - 72, "ORIADON 12, STROVOLOS 2037  •  NICOSIA, CYPRUS")

    # Minimalist "INVOICE" text
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, height - 100, "INVOICE")

    # Invoice number right aligned, super clean
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 32)
    c.drawRightString(width - 40, height - 100, data['invoice_number'])

    # Thin divider line
    c.setStrokeColor(light)
    c.setLineWidth(1)
    c.line(40, height - 120, width - 40, height - 120)

    # Two column layout - very spacious
    left_x = 40
    right_x = width / 2 + 20
    detail_y = height - 160

    # Left column - Client
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(left_x, detail_y, "BILL TO")

    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(left_x, detail_y - 25, data['client_name'])

    c.setFillColor(medium)
    c.setFont("Helvetica", 9)
    detail_y -= 42
    if data.get('client_address_2'):
        c.drawString(left_x, detail_y, data['client_address_2'])
        detail_y -= 16
    if data.get('client_address_3'):
        c.drawString(left_x, detail_y, data['client_address_3'])

    # Right column - Details
    detail_y = height - 160
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(right_x, detail_y, "INVOICE DETAILS")

    detail_y -= 22
    c.setFillColor(medium)
    c.setFont("Helvetica", 8)
    c.drawString(right_x, detail_y, "Date")
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(width - 40, detail_y, data['date_issued'])

    detail_y -= 18
    c.setFillColor(medium)
    c.setFont("Helvetica", 8)
    c.drawString(right_x, detail_y, "Month")
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(width - 40, detail_y, data['month'])

    detail_y -= 18
    c.setFillColor(medium)
    c.setFont("Helvetica", 8)
    c.drawString(right_x, detail_y, "VAT")
    c.setFillColor(dark)
    c.setFont("Helvetica", 9)
    c.drawRightString(width - 40, detail_y, data['vat_number'])

    # Ultra minimalist table
    table_y = height - 350

    # Thin header line
    c.setStrokeColor(light)
    c.setLineWidth(1)
    c.line(40, table_y + 30, width - 40, table_y + 30)

    # Table headers - uppercase, spaced out
    c.setFillColor(medium)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(50, table_y + 15, "DESCRIPTION")
    c.drawRightString(width - 200, table_y + 15, "QTY")
    c.drawRightString(width - 130, table_y + 15, "MONTH")
    c.drawRightString(width - 50, table_y + 15, "AMOUNT")

    # Table content - clean and spacious
    c.setFillColor(dark)
    c.setFont("Helvetica", 11)
    c.drawString(50, table_y - 15, data['description'])
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 200, table_y - 15, str(data['quantity']))
    c.drawRightString(width - 130, table_y - 15, data['month'])
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(width - 50, table_y - 15, f"€{data['total']}")

    # Bottom line
    c.setStrokeColor(light)
    c.line(40, table_y - 35, width - 40, table_y - 35)

    # Totals - right aligned, lots of space
    totals_y = table_y - 80
    totals_x = width - 50

    c.setFillColor(medium)
    c.setFont("Helvetica", 9)
    c.drawRightString(totals_x - 100, totals_y, "Subtotal")
    c.setFillColor(dark)
    c.setFont("Helvetica", 10)
    c.drawRightString(totals_x, totals_y, f"€{data['subtotal']}")

    totals_y -= 20
    c.setFillColor(medium)
    c.setFont("Helvetica", 9)
    c.drawRightString(totals_x - 100, totals_y, "Tax 19%")
    c.setFillColor(dark)
    c.setFont("Helvetica", 10)
    c.drawRightString(totals_x, totals_y, f"€{data['tax']}")

    # Thin divider
    totals_y -= 8
    c.setStrokeColor(light)
    c.setLineWidth(1)
    c.line(totals_x - 120, totals_y, totals_x, totals_y)

    # TOTAL - emphasized with accent color
    totals_y -= 22
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(totals_x - 100, totals_y, "TOTAL")
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(totals_x, totals_y, f"€{data['total_amount']}")

    # Payment info - minimal footer
    payment_y = 140
    c.setStrokeColor(light)
    c.setLineWidth(0.5)
    c.line(40, payment_y + 20, width - 40, payment_y + 20)

    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(40, payment_y, "PAYMENT")

    c.setFillColor(medium)
    c.setFont("Helvetica", 7)
    c.drawString(40, payment_y - 15, "Alpha Bank Cyprus")
    c.drawString(40, payment_y - 27, "IBAN: CY69009002020002021001571029")

    c.drawString(width - 230, payment_y - 15, "BIC: ABKLCY2N")
    c.drawString(width - 230, payment_y - 27, "Revolut: @anastasiamouskou")

    # Minimal logo placement
    try:
        temp_logo = "temp_logo_transparent.png"
        logo_processed = remove_white_background(logo_path, temp_logo)
        if logo_processed and os.path.exists(temp_logo):
            logo_img = ImageReader(temp_logo)
        else:
            logo_img = ImageReader(logo_path)
        c.drawImage(logo_img, (width - LOGO_WIDTH) / 2, 20,
                    width=LOGO_WIDTH, height=LOGO_HEIGHT,
                    preserveAspectRatio=True, mask='auto')
        if os.path.exists(temp_logo):
            os.remove(temp_logo)
    except:
        pass

    c.save()


def send_invoices_email(pdf_files, recipient_email, invoice_month, email_config):
    """Send invoices via email"""
    msg = MIMEMultipart()
    msg['From'] = email_config['sender_email']
    msg['To'] = recipient_email
    msg['Subject'] = f"Velvet Lavender Invoices - {invoice_month}"

    body = f"""
Hello,

Please find attached your invoices for {invoice_month}.

Total invoices: {len(pdf_files)}

Best regards,
Velvet Lavender
    """
    msg.attach(MIMEText(body, 'plain'))

    for pdf_file in pdf_files:
        with open(pdf_file, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(pdf_file)}')
            msg.attach(part)

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(email_config['sender_email'], email_config['sender_password'])
    server.sendmail(email_config['sender_email'], recipient_email, msg.as_string())
    server.quit()


def process_invoices(excel_file, output_folder, logo_path, email_config=None, template='classic'):
    """Main processing function with template selection"""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    df = pd.read_excel(excel_file)
    today = datetime.now()
    invoice_date = today.strftime('%d %B, %Y')
    current_month = today.strftime('%B')
    current_year = today.year

    generated_pdfs = []

    # Select template function
    template_functions = {
        'classic': create_invoice_pdf,
        'modern': create_invoice_modern,
        'dark': create_invoice_dark
    }

    create_pdf = template_functions.get(template, create_invoice_pdf)

    for index, row in df.iterrows():
        current_invoice = row['Invoice No:']
        invoice_num = int(str(current_invoice).replace('#', ''))
        new_invoice_num = invoice_num + 1

        df.at[index, 'Invoice No:'] = f'#{new_invoice_num}'
        df.at[index, 'Date Issued:'] = invoice_date
        df.at[index, 'Month'] = current_month

        client_lines = row['Issued to'].split('\n')

        invoice_data = {
            'client_name': client_lines[0] if len(client_lines) > 0 else "",
            'client_address_2': client_lines[1] if len(client_lines) > 1 else "",
            'client_address_3': client_lines[2] if len(client_lines) > 2 else "",
            'client_address_4': client_lines[3] if len(client_lines) > 3 else "",
            'vat_number': str(row['VAT Number']),
            'invoice_number': f'#{new_invoice_num}',
            'date_issued': invoice_date,
            'description': str(row['Description']),
            'quantity': str(row['Quantity']),
            'month': current_month,
            'total': str(row['Total']),
            'subtotal': str(row['Subtotal']),
            'tax': str(row['Tax(19%)']),
            'total_amount': str(row['Total.1'])
        }

        client_name_clean = invoice_data['client_name'].replace(' ', '_').replace('.', '').replace(',', '')
        pdf_filename = f"{output_folder}/Invoice_{client_name_clean}_{current_month}_{current_year}.pdf"

        create_pdf(invoice_data, pdf_filename, logo_path)
        generated_pdfs.append(pdf_filename)

        # Save to database
        invoice_data['pdf_filename'] = pdf_filename
        invoice_data['template'] = template
        add_invoice(invoice_data)

    df.to_excel(excel_file, index=False)
    return generated_pdfs