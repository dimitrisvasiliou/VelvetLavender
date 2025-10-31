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

# ====================================================
# 📧 EMAIL CONFIGURATION - CHANGE THESE!
# ====================================================
SENDER_EMAIL = "dimitris.123666@gmail.com"  # Your Gmail
SENDER_PASSWORD = "nsqmhbiptydyzxel"  # Gmail App Password (see instructions below)
RECIPIENT_EMAIL = "miltiadouy@gmail.com"  # Who receives the invoices "mouskoua@outlook.com"


# ====================================================


def remove_white_background(logo_path, output_path="temp_logo_transparent.png"):
    """Remove white background from logo, keep burgundy VL design"""
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
    """Create a beautiful modern invoice from scratch"""

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

    c.setFillColor(dark_brown)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 40, "VELVET LAVENDER")

    c.setFont("Helvetica", 9)
    c.drawString(40, height - 55, "Oriadon 12, Strovolos, 2037")
    c.drawString(40, height - 68, "Nicosia, Cyprus")

    c.setFont("Helvetica-Bold", 36)
    c.setFillColor(dark_brown)
    title = "I N V O I C E"
    title_width = c.stringWidth(title, "Helvetica-Bold", 36)
    c.drawString((width - title_width) / 2, height - 140, title)

    left_x = 40
    right_x = 380
    y_start = height - 200

    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, y_start, "Issued to:")

    c.setFont("Helvetica", 10)
    y = y_start - 15
    c.drawString(left_x, y, data['client_name'])
    y -= 13
    if data['client_address_2']:
        c.drawString(left_x, y, data['client_address_2'])
        y -= 13
    if data['client_address_3']:
        c.drawString(left_x, y, data['client_address_3'])
        y -= 13
    if data['client_address_4']:
        c.drawString(left_x, y, data['client_address_4'])

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

    totals_x = width - 50
    totals_y = footer_y

    c.setFont("Helvetica", 11)
    c.drawRightString(totals_x, totals_y, f"Subtotal: €{data['subtotal']}")

    totals_y -= 20
    c.drawRightString(totals_x, totals_y, f"Tax (19%): €{data['tax']}")

    totals_y -= 10
    c.setStrokeColor(dark_brown)
    c.setLineWidth(1)
    c.line(totals_x - 120, totals_y, totals_x, totals_y)

    totals_y -= 15
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(totals_x, totals_y, f"TOTAL: €{data['total_amount']}")

    try:
        if logo_processed and os.path.exists(temp_logo):
            logo_bottom = ImageReader(temp_logo)
        else:
            logo_bottom = ImageReader(logo_path)

        logo_x_bottom = (width - LOGO_BOTTOM_WIDTH) / 2
        logo_y_bottom = 20

        c.drawImage(logo_bottom, logo_x_bottom, logo_y_bottom,
                    width=LOGO_BOTTOM_WIDTH, height=LOGO_BOTTOM_HEIGHT,
                    preserveAspectRatio=True, mask='auto')

    except Exception as e:
        print(f"Warning: Could not load bottom logo - {e}")

    c.save()

    if os.path.exists(temp_logo):
        try:
            os.remove(temp_logo)
        except:
            pass


def send_invoices_email(pdf_files, recipient_email, invoice_month):
    """Send all generated invoices via email"""

    print(f"\n📧 Preparing to send {len(pdf_files)} invoice(s) via email...")

    # Create message
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = f"Velvet Lavender Invoices - {invoice_month}"

    # Email body
    body = f"""
Hello,

Please find attached your invoices for {invoice_month}.

Total invoices: {len(pdf_files)}

Best regards,
Velvet Lavender
Oriadon 12, Strovolos, 2037
Nicosia, Cyprus
    """

    msg.attach(MIMEText(body, 'plain'))

    # Attach all PDF files
    for pdf_file in pdf_files:
        try:
            with open(pdf_file, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)

                filename = os.path.basename(pdf_file)
                part.add_header('Content-Disposition', f'attachment; filename= {filename}')
                msg.attach(part)
                print(f"  ✓ Attached: {filename}")
        except Exception as e:
            print(f"  ✗ Failed to attach {pdf_file}: {e}")

    # Send email via Gmail
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, recipient_email, text)
        server.quit()

        print(f"\n✅ Email sent successfully to {recipient_email}!")
        return True

    except Exception as e:
        print(f"\n❌ Failed to send email: {e}")
        return False


def process_invoices(excel_file, output_folder='generated_invoices', logo_path='image.jpg', send_email=True):
    """Process all invoices from Excel"""

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    df = pd.read_excel(excel_file)

    today = datetime.now()
    invoice_date = today.strftime('%d %B, %Y')
    current_month = today.strftime('%B')
    current_year = today.year

    print(f"📅 Today's date: {invoice_date}")
    print(f"📅 Current month: {current_month}")
    print(f"Processing {len(df)} invoice(s)...\n")

    generated_pdfs = []  # Track all generated PDFs

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

        try:
            create_invoice_pdf(invoice_data, pdf_filename, logo_path)
            print(f"✓ Generated: {pdf_filename}")
            generated_pdfs.append(pdf_filename)  # Add to list
        except Exception as e:
            print(f"✗ Failed: {pdf_filename}")
            print(f"   Error: {e}")

    df.to_excel(excel_file, index=False)
    print(f"\n✅ Updated SAME Excel file: {excel_file}")
    print(f"✅ Total invoices generated: {len(generated_pdfs)}")
    print(f"📅 All dates updated to: {invoice_date}")

    # Send email with all PDFs
    if send_email and generated_pdfs:
        send_invoices_email(generated_pdfs, RECIPIENT_EMAIL, f"{current_month} {current_year}")


if __name__ == "__main__":
    excel_file = "Anainvoices.xlsx"
    logo_path = "image.jpg"

    # Set send_email=True to send emails, False to skip
    process_invoices(excel_file, logo_path=logo_path, send_email=True)
