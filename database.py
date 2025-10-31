import os
from datetime import datetime

# Check if we're using PostgreSQL or SQLite
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # PostgreSQL (Render/Production)
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from urllib.parse import urlparse

    # Fix for Render's postgres:// vs postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


    def get_connection():
        """Get PostgreSQL connection"""
        return psycopg2.connect(DATABASE_URL)


    USE_POSTGRES = True
    print("🐘 Using PostgreSQL database")
else:
    # SQLite (Local development)
    import sqlite3

    DATABASE = 'invoices.db'


    def get_connection():
        """Get SQLite connection"""
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn


    USE_POSTGRES = False
    print("💾 Using SQLite database")


def init_db():
    """Initialize the database with invoices table"""
    conn = get_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        # PostgreSQL syntax
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id SERIAL PRIMARY KEY,
                invoice_number TEXT NOT NULL UNIQUE,
                client_name TEXT NOT NULL,
                client_address TEXT,
                amount DECIMAL(10, 2) NOT NULL,
                tax DECIMAL(10, 2),
                total_amount DECIMAL(10, 2) NOT NULL,
                issue_date TEXT NOT NULL,
                due_date TEXT,
                month TEXT NOT NULL,
                year INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                payment_date TEXT,
                pdf_filename TEXT,
                template TEXT DEFAULT 'classic',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        # SQLite syntax
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL UNIQUE,
                client_name TEXT NOT NULL,
                client_address TEXT,
                amount REAL NOT NULL,
                tax REAL,
                total_amount REAL NOT NULL,
                issue_date TEXT NOT NULL,
                due_date TEXT,
                month TEXT NOT NULL,
                year INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                payment_date TEXT,
                pdf_filename TEXT,
                template TEXT DEFAULT 'classic',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    conn.commit()
    conn.close()
    print("✅ Database initialized!")


