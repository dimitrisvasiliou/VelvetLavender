from flask import Flask, render_template, request, redirect, flash, send_file, jsonify, session, url_for
import os
import json
from datetime import datetime
from invoice_generator import process_invoices, send_invoices_email
import zipfile
from functools import wraps
from werkzeug.utils import secure_filename
import shutil
from database import (
    get_all_invoices,
    get_invoice_stats,
    update_invoice_status,
    delete_invoice
)
from flask import send_from_directory

app = Flask(__name__)
app.secret_key = 'velvet-lavender-secret-key-2025-secure'

# Configuration
EXCEL_FILE = 'Anainvoices.xlsx'
LOGO_PATH = 'image.jpg'
OUTPUT_FOLDER = 'generated_invoices'
EMAIL_CONFIG_FILE = 'email_config.json'  # Store email config persistently

# ====================================================
# 🔐 LOGIN PASSWORD - CHANGE THIS IF NEEDED 
# ====================================================
LOGIN_PASSWORD = 'anamoux'


# ====================================================

def load_email_config():
    """Load email configuration from file"""
    if os.path.exists(EMAIL_CONFIG_FILE):
        try:
            with open(EMAIL_CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        'sender_email': '',
        'sender_password': '',
        'recipient_email': '',
        'configured': False
    }


def save_email_config(config):
    """Save email configuration to file"""
    try:
        with open(EMAIL_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


# Load email config on startup
email_config = load_email_config()


def login_required(f):
    """Decorator to protect routes - require login"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('🔒 Please login to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


# Add this with other configurations (after OUTPUT_FOLDER)
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if session.get('logged_in'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        password = request.form.get('password')

        if password == LOGIN_PASSWORD:
            session['logged_in'] = True
            session['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            flash('✅ Welcome to Velvet Lavender Invoice Generator!', 'success')
            return redirect(url_for('index'))
        else:
            flash('❌ Incorrect password. Please try again.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('👋 You have been logged out successfully', 'success')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """Main page - protected by login"""
    # Reload email config from file
    global email_config
    email_config = load_email_config()

    # Check if Excel file exists
    excel_exists = os.path.exists(EXCEL_FILE)

    # Get current date info
    today = datetime.now()
    current_date = today.strftime('%d %B, %Y')
    current_month = today.strftime('%B')

    # Count existing invoices
    invoice_count = 0
    if excel_exists:
        import pandas as pd
        df = pd.read_excel(EXCEL_FILE)
        invoice_count = len(df)

    # Get just the filename (not the full path)
    excel_filename = os.path.basename(EXCEL_FILE)

    # Get invoice statistics
    stats = get_invoice_stats()

    return render_template('index.html',
                           excel_exists=excel_exists,
                           excel_filename=excel_filename,
                           current_date=current_date,
                           current_month=current_month,
                           invoice_count=invoice_count,
                           email_config=email_config,
                           stats=stats)  # Add this line


@app.route('/configure-email', methods=['POST'])
@login_required
def configure_email():
    """Save email configuration"""
    global email_config

    email_config['sender_email'] = request.form.get('sender_email')
    email_config['sender_password'] = request.form.get('sender_password')
    email_config['recipient_email'] = request.form.get('recipient_email')
    email_config['configured'] = True

    # Save to file
    if save_email_config(email_config):
        flash('✅ Email configuration saved and stored!', 'success')
    else:
        flash('⚠️ Email saved but could not persist to disk', 'error')

    return redirect(url_for('index'))


@app.route('/reset-email', methods=['POST'])
@login_required
def reset_email():
    """Reset email configuration"""
    global email_config

    email_config = {
        'sender_email': '',
        'sender_password': '',
        'recipient_email': '',
        'configured': False
    }

    # Delete config file
    if os.path.exists(EMAIL_CONFIG_FILE):
        try:
            os.remove(EMAIL_CONFIG_FILE)
        except:
            pass

    save_email_config(email_config)
    flash('🔄 Email configuration has been reset', 'success')
    return redirect(url_for('index'))


@app.route('/generate', methods=['POST'])
@login_required
def generate():
    """Generate all invoices with template selection"""
    send_email = request.form.get('send_email') == 'on'
    template = request.form.get('template', 'classic')

    try:
        # Clear old PDFs before generating new ones
        if os.path.exists(OUTPUT_FOLDER):
            for file in os.listdir(OUTPUT_FOLDER):
                if file.endswith('.pdf'):
                    try:
                        os.remove(os.path.join(OUTPUT_FOLDER, file))
                    except:
                        pass

        # Generate invoices with selected template
        pdf_files = process_invoices(
            EXCEL_FILE,
            OUTPUT_FOLDER,
            LOGO_PATH,
            email_config if send_email else None,
            template=template
        )

        flash(f'✅ Successfully generated {len(pdf_files)} invoice(s) using {template.title()} template!', 'success')

        if send_email and email_config.get('configured') and email_config['sender_email']:
            today = datetime.now()
            month_year = f"{today.strftime('%B')} {today.year}"
            send_invoices_email(pdf_files, email_config['recipient_email'], month_year, email_config)
            flash(f'📧 Invoices sent to {email_config["recipient_email"]}', 'success')

    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'error')

    return redirect(url_for('index'))


@app.route('/download-all')
@login_required
def download_all():
    """Download all generated PDFs as ZIP"""
    if not os.path.exists(OUTPUT_FOLDER):
        flash('❌ No invoices generated yet!', 'error')
        return redirect(url_for('index'))

    # Create ZIP file
    zip_filename = f"Invoices_{datetime.now().strftime('%Y%m%d')}.zip"
    zip_path = os.path.join(OUTPUT_FOLDER, zip_filename)

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in os.listdir(OUTPUT_FOLDER):
            if file.endswith('.pdf'):
                zipf.write(os.path.join(OUTPUT_FOLDER, file), file)

    return send_file(zip_path, as_attachment=True)


@app.route('/preview/<filename>')
@login_required
def preview(filename):
    """Preview a specific PDF"""
    pdf_path = os.path.join(OUTPUT_FOLDER, filename)
    if os.path.exists(pdf_path):
        return send_file(pdf_path)
    return "PDF not found", 404


@app.route('/preview/<filename>')
@login_required
def preview_pdf(filename):
    """Serve PDF for preview"""
    return send_from_directory(OUTPUT_FOLDER, filename)


@app.route('/upload-excel', methods=['POST'])
@login_required
def upload_excel():
    """Upload and replace Excel file"""
    if 'excel_file' not in request.files:
        flash('❌ No file selected', 'error')
        return redirect(url_for('index'))

    file = request.files['excel_file']

    if file.filename == '':
        flash('❌ No file selected', 'error')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        try:
            # Backup old file if exists
            if os.path.exists(EXCEL_FILE):
                backup_name = f"Ana-s-invoices-backup-{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                shutil.copy(EXCEL_FILE, backup_name)

            # Save new file
            file.save(EXCEL_FILE)
            flash('✅ Excel file uploaded successfully!', 'success')

        except Exception as e:
            flash(f'❌ Error uploading file: {str(e)}', 'error')
    else:
        flash('❌ Invalid file type. Please upload .xlsx or .xls files only', 'error')

    return redirect(url_for('index'))


@app.route('/delete-excel', methods=['POST'])
@login_required
def delete_excel():
    """Delete current Excel file"""
    try:
        if os.path.exists(EXCEL_FILE):
            # Create backup before deleting
            backup_name = f"Ana-s-invoices-deleted-{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            shutil.copy(EXCEL_FILE, backup_name)
            os.remove(EXCEL_FILE)
            flash('✅ Excel file removed. Backup created.', 'success')
        else:
            flash('❌ No Excel file to delete', 'error')
    except Exception as e:
        flash(f'❌ Error deleting file: {str(e)}', 'error')

    return redirect(url_for('index'))


@app.route('/invoices')
@login_required
def invoices():
    """Invoice list page with status management"""
    invoices_list = get_all_invoices()
    stats = get_invoice_stats()

    return render_template('invoices.html',
                           invoices=invoices_list,
                           stats=stats)


@app.route('/update-status', methods=['POST'])
@login_required
def update_status():
    """Update invoice payment status"""
    invoice_number = request.form.get('invoice_number')
    status = request.form.get('status')

    if not invoice_number or not status:
        flash('❌ Invalid request', 'error')
        return redirect(url_for('invoices'))

    if status == 'paid':
        payment_date = datetime.now().strftime('%Y-%m-%d')
        update_invoice_status(invoice_number, status, payment_date)
    else:
        update_invoice_status(invoice_number, status)

    flash(f'✅ Invoice {invoice_number} marked as {status.title()}', 'success')
    return redirect(url_for('invoices'))


@app.route('/delete-invoice', methods=['POST'])
@login_required
def delete_invoice_route():
    """Delete an invoice"""
    invoice_number = request.form.get('invoice_number')

    if not invoice_number:
        flash('❌ Invalid request', 'error')
        return redirect(url_for('invoices'))

    delete_invoice(invoice_number)
    flash(f'✅ Invoice {invoice_number} deleted', 'success')
    return redirect(url_for('invoices'))


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🌸 VELVET LAVENDER INVOICE GENERATOR")
    print("=" * 60)
    print("\n✨ Starting secure web server...")
    print("🔒 Login required - Password: anamoux")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("\n💡 Press Ctrl+C to stop the server\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
