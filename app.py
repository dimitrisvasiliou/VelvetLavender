from flask import Flask, render_template, request, redirect, flash, send_file, jsonify, session, url_for
import os
import json
from datetime import datetime
from invoice_generator import process_invoices, send_invoices_email
import zipfile
from functools import wraps

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

    return render_template('index.html',
                           excel_exists=excel_exists,
                           current_date=current_date,
                           current_month=current_month,
                           invoice_count=invoice_count,
                           email_config=email_config)


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
    """Generate all invoices"""
    send_email = request.form.get('send_email') == 'on'

    try:
        # Generate invoices
        pdf_files = process_invoices(
            EXCEL_FILE,
            OUTPUT_FOLDER,
            LOGO_PATH,
            email_config if send_email else None
        )

        flash(f'✅ Successfully generated {len(pdf_files)} invoice(s)!', 'success')

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


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🌸 VELVET LAVENDER INVOICE GENERATOR")
    print("=" * 60)
    print("\n✨ Starting secure web server...")
    print("🔒 Login required - Password: anamoux")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("\n💡 Press Ctrl+C to stop the server\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
