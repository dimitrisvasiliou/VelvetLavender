import sqlite3
from datetime import datetime

DATABASE = 'invoices.db'


def init_db():
    """Initialize the database with invoices table"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

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
    """Add a new invoice to the database"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO invoices (
                invoice_number, client_name, client_address, amount, tax, 
                total_amount, issue_date, due_date, month, year, 
                status, pdf_filename, template
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            invoice_data['invoice_number'],
            invoice_data['client_name'],
            invoice_data.get('client_address', ''),
            float(invoice_data['total'].replace(',', '')),
            float(invoice_data['tax'].replace(',', '')),
            float(invoice_data['total_amount'].replace(',', '')),
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
    except sqlite3.IntegrityError:
        print(f"⚠️ Invoice {invoice_data['invoice_number']} already exists")
        return False
    except Exception as e:
        print(f"❌ Error adding invoice: {e}")
        return False
    finally:
        conn.close()


def get_all_invoices():
    """Get all invoices from database"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM invoices 
        ORDER BY created_at DESC
    ''')

    invoices = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return invoices


def get_invoice_by_number(invoice_number):
    """Get a specific invoice by number"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM invoices WHERE invoice_number = ?', (invoice_number,))
    invoice = cursor.fetchone()
    conn.close()

    return dict(invoice) if invoice else None


def update_invoice_status(invoice_number, status, payment_date=None):
    """Update invoice payment status"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

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
    conn.close()
    print(f"✅ Invoice {invoice_number} status updated to {status}")


def get_invoice_stats():
    """Get invoice statistics"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Total outstanding
    cursor.execute('''
        SELECT SUM(total_amount) FROM invoices 
        WHERE status IN ('pending', 'overdue')
    ''')
    outstanding = cursor.fetchone()[0] or 0

    # Count by status
    cursor.execute('''
        SELECT status, COUNT(*) as count 
        FROM invoices 
        GROUP BY status
    ''')
    status_counts = dict(cursor.fetchall())

    # Total paid this month
    cursor.execute('''
        SELECT SUM(total_amount) FROM invoices 
        WHERE status = 'paid' 
        AND strftime('%Y-%m', payment_date) = strftime('%Y-%m', 'now')
    ''')
    paid_this_month = cursor.fetchone()[0] or 0

    conn.close()

    return {
        'outstanding': round(outstanding, 2),
        'pending_count': status_counts.get('pending', 0),
        'paid_count': status_counts.get('paid', 0),
        'overdue_count': status_counts.get('overdue', 0),
        'paid_this_month': round(paid_this_month, 2)
    }


def delete_invoice(invoice_number):
    """Delete an invoice from database"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM invoices WHERE invoice_number = ?', (invoice_number,))
    conn.commit()
    conn.close()
    print(f"✅ Invoice {invoice_number} deleted")


# Initialize database when module is imported
init_db()