def add_invoice(invoice_data):
    """Add a new invoice to the database - BULLETPROOF VERSION"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Extract client address (combine all address fields)
        client_address_parts = []
        for i in range(2, 5):
            addr = invoice_data.get(f'client_address_{i}', '')
            if addr:
                client_address_parts.append(addr)
        client_address = '\n'.join(client_address_parts)

        # Clean and convert amounts
        def clean_amount(value):
            """Remove commas and convert to float"""
            if isinstance(value, (int, float)):
                return float(value)
            return float(str(value).replace(',', ''))

        amount = clean_amount(invoice_data.get('total', 0))
        tax = clean_amount(invoice_data.get('tax', 0))
        total_amount = clean_amount(invoice_data.get('total_amount', 0))

        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO invoices (
                    invoice_number, client_name, client_address, amount, tax, 
                    total_amount, issue_date, due_date, month, year, 
                    status, pdf_filename, template
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (invoice_number) DO UPDATE SET
                    client_name = EXCLUDED.client_name,
                    total_amount = EXCLUDED.total_amount,
                    updated_at = CURRENT_TIMESTAMP
            ''', (
                invoice_data['invoice_number'],
                invoice_data['client_name'],
                client_address,
                amount,
                tax,
                total_amount,
                invoice_data['date_issued'],
                invoice_data.get('due_date'),
                invoice_data['month'],
                datetime.now().year,
                'pending',
                invoice_data.get('pdf_filename', ''),
                invoice_data.get('template', 'classic')
            ))
        else:
            cursor.execute('''
                INSERT OR REPLACE INTO invoices (
                    invoice_number, client_name, client_address, amount, tax, 
                    total_amount, issue_date, due_date, month, year, 
                    status, pdf_filename, template
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_data['invoice_number'],
                invoice_data['client_name'],
                client_address,
                amount,
                tax,
                total_amount,
                invoice_data['date_issued'],
                invoice_data.get('due_date'),
                invoice_data['month'],
                datetime.now().year,
                'pending',
                invoice_data.get('pdf_filename', ''),
                invoice_data.get('template', 'classic')
            ))

        conn.commit()
        print(f"✅ Invoice {invoice_data['invoice_number']} added to database")
        return True
    except Exception as e:
        print(f"❌ Error adding invoice: {e}")
        print(f"   Invoice data: {invoice_data}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_all_invoices():
    """Get all invoices from database"""
    try:
        conn = get_connection()

        if USE_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM invoices 
            ORDER BY created_at DESC
        ''')

        invoices = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return invoices
    except Exception as e:
        print(f"❌ Error getting invoices: {e}")
        return []


def get_invoice_by_number(invoice_number):
    """Get a specific invoice by number"""
    try:
        conn = get_connection()

        if USE_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('SELECT * FROM invoices WHERE invoice_number = %s', (invoice_number,))
        else:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM invoices WHERE invoice_number = ?', (invoice_number,))

        invoice = cursor.fetchone()
        conn.close()

        return dict(invoice) if invoice else None
    except Exception as e:
        print(f"❌ Error getting invoice: {e}")
        return None


def update_invoice_status(invoice_number, status, payment_date=None):
    """Update invoice payment status"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if USE_POSTGRES:
            if payment_date:
                cursor.execute('''
                    UPDATE invoices 
                    SET status = %s, payment_date = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE invoice_number = %s
                ''', (status, payment_date, invoice_number))
            else:
                cursor.execute('''
                    UPDATE invoices 
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE invoice_number = %s
                ''', (status, invoice_number))
        else:
            if payment_date:
                cursor.execute('''
                    UPDATE invoices 
                    SET status = ?, payment_date = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE invoice_number = ?
                ''', (status, payment_date, invoice_number))
            else:
                cursor.execute('''
                    UPDATE invoices 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE invoice_number = ?
                ''', (status, invoice_number))

        conn.commit()
        print(f"✅ Invoice {invoice_number} status updated to {status}")
    except Exception as e:
        print(f"❌ Error updating status: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_invoice_stats():
    """Get invoice statistics - BULLETPROOF VERSION"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Get all invoices
        cursor.execute('SELECT status, total_amount, payment_date FROM invoices')
        all_invoices = cursor.fetchall()
        conn.close()

        # Calculate everything in Python (works everywhere!)
        outstanding = 0
        pending_count = 0
        paid_count = 0
        overdue_count = 0
        paid_this_month = 0

        current_month = datetime.now().strftime('%Y-%m')

        for row in all_invoices:
            status = row[0]
            amount = float(row[1]) if row[1] else 0
            payment_date = row[2]

            # Count by status
            if status == 'pending':
                pending_count += 1
                outstanding += amount
            elif status == 'overdue':
                overdue_count += 1
                outstanding += amount
            elif status == 'paid':
                paid_count += 1
                # Check if paid this month
                if payment_date and payment_date.startswith(current_month):
                    paid_this_month += amount

        return {
            'outstanding': round(outstanding, 2),
            'pending_count': pending_count,
            'paid_count': paid_count,
            'overdue_count': overdue_count,
            'paid_this_month': round(paid_this_month, 2)
        }
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return {
            'outstanding': 0,
            'pending_count': 0,
            'paid_count': 0,
            'overdue_count': 0,
            'paid_this_month': 0
        }


def delete_invoice(invoice_number):
    """Delete an invoice from database"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if USE_POSTGRES:
            cursor.execute('DELETE FROM invoices WHERE invoice_number = %s', (invoice_number,))
        else:
            cursor.execute('DELETE FROM invoices WHERE invoice_number = ?', (invoice_number,))

        conn.commit()
        print(f"✅ Invoice {invoice_number} deleted")
    except Exception as e:
        print(f"❌ Error deleting invoice: {e}")
        conn.rollback()
    finally:
        conn.close()


# Initialize database when module is imported
try:
    init_db()
except Exception as e:
    print(f"⚠️ Database initialization error: {e}")