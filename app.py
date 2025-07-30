#!/usr/bin/env python3
"""
Web-based Inventory Management System
Main Flask Application
"""

import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import psycopg2
from datetime import datetime, date
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") 

# Database configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'inventory_management')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def get_db_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# ===== AUTO-GENERATION HELPER FUNCTIONS =====

def get_next_part_number():
    """Generate next part number (numeric for DB, display as P001)"""
    try:
        conn = get_db_connection()
        if not conn:
            return 1

        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(part_num), 0) + 1 FROM part WHERE company = 1")
        next_num = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        return next_num
    except Exception as e:
        print(f"Error generating part number: {e}")
        return 1

def get_next_customer_code():
    """Generate next customer code (numeric for DB, display as C001)"""
    try:
        conn = get_db_connection()
        if not conn:
            return 1

        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(customer_code), 0) + 1 FROM customer WHERE company = 1")
        next_code = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        return next_code
    except Exception as e:
        print(f"Error generating customer code: {e}")
        return 1

def get_next_vendor_code():
    """Generate next vendor code (numeric for DB, display as V001)"""
    try:
        conn = get_db_connection()
        if not conn:
            return 1

        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(vendor_code), 0) + 1 FROM vendor WHERE company = 1")
        next_code = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        return next_code
    except Exception as e:
        print(f"Error generating vendor code: {e}")
        return 1

def get_next_po_number():
    """Generate next purchase order number (numeric for DB, display as PO001)"""
    try:
        conn = get_db_connection()
        if not conn:
            return 1

        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(po_no), 0) + 1 FROM purchase_order_head WHERE company = 1")
        next_po = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        return next_po
    except Exception as e:
        print(f"Error generating PO number: {e}")
        return 1

def get_next_invoice_number():
    """Generate next sales invoice number (numeric for DB, display as SI001)"""
    try:
        conn = get_db_connection()
        if not conn:
            return 1

        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(inv_no), 0) + 1 FROM sales_invoice_head WHERE company = 1")
        next_inv = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        return next_inv
    except Exception as e:
        print(f"Error generating invoice number: {e}")
        return 1

def get_next_indent_number():
    """Generate next indent number (numeric for DB, display as IN001)"""
    try:
        conn = get_db_connection()
        if not conn:
            return 1

        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(indent_id), 0) + 1 FROM indent_request_head WHERE company = 1")
        next_indent = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        return next_indent
    except Exception as e:
        print(f"Error generating indent number: {e}")
        return 1

@app.route('/')
def dashboard():
    """Main dashboard"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return render_template('error.html', message='Database connection failed')
        
        cursor = conn.cursor()
        
        # Get dashboard statistics
        stats = {}
        
        # Total parts
        cursor.execute("SELECT COUNT(*) FROM part WHERE active = true")
        stats['total_parts'] = cursor.fetchone()[0]
        
        # Total vendors
        cursor.execute("SELECT COUNT(*) FROM vendor WHERE active = true")
        stats['total_vendors'] = cursor.fetchone()[0]
        
        # Total customers
        cursor.execute("SELECT COUNT(*) FROM customer WHERE active = true")
        stats['total_customers'] = cursor.fetchone()[0]
        
        # Pending purchase orders
        cursor.execute("SELECT COUNT(*) FROM purchase_order_head WHERE active = true")
        stats['pending_pos'] = cursor.fetchone()[0]
        
        # Recent transactions
        cursor.execute("""
            SELECT 'Purchase Order' as type, po_no as doc_no, po_date as doc_date, 
                   v.vendor_name as party_name
            FROM purchase_order_head poh
            JOIN vendor v ON poh.vendor = v.vendor_code AND poh.company = v.company
            WHERE poh.active = true
            ORDER BY poh.po_date DESC
            LIMIT 5
        """)
        recent_transactions = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('dashboard.html', stats=stats, recent_transactions=recent_transactions)
        
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('error.html', message=str(e))

@app.route('/parts')
def parts():
    """Parts management page"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return render_template('error.html', message='Database connection failed')
        
        cursor = conn.cursor()
        
        # Get all parts with unit and tax information
        cursor.execute("""
            SELECT p.part_num, p.part_desc, p.part_type, p.part_category,
                   u.unit_desc, p.pur_price, p.sell_price, p.hsn_code,
                   t.tax_desc, p.tax_percent, p.active
            FROM part p
            LEFT JOIN unit u ON p.unit_id = u.unit_id AND p.company = u.company
            LEFT JOIN tax t ON p.tax_id = t.tax_id AND p.company = t.company
            ORDER BY p.part_num
        """)
        
        parts_data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template('parts.html', parts=parts_data)
        
    except Exception as e:
        flash(f'Error loading parts: {str(e)}', 'error')
        return render_template('error.html', message=str(e))

@app.route('/vendors')
def vendors():
    """Vendors management page"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return render_template('error.html', message='Database connection failed')
        
        cursor = conn.cursor()
        
        # Get all vendors
        cursor.execute("""
            SELECT vendor_code, vendor_name, city, state, phone, mobile, 
                   email, gst, active
            FROM vendor
            ORDER BY vendor_name
        """)
        
        vendors_data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template('vendors.html', vendors=vendors_data)
        
    except Exception as e:
        flash(f'Error loading vendors: {str(e)}', 'error')
        return render_template('error.html', message=str(e))

@app.route('/customers')
def customers():
    """Customers management page"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return render_template('error.html', message='Database connection failed')
        
        cursor = conn.cursor()
        
        # Get all customers
        cursor.execute("""
            SELECT customer_code, customer_name, city, state, phone, mobile, 
                   email, gst, active
            FROM customer
            ORDER BY customer_name
        """)
        
        customers_data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template('customers.html', customers=customers_data)
        
    except Exception as e:
        flash(f'Error loading customers: {str(e)}', 'error')
        return render_template('error.html', message=str(e))

@app.route('/purchase_orders')
def purchase_orders():
    """Purchase Orders management page"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return render_template('error.html', message='Database connection failed')
        
        cursor = conn.cursor()
        
        # Get all purchase orders with vendor information
        cursor.execute("""
            SELECT poh.po_no, poh.po_date, v.vendor_name, poh.active,
                   COUNT(CASE WHEN pot.active = true THEN pot.rowid END) as line_items,
                   SUM(CASE WHEN pot.active = true THEN pot.amount ELSE 0 END) as total_amount
            FROM purchase_order_head poh
            LEFT JOIN vendor v ON poh.vendor = v.vendor_code AND poh.company = v.company
            LEFT JOIN purchase_order_tran pot ON poh.po_no = pot.po_no AND poh.company = pot.company
            WHERE poh.company = 1
            GROUP BY poh.po_no, poh.po_date, v.vendor_name, poh.active
            ORDER BY poh.po_date DESC
        """)
        
        po_data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template('purchase_orders.html', purchase_orders=po_data)
        
    except Exception as e:
        flash(f'Error loading purchase orders: {str(e)}', 'error')
        return render_template('error.html', message=str(e))

# Parts CRUD Operations
@app.route('/parts/add', methods=['GET', 'POST'])
def add_part():
    """Add new part"""
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'error')
                return redirect(url_for('parts'))

            cursor = conn.cursor()

            # Get form data
            part_num = request.form['part_num']
            part_desc = request.form['part_desc']
            part_type = request.form.get('part_type')
            part_category = request.form.get('part_category')
            unit_id = request.form.get('unit_id') or None
            pur_price = request.form.get('pur_price') or None
            sell_price = request.form.get('sell_price') or None
            hsn_code = request.form.get('hsn_code')
            tax_id = request.form.get('tax_id') or None
            tax_percent = request.form.get('tax_percent') or None
            lot = request.form.get('lot') == 'on'
            batch = request.form.get('batch') == 'on'
            warranty = request.form.get('warranty') == 'on'
            costing = request.form.get('costing')

            # Insert new part
            cursor.execute("""
                INSERT INTO part (company, part_num, part_desc, part_type, part_category,
                                unit_id, pur_price, sell_price, hsn_code, tax_id, tax_percent,
                                lot, batch, warranty, costing, active, created_by, updated)
                VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, 'admin', CURRENT_DATE)
            """, (part_num, part_desc, part_type, part_category, unit_id, pur_price,
                  sell_price, hsn_code, tax_id, tax_percent, lot, batch, warranty, costing))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Part added successfully!', 'success')
            return redirect(url_for('parts'))

        except Exception as e:
            flash(f'Error adding part: {str(e)}', 'error')
            return redirect(url_for('parts'))

    # GET request - show form
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('parts'))

        cursor = conn.cursor()

        # Get units for dropdown
        cursor.execute("SELECT unit_id, unit_desc FROM unit WHERE active = true ORDER BY unit_desc")
        units = cursor.fetchall()

        # Get taxes for dropdown
        cursor.execute("SELECT tax_id, tax_desc, tax_percent FROM tax WHERE active = true ORDER BY tax_desc")
        taxes = cursor.fetchall()

        cursor.close()
        conn.close()

        # Generate next part number
        next_part_num = get_next_part_number()

        return render_template('add_part.html', units=units, taxes=taxes, next_part_num=next_part_num)

    except Exception as e:
        flash(f'Error loading form: {str(e)}', 'error')
        return redirect(url_for('parts'))

@app.route('/parts/edit/<int:part_num>', methods=['GET', 'POST'])
def edit_part(part_num):
    """Edit existing part"""
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'error')
                return redirect(url_for('parts'))

            cursor = conn.cursor()

            # Get form data
            part_desc = request.form['part_desc']
            part_type = request.form.get('part_type')
            part_category = request.form.get('part_category')
            unit_id = request.form.get('unit_id') or None
            pur_price = request.form.get('pur_price') or None
            sell_price = request.form.get('sell_price') or None
            hsn_code = request.form.get('hsn_code')
            tax_id = request.form.get('tax_id') or None
            tax_percent = request.form.get('tax_percent') or None
            lot = request.form.get('lot') == 'on'
            batch = request.form.get('batch') == 'on'
            warranty = request.form.get('warranty') == 'on'
            costing = request.form.get('costing')
            active = request.form.get('active') == 'on'

            # Update part
            cursor.execute("""
                UPDATE part SET part_desc = %s, part_type = %s, part_category = %s,
                              unit_id = %s, pur_price = %s, sell_price = %s, hsn_code = %s,
                              tax_id = %s, tax_percent = %s, lot = %s, batch = %s, warranty = %s,
                              costing = %s, active = %s, updated = CURRENT_DATE
                WHERE company = 1 AND part_num = %s
            """, (part_desc, part_type, part_category, unit_id, pur_price, sell_price,
                  hsn_code, tax_id, tax_percent, lot, batch, warranty, costing, active, part_num))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Part updated successfully!', 'success')
            return redirect(url_for('parts'))

        except Exception as e:
            flash(f'Error updating part: {str(e)}', 'error')
            return redirect(url_for('parts'))

    # GET request - show form with existing data
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('parts'))

        cursor = conn.cursor()

        # Get part data
        cursor.execute("""
            SELECT * FROM part WHERE company = 1 AND part_num = %s
        """, (part_num,))
        part = cursor.fetchone()

        if not part:
            flash('Part not found', 'error')
            return redirect(url_for('parts'))

        # Get units for dropdown
        cursor.execute("SELECT unit_id, unit_desc FROM unit WHERE active = true ORDER BY unit_desc")
        units = cursor.fetchall()

        # Get taxes for dropdown
        cursor.execute("SELECT tax_id, tax_desc, tax_percent FROM tax WHERE active = true ORDER BY tax_desc")
        taxes = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('edit_part.html', part=part, units=units, taxes=taxes)

    except Exception as e:
        flash(f'Error loading part: {str(e)}', 'error')
        return redirect(url_for('parts'))

@app.route('/parts/delete/<int:part_num>', methods=['POST'])
def delete_part(part_num):
    """Delete part (soft delete)"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('parts'))

        cursor = conn.cursor()

        # Soft delete - set active to false
        cursor.execute("""
            UPDATE part SET active = false, updated = CURRENT_DATE
            WHERE company = 1 AND part_num = %s
        """, (part_num,))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Part deleted successfully!', 'success')
        return redirect(url_for('parts'))

    except Exception as e:
        flash(f'Error deleting part: {str(e)}', 'error')
        return redirect(url_for('parts'))

@app.route('/parts/view/<int:part_num>')
def view_part(part_num):
    """View part details"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('parts'))

        cursor = conn.cursor()

        # Get part details with unit information
        cursor.execute("""
            SELECT p.company, p.part_num, p.part_desc, p.part_type, p.part_category,
                   p.unit_id, p.pur_price, p.sell_price, p.hsn_code, p.costing_method,
                   p.tax_id, p.tax_percent, p.active, p.created, p.updated,
                   u.unit_desc, COALESCE(t.tax_desc, 'N/A') as tax_desc
            FROM part p
            LEFT JOIN unit u ON p.unit_id = u.unit_id AND p.company = u.company
            LEFT JOIN tax t ON p.tax_id = t.tax_id AND p.company = t.company
            WHERE p.company = 1 AND p.part_num = %s
        """, (part_num,))
        part_details = cursor.fetchone()

        if not part_details:
            flash('Part not found', 'error')
            return redirect(url_for('parts'))

        # Get stock information
        cursor.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN type = 'IN' THEN qty ELSE -qty END), 0) as current_stock,
                COUNT(*) as total_transactions,
                MAX(update_date) as last_updated
            FROM stock_update
            WHERE company = 1 AND part_num = %s
        """, (part_num,))
        stock_info = cursor.fetchone()

        # Get recent purchase history
        cursor.execute("""
            SELECT poh.po_no, poh.po_date, v.vendor_name, pot.quantity, pot.unit_price, pot.amount
            FROM purchase_order_tran pot
            JOIN purchase_order_head poh ON pot.po_no = poh.po_no AND pot.company = poh.company
            LEFT JOIN vendor v ON poh.vendor = v.vendor_code AND poh.company = v.company
            WHERE pot.company = 1 AND pot.partnum = %s AND pot.active = true
            ORDER BY poh.po_date DESC
            LIMIT 5
        """, (part_num,))
        purchase_history = cursor.fetchall()

        # Get recent sales history
        cursor.execute("""
            SELECT sih.inv_no, sih.inv_dt, c.customer_name, sit.quantity, sit.unit_price, sit.amount
            FROM sales_invoice_tran sit
            JOIN sales_invoice_head sih ON sit.inv_no = sih.inv_no AND sit.company = sih.company
            LEFT JOIN customer c ON sih.customer = c.customer_code AND sih.company = c.company
            WHERE sit.company = 1 AND sit.partnum = %s AND sit.active = true
            ORDER BY sih.inv_dt DESC
            LIMIT 5
        """, (part_num,))
        sales_history = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('view_part.html',
                             part_details=part_details,
                             stock_info=stock_info,
                             purchase_history=purchase_history,
                             sales_history=sales_history)

    except Exception as e:
        flash(f'Error loading part details: {str(e)}', 'error')
        return redirect(url_for('parts'))

@app.route('/api/dashboard_stats')
def api_dashboard_stats():
    """API endpoint for dashboard statistics"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()

        # Get critical business analytics for 3 key charts
        stats = {}

        # 1. REVENUE vs EXPENSES (Last 6 Months) - Most Critical for Business Health
        # Total Sales Revenue
        cursor.execute("""
            SELECT COALESCE(SUM(sit.amount), 0) as total_sales
            FROM sales_invoice_head sih
            JOIN sales_invoice_tran sit ON sih.inv_no = sit.inv_no AND sih.company = sit.company
            WHERE sih.inv_dt >= CURRENT_DATE - INTERVAL '6 months'
            AND sih.active = true AND sit.active = true
        """)
        total_sales = cursor.fetchone()[0] or 0

        # Total Purchase Expenses
        cursor.execute("""
            SELECT COALESCE(SUM(pot.amount), 0) as total_purchases
            FROM purchase_order_head poh
            JOIN purchase_order_tran pot ON poh.po_no = pot.po_no AND poh.company = pot.company
            WHERE poh.po_date >= CURRENT_DATE - INTERVAL '6 months'
            AND poh.active = true AND pot.active = true
        """)
        total_purchases = cursor.fetchone()[0] or 0

        profit = total_sales - total_purchases
        stats['revenue_expense'] = {
            'Sales Revenue': float(total_sales),
            'Purchase Costs': float(total_purchases),
            'Profit': float(profit) if profit > 0 else 0
        }

        # 2. TOP BUSINESS PARTNERS - Critical for Relationship Management
        # Combine top vendors and customers by value
        partners = {}

        # Top vendors by purchase value
        cursor.execute("""
            SELECT v.vendor_name, SUM(pot.amount) as total_value
            FROM purchase_order_head poh
            JOIN vendor v ON poh.vendor = v.vendor_code AND poh.company = v.company
            JOIN purchase_order_tran pot ON poh.po_no = pot.po_no AND poh.company = pot.company
            WHERE poh.po_date >= CURRENT_DATE - INTERVAL '6 months'
            AND poh.active = true AND pot.active = true
            GROUP BY v.vendor_name
            ORDER BY total_value DESC
            LIMIT 3
        """)
        vendor_data = cursor.fetchall()
        for row in vendor_data:
            partners[f"🏢 {row[0]} (Vendor)"] = float(row[1]) if row[1] else 0

        # Top customers by sales value
        cursor.execute("""
            SELECT c.customer_name, SUM(sit.amount) as total_value
            FROM sales_invoice_head sih
            JOIN customer c ON sih.customer = c.customer_code AND sih.company = c.company
            JOIN sales_invoice_tran sit ON sih.inv_no = sit.inv_no AND sih.company = sit.company
            WHERE sih.inv_dt >= CURRENT_DATE - INTERVAL '6 months'
            AND sih.active = true AND sit.active = true
            GROUP BY c.customer_name
            ORDER BY total_value DESC
            LIMIT 3
        """)
        customer_data = cursor.fetchall()
        for row in customer_data:
            partners[f"👥 {row[0]} (Customer)"] = float(row[1]) if row[1] else 0

        stats['top_partners'] = partners

        # 3. OPERATIONAL EFFICIENCY - Critical for Workflow Management
        # Count active vs completed operations across all key processes
        operations = {}

        # Active Purchase Orders
        cursor.execute("SELECT COUNT(*) FROM purchase_order_head WHERE active = true")
        active_pos = cursor.fetchone()[0] or 0

        # Pending GRNs (Active POs without corresponding GRNs)
        cursor.execute("""
            SELECT COUNT(*) FROM purchase_order_head poh
            LEFT JOIN goods_receipt_head grh ON poh.po_no = grh.po_no AND poh.company = grh.company
            WHERE poh.active = true AND grh.po_no IS NULL
        """)
        pending_grns = cursor.fetchone()[0] or 0

        # Active Sales Invoices
        cursor.execute("SELECT COUNT(*) FROM sales_invoice_head WHERE active = true")
        active_invoices = cursor.fetchone()[0] or 0

        # Total Completed Operations (last 30 days)
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT 1 FROM purchase_order_head WHERE active = false AND po_date >= CURRENT_DATE - INTERVAL '30 days'
                UNION ALL
                SELECT 1 FROM sales_invoice_head WHERE active = false AND inv_dt >= CURRENT_DATE - INTERVAL '30 days'
                UNION ALL
                SELECT 1 FROM goods_receipt_head WHERE active = false AND grn_dt >= CURRENT_DATE - INTERVAL '30 days'
            ) completed
        """)
        completed_ops = cursor.fetchone()[0] or 0

        operations = {
            'Active Purchase Orders': active_pos,
            'Pending GRNs': pending_grns,
            'Active Sales Invoices': active_invoices,
            'Completed Operations (30d)': completed_ops
        }

        stats['operational_status'] = operations

        cursor.close()
        conn.close()

        return jsonify(stats)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test_charts')
def test_charts():
    """Test page for Chart.js"""
    return render_template('test_charts.html')

# Vendor CRUD Operations
@app.route('/vendors/add', methods=['GET', 'POST'])
def add_vendor():
    """Add new vendor"""
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'error')
                return redirect(url_for('vendors'))

            cursor = conn.cursor()

            # Get form data
            vendor_code = request.form['vendor_code']
            vendor_name = request.form['vendor_name']
            address1 = request.form.get('address1')
            address2 = request.form.get('address2')
            location = request.form.get('location')
            city = request.form.get('city')
            state = request.form.get('state')
            pin = request.form.get('pin') or None
            std_code = request.form.get('std_code') or None
            phone = request.form.get('phone') or None
            mobile = request.form.get('mobile') or None
            email = request.form.get('email')
            website = request.form.get('website')
            gst = request.form.get('gst')
            pan = request.form.get('pan')

            # Insert new vendor
            cursor.execute("""
                INSERT INTO vendor (company, vendor_code, vendor_name, address1, address2,
                                  location, city, state, pin, std_code, phone, mobile,
                                  email, website, gst, pan, active, created_by, updated)
                VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, 'admin', CURRENT_DATE)
            """, (vendor_code, vendor_name, address1, address2, location, city, state,
                  pin, std_code, phone, mobile, email, website, gst, pan))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Vendor added successfully!', 'success')
            return redirect(url_for('vendors'))

        except Exception as e:
            flash(f'Error adding vendor: {str(e)}', 'error')
            return redirect(url_for('vendors'))

    # GET request - show form
    next_vendor_code = get_next_vendor_code()
    return render_template('add_vendor.html', next_vendor_code=next_vendor_code)

@app.route('/vendors/edit/<int:vendor_code>', methods=['GET', 'POST'])
def edit_vendor(vendor_code):
    """Edit existing vendor"""
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'error')
                return redirect(url_for('vendors'))

            cursor = conn.cursor()

            # Get form data
            vendor_name = request.form['vendor_name']
            address1 = request.form.get('address1')
            address2 = request.form.get('address2')
            location = request.form.get('location')
            city = request.form.get('city')
            state = request.form.get('state')
            pin = request.form.get('pin') or None
            std_code = request.form.get('std_code') or None
            phone = request.form.get('phone') or None
            mobile = request.form.get('mobile') or None
            email = request.form.get('email')
            website = request.form.get('website')
            gst = request.form.get('gst')
            pan = request.form.get('pan')
            active = request.form.get('active') == 'on'

            # Update vendor
            cursor.execute("""
                UPDATE vendor SET vendor_name = %s, address1 = %s, address2 = %s,
                                location = %s, city = %s, state = %s, pin = %s,
                                std_code = %s, phone = %s, mobile = %s, email = %s,
                                website = %s, gst = %s, pan = %s, active = %s, updated = CURRENT_DATE
                WHERE company = 1 AND vendor_code = %s
            """, (vendor_name, address1, address2, location, city, state, pin,
                  std_code, phone, mobile, email, website, gst, pan, active, vendor_code))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Vendor updated successfully!', 'success')
            return redirect(url_for('vendors'))

        except Exception as e:
            flash(f'Error updating vendor: {str(e)}', 'error')
            return redirect(url_for('vendors'))

    # GET request - show form with existing data
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('vendors'))

        cursor = conn.cursor()

        # Get vendor data
        cursor.execute("""
            SELECT * FROM vendor WHERE company = 1 AND vendor_code = %s
        """, (vendor_code,))
        vendor = cursor.fetchone()

        if not vendor:
            flash('Vendor not found', 'error')
            return redirect(url_for('vendors'))

        cursor.close()
        conn.close()

        return render_template('edit_vendor.html', vendor=vendor)

    except Exception as e:
        flash(f'Error loading vendor: {str(e)}', 'error')
        return redirect(url_for('vendors'))

@app.route('/vendors/delete/<int:vendor_code>', methods=['POST'])
def delete_vendor(vendor_code):
    """Delete vendor (soft delete)"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('vendors'))

        cursor = conn.cursor()

        # Soft delete - set active to false
        cursor.execute("""
            UPDATE vendor SET active = false, updated = CURRENT_DATE
            WHERE company = 1 AND vendor_code = %s
        """, (vendor_code,))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Vendor deleted successfully!', 'success')
        return redirect(url_for('vendors'))

    except Exception as e:
        flash(f'Error deleting vendor: {str(e)}', 'error')
        return redirect(url_for('vendors'))

@app.route('/vendors/view/<int:vendor_code>')
def view_vendor(vendor_code):
    """View vendor details"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('vendors'))

        cursor = conn.cursor()

        # Get vendor details
        cursor.execute("""
            SELECT company, vendor_code, vendor_name, address1, address2, city, state,
                   country, pincode, phone, mobile, email, gst, pan, created, updated, active
            FROM vendor WHERE company = 1 AND vendor_code = %s
        """, (vendor_code,))
        vendor_details = cursor.fetchone()

        if not vendor_details:
            flash('Vendor not found', 'error')
            return redirect(url_for('vendors'))

        # Get purchase order statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_pos,
                COUNT(CASE WHEN active = true THEN 1 END) as active_pos,
                COALESCE(SUM(CASE WHEN active = true THEN
                    (SELECT SUM(amount) FROM purchase_order_tran WHERE po_no = poh.po_no AND company = poh.company AND active = true)
                END), 0) as total_po_value,
                MAX(po_date) as last_po_date
            FROM purchase_order_head poh
            WHERE company = 1 AND vendor = %s
        """, (vendor_code,))
        po_stats = cursor.fetchone()

        # Get recent purchase orders
        cursor.execute("""
            SELECT poh.po_no, poh.po_date, poh.active,
                   COUNT(pot.rowid) as line_items,
                   COALESCE(SUM(pot.amount), 0) as total_amount
            FROM purchase_order_head poh
            LEFT JOIN purchase_order_tran pot ON poh.po_no = pot.po_no AND poh.company = pot.company AND pot.active = true
            WHERE poh.company = 1 AND poh.vendor = %s
            GROUP BY poh.po_no, poh.po_date, poh.active
            ORDER BY poh.po_date DESC
            LIMIT 10
        """, (vendor_code,))
        recent_pos = cursor.fetchall()

        # Get top purchased parts
        cursor.execute("""
            SELECT p.part_num, p.part_desc,
                   COUNT(*) as purchase_count,
                   SUM(pot.quantity) as total_quantity,
                   SUM(pot.amount) as total_value
            FROM purchase_order_tran pot
            JOIN purchase_order_head poh ON pot.po_no = poh.po_no AND pot.company = poh.company
            LEFT JOIN part p ON pot.partnum = p.part_num AND pot.company = p.company
            WHERE poh.company = 1 AND poh.vendor = %s AND pot.active = true
            GROUP BY p.part_num, p.part_desc
            ORDER BY total_value DESC
            LIMIT 5
        """, (vendor_code,))
        top_parts = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('view_vendor.html',
                             vendor_details=vendor_details,
                             po_stats=po_stats,
                             recent_pos=recent_pos,
                             top_parts=top_parts)

    except Exception as e:
        flash(f'Error loading vendor details: {str(e)}', 'error')
        return redirect(url_for('vendors'))

# Customer CRUD Operations
@app.route('/customers/add', methods=['GET', 'POST'])
def add_customer():
    """Add new customer"""
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'error')
                return redirect(url_for('customers'))

            cursor = conn.cursor()

            # Get form data
            customer_code = request.form['customer_code']
            customer_name = request.form['customer_name']
            address1 = request.form.get('address1')
            address2 = request.form.get('address2')
            location = request.form.get('location')
            city = request.form.get('city')
            state = request.form.get('state')
            pin = request.form.get('pin') or None
            std_code = request.form.get('std_code') or None
            phone = request.form.get('phone') or None
            mobile = request.form.get('mobile') or None
            email = request.form.get('email')
            website = request.form.get('website')
            gst = request.form.get('gst')
            pan = request.form.get('pan')

            # Insert new customer
            cursor.execute("""
                INSERT INTO customer (company, customer_code, customer_name, address1, address2,
                                    location, city, state, pin, std_code, phone, mobile,
                                    email, website, gst, pan, active, created_by, updated)
                VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, 'admin', CURRENT_DATE)
            """, (customer_code, customer_name, address1, address2, location, city, state,
                  pin, std_code, phone, mobile, email, website, gst, pan))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Customer added successfully!', 'success')
            return redirect(url_for('customers'))

        except Exception as e:
            flash(f'Error adding customer: {str(e)}', 'error')
            return redirect(url_for('customers'))

    # GET request - show form
    next_customer_code = get_next_customer_code()
    return render_template('add_customer.html', next_customer_code=next_customer_code)

@app.route('/customers/edit/<int:customer_code>', methods=['GET', 'POST'])
def edit_customer(customer_code):
    """Edit existing customer"""
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'error')
                return redirect(url_for('customers'))

            cursor = conn.cursor()

            # Get form data
            customer_name = request.form['customer_name']
            address1 = request.form.get('address1')
            address2 = request.form.get('address2')
            location = request.form.get('location')
            city = request.form.get('city')
            state = request.form.get('state')
            pin = request.form.get('pin') or None
            std_code = request.form.get('std_code') or None
            phone = request.form.get('phone') or None
            mobile = request.form.get('mobile') or None
            email = request.form.get('email')
            website = request.form.get('website')
            gst = request.form.get('gst')
            pan = request.form.get('pan')
            active = request.form.get('active') == 'on'

            # Update customer
            cursor.execute("""
                UPDATE customer SET customer_name = %s, address1 = %s, address2 = %s,
                                  location = %s, city = %s, state = %s, pin = %s,
                                  std_code = %s, phone = %s, mobile = %s, email = %s,
                                  website = %s, gst = %s, pan = %s, active = %s, updated = CURRENT_DATE
                WHERE company = 1 AND customer_code = %s
            """, (customer_name, address1, address2, location, city, state, pin,
                  std_code, phone, mobile, email, website, gst, pan, active, customer_code))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Customer updated successfully!', 'success')
            return redirect(url_for('customers'))

        except Exception as e:
            flash(f'Error updating customer: {str(e)}', 'error')
            return redirect(url_for('customers'))

    # GET request - show form with existing data
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('customers'))

        cursor = conn.cursor()

        # Get customer data
        cursor.execute("""
            SELECT * FROM customer WHERE company = 1 AND customer_code = %s
        """, (customer_code,))
        customer = cursor.fetchone()

        if not customer:
            flash('Customer not found', 'error')
            return redirect(url_for('customers'))

        cursor.close()
        conn.close()

        return render_template('edit_customer.html', customer=customer)

    except Exception as e:
        flash(f'Error loading customer: {str(e)}', 'error')
        return redirect(url_for('customers'))

@app.route('/customers/delete/<int:customer_code>', methods=['POST'])
def delete_customer(customer_code):
    """Delete customer (soft delete)"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('customers'))

        cursor = conn.cursor()

        # Soft delete - set active to false
        cursor.execute("""
            UPDATE customer SET active = false, updated = CURRENT_DATE
            WHERE company = 1 AND customer_code = %s
        """, (customer_code,))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Customer deleted successfully!', 'success')
        return redirect(url_for('customers'))

    except Exception as e:
        flash(f'Error deleting customer: {str(e)}', 'error')
        return redirect(url_for('customers'))

@app.route('/customers/view/<int:customer_code>')
def view_customer(customer_code):
    """View customer details"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('customers'))

        cursor = conn.cursor()

        # Get customer details
        cursor.execute("""
            SELECT company, customer_code, customer_name, address1, address2, city, state,
                   country, pincode, phone, mobile, email, gst, pan, created, updated, active
            FROM customer WHERE company = 1 AND customer_code = %s
        """, (customer_code,))
        customer_details = cursor.fetchone()

        if not customer_details:
            flash('Customer not found', 'error')
            return redirect(url_for('customers'))

        # Get sales invoice statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_invoices,
                COUNT(CASE WHEN active = true THEN 1 END) as active_invoices,
                COALESCE(SUM(CASE WHEN active = true THEN
                    (SELECT SUM(amount) FROM sales_invoice_tran WHERE inv_no = sih.inv_no AND company = sih.company AND active = true)
                END), 0) as total_sales_value,
                MAX(inv_dt) as last_invoice_date
            FROM sales_invoice_head sih
            WHERE company = 1 AND customer = %s
        """, (customer_code,))
        invoice_stats = cursor.fetchone()

        # Get recent sales invoices
        cursor.execute("""
            SELECT sih.inv_no, sih.inv_dt, sih.active,
                   COUNT(sit.rowid) as line_items,
                   COALESCE(SUM(sit.amount), 0) as total_amount
            FROM sales_invoice_head sih
            LEFT JOIN sales_invoice_tran sit ON sih.inv_no = sit.inv_no AND sih.company = sit.company AND sit.active = true
            WHERE sih.company = 1 AND sih.customer = %s
            GROUP BY sih.inv_no, sih.inv_dt, sih.active
            ORDER BY sih.inv_dt DESC
            LIMIT 10
        """, (customer_code,))
        recent_invoices = cursor.fetchall()

        # Get top purchased parts
        cursor.execute("""
            SELECT p.part_num, p.part_desc,
                   COUNT(*) as purchase_count,
                   SUM(sit.quantity) as total_quantity,
                   SUM(sit.amount) as total_value
            FROM sales_invoice_tran sit
            JOIN sales_invoice_head sih ON sit.inv_no = sih.inv_no AND sit.company = sih.company
            LEFT JOIN part p ON sit.partnum = p.part_num AND sit.company = p.company
            WHERE sih.company = 1 AND sih.customer = %s AND sit.active = true
            GROUP BY p.part_num, p.part_desc
            ORDER BY total_value DESC
            LIMIT 5
        """, (customer_code,))
        top_parts = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('view_customer.html',
                             customer_details=customer_details,
                             invoice_stats=invoice_stats,
                             recent_invoices=recent_invoices,
                             top_parts=top_parts)

    except Exception as e:
        flash(f'Error loading customer details: {str(e)}', 'error')
        return redirect(url_for('customers'))

# Purchase Order CRUD Operations
@app.route('/purchase_orders/add', methods=['GET', 'POST'])
def add_purchase_order():
    """Add new purchase order"""
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'error')
                return redirect(url_for('purchase_orders'))

            cursor = conn.cursor()

            # Get form data
            po_no = request.form['po_no']
            po_date = request.form['po_date']
            vendor_code = request.form['vendor_code']
            remarks = request.form.get('remarks')

            # Insert purchase order header
            cursor.execute("""
                INSERT INTO purchase_order_head (company, po_no, po_date, vendor, remarks, active, created_by, updated)
                VALUES (1, %s, %s, %s, %s, true, 'admin', CURRENT_DATE)
            """, (po_no, po_date, vendor_code, remarks))

            # Get line items from form
            part_nums = request.form.getlist('part_num[]')
            quantities = request.form.getlist('quantity[]')
            rates = request.form.getlist('rate[]')

            # Insert line items
            for i, part_num in enumerate(part_nums):
                if part_num and quantities[i] and rates[i]:
                    quantity = float(quantities[i])
                    rate = float(rates[i])
                    amount = quantity * rate

                    cursor.execute("""
                        INSERT INTO purchase_order_tran (company, po_no, rowid, partnum, quantity, unit_price, amount, active, createdby, updated)
                        VALUES (1, %s, %s, %s, %s, %s, %s, true, 'admin', CURRENT_DATE)
                    """, (po_no, i+1, part_num, quantity, rate, amount))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Purchase Order created successfully!', 'success')
            return redirect(url_for('purchase_orders'))

        except Exception as e:
            flash(f'Error creating purchase order: {str(e)}', 'error')
            return redirect(url_for('purchase_orders'))

    # GET request - show form
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('purchase_orders'))

        cursor = conn.cursor()

        # Get vendors for dropdown
        cursor.execute("SELECT vendor_code, vendor_name FROM vendor WHERE active = true ORDER BY vendor_name")
        vendors = cursor.fetchall()

        # Get parts for dropdown
        cursor.execute("SELECT part_num, part_desc FROM part WHERE active = true ORDER BY part_desc")
        parts = cursor.fetchall()

        cursor.close()
        conn.close()

        # Generate next PO number
        next_po_no = get_next_po_number()

        return render_template('add_purchase_order.html', vendors=vendors, parts=parts, next_po_no=next_po_no)

    except Exception as e:
        flash(f'Error loading form: {str(e)}', 'error')
        return redirect(url_for('purchase_orders'))

@app.route('/purchase_orders/view/<int:po_no>')
def view_purchase_order(po_no):
    """View purchase order details"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('purchase_orders'))

        cursor = conn.cursor()

        # Get PO header
        cursor.execute("""
            SELECT poh.*, v.vendor_name, v.address1, v.city, v.state, v.phone, v.email
            FROM purchase_order_head poh
            LEFT JOIN vendor v ON poh.vendor = v.vendor_code AND poh.company = v.company
            WHERE poh.company = 1 AND poh.po_no = %s
        """, (po_no,))
        po_header = cursor.fetchone()

        if not po_header:
            flash('Purchase Order not found', 'error')
            return redirect(url_for('purchase_orders'))

        # Get PO line items
        cursor.execute("""
            SELECT pot.*, p.part_desc, u.unit_desc
            FROM purchase_order_tran pot
            LEFT JOIN part p ON pot.partnum = p.part_num AND pot.company = p.company
            LEFT JOIN unit u ON p.unit_id = u.unit_id AND p.company = u.company
            WHERE pot.company = 1 AND pot.po_no = %s AND pot.active = true
            ORDER BY pot.rowid
        """, (po_no,))
        po_lines = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('view_purchase_order.html', po_header=po_header, po_lines=po_lines)

    except Exception as e:
        flash(f'Error loading purchase order: {str(e)}', 'error')
        return redirect(url_for('purchase_orders'))

@app.route('/purchase_orders/edit/<int:po_no>', methods=['GET', 'POST'])
def edit_purchase_order(po_no):
    """Edit existing purchase order"""
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'error')
                return redirect(url_for('purchase_orders'))

            cursor = conn.cursor()

            # Get form data
            po_date = request.form['po_date']
            vendor_code = request.form['vendor_code']
            remarks = request.form.get('remarks')
            active = request.form.get('active') == 'on'

            # Update purchase order header
            cursor.execute("""
                UPDATE purchase_order_head
                SET po_date = %s, vendor = %s, remarks = %s, active = %s, updated = CURRENT_DATE
                WHERE company = 1 AND po_no = %s
            """, (po_date, vendor_code, remarks, active, po_no))

            # Delete existing line items
            cursor.execute("""
                UPDATE purchase_order_tran
                SET active = false, updated = CURRENT_DATE
                WHERE company = 1 AND po_no = %s
            """, (po_no,))

            # Get line items from form
            part_nums = request.form.getlist('part_num[]')
            quantities = request.form.getlist('quantity[]')
            rates = request.form.getlist('rate[]')

            # Insert updated line items
            for i, part_num in enumerate(part_nums):
                if part_num and quantities[i] and rates[i]:
                    quantity = float(quantities[i])
                    rate = float(rates[i])
                    amount = quantity * rate

                    cursor.execute("""
                        INSERT INTO purchase_order_tran (company, po_no, rowid, partnum, quantity, unit_price, amount, active, createdby, updated)
                        VALUES (1, %s, %s, %s, %s, %s, %s, true, 'admin', CURRENT_DATE)
                    """, (po_no, i+1, part_num, quantity, rate, amount))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Purchase Order updated successfully!', 'success')
            return redirect(url_for('purchase_orders'))

        except Exception as e:
            flash(f'Error updating purchase order: {str(e)}', 'error')
            return redirect(url_for('purchase_orders'))

    # GET request - show form with existing data
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('purchase_orders'))

        cursor = conn.cursor()

        # Get PO header
        cursor.execute("""
            SELECT * FROM purchase_order_head WHERE company = 1 AND po_no = %s
        """, (po_no,))
        po_header = cursor.fetchone()

        if not po_header:
            flash('Purchase Order not found', 'error')
            return redirect(url_for('purchase_orders'))

        # Get PO line items
        cursor.execute("""
            SELECT pot.*, p.part_desc
            FROM purchase_order_tran pot
            LEFT JOIN part p ON pot.partnum = p.part_num AND pot.company = p.company
            WHERE pot.company = 1 AND pot.po_no = %s AND pot.active = true
            ORDER BY pot.rowid
        """, (po_no,))
        po_lines = cursor.fetchall()

        # Get vendors for dropdown
        cursor.execute("SELECT vendor_code, vendor_name FROM vendor WHERE active = true ORDER BY vendor_name")
        vendors = cursor.fetchall()

        # Get parts for dropdown
        cursor.execute("SELECT part_num, part_desc FROM part WHERE active = true ORDER BY part_desc")
        parts = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('edit_purchase_order.html', po_header=po_header, po_lines=po_lines, vendors=vendors, parts=parts)

    except Exception as e:
        flash(f'Error loading purchase order: {str(e)}', 'error')
        return redirect(url_for('purchase_orders'))

@app.route('/purchase_orders/delete/<int:po_no>', methods=['POST'])
def delete_purchase_order(po_no):
    """Delete purchase order (soft delete)"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('purchase_orders'))

        cursor = conn.cursor()

        # Soft delete - set active to false for header and lines
        cursor.execute("""
            UPDATE purchase_order_head SET active = false, updated = CURRENT_DATE
            WHERE company = 1 AND po_no = %s
        """, (po_no,))

        cursor.execute("""
            UPDATE purchase_order_tran SET active = false, updated = CURRENT_DATE
            WHERE company = 1 AND po_no = %s
        """, (po_no,))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Purchase Order deleted successfully!', 'success')
        return redirect(url_for('purchase_orders'))

    except Exception as e:
        flash(f'Error deleting purchase order: {str(e)}', 'error')
        return redirect(url_for('purchase_orders'))

@app.route('/purchase_history')
def purchase_history():
    """View purchase history with filtering options"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('dashboard'))

        cursor = conn.cursor()

        # Get filter parameters
        vendor_filter = request.args.get('vendor', '')
        part_filter = request.args.get('part', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')

        # Build WHERE clause
        where_conditions = ["poh.company = 1", "pot.active = true"]
        params = []

        if vendor_filter:
            where_conditions.append("v.vendor_name ILIKE %s")
            params.append(f"%{vendor_filter}%")

        if part_filter:
            where_conditions.append("p.part_desc ILIKE %s")
            params.append(f"%{part_filter}%")

        if date_from:
            where_conditions.append("poh.po_date >= %s")
            params.append(date_from)

        if date_to:
            where_conditions.append("poh.po_date <= %s")
            params.append(date_to)

        where_clause = " AND ".join(where_conditions)

        # Get purchase history
        cursor.execute(f"""
            SELECT poh.po_no, poh.po_date, v.vendor_name, p.part_num, p.part_desc,
                   pot.quantity, pot.unit_price, pot.amount, u.unit_desc
            FROM purchase_order_tran pot
            JOIN purchase_order_head poh ON pot.po_no = poh.po_no AND pot.company = poh.company
            LEFT JOIN vendor v ON poh.vendor = v.vendor_code AND poh.company = v.company
            LEFT JOIN part p ON pot.partnum = p.part_num AND pot.company = p.company
            LEFT JOIN unit u ON p.unit_id = u.unit_id AND p.company = u.company
            WHERE {where_clause}
            ORDER BY poh.po_date DESC, poh.po_no DESC
            LIMIT 100
        """, params)
        purchase_data = cursor.fetchall()

        # Get summary statistics
        cursor.execute(f"""
            SELECT
                COUNT(DISTINCT poh.po_no) as total_pos,
                COUNT(*) as total_line_items,
                SUM(pot.quantity) as total_quantity,
                SUM(pot.amount) as total_value
            FROM purchase_order_tran pot
            JOIN purchase_order_head poh ON pot.po_no = poh.po_no AND pot.company = poh.company
            LEFT JOIN vendor v ON poh.vendor = v.vendor_code AND poh.company = v.company
            LEFT JOIN part p ON pot.partnum = p.part_num AND pot.company = p.company
            WHERE {where_clause}
        """, params)
        summary_stats = cursor.fetchone()

        # Get vendors for filter dropdown
        cursor.execute("SELECT vendor_code, vendor_name FROM vendor WHERE company = 1 AND active = true ORDER BY vendor_name")
        vendors = cursor.fetchall()

        # Get parts for filter dropdown
        cursor.execute("SELECT part_num, part_desc FROM part WHERE company = 1 AND active = true ORDER BY part_desc")
        parts = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('purchase_history.html',
                             purchase_data=purchase_data,
                             summary_stats=summary_stats,
                             vendors=vendors,
                             parts=parts,
                             filters={
                                 'vendor': vendor_filter,
                                 'part': part_filter,
                                 'date_from': date_from,
                                 'date_to': date_to
                             })

    except Exception as e:
        flash(f'Error loading purchase history: {str(e)}', 'error')
        return redirect(url_for('purchase_orders'))

# Sales Invoice Routes
@app.route('/sales_invoices')
def sales_invoices():
    """Sales invoices management page"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return render_template('error.html', message='Database connection failed')

        cursor = conn.cursor()

        # Get all sales invoices with customer information
        cursor.execute("""
            SELECT sih.inv_no, sih.inv_dt, c.customer_name, sih.active,
                   COUNT(CASE WHEN sit.active = true THEN sit.rowid END) as line_items,
                   SUM(CASE WHEN sit.active = true THEN sit.amount ELSE 0 END) as total_amount
            FROM sales_invoice_head sih
            LEFT JOIN customer c ON sih.customer = c.customer_code AND sih.company = c.company
            LEFT JOIN sales_invoice_tran sit ON sih.inv_no = sit.inv_no AND sih.company = sit.company
            WHERE sih.company = 1
            GROUP BY sih.inv_no, sih.inv_dt, c.customer_name, sih.active
            ORDER BY sih.inv_dt DESC
        """)

        invoices_data = cursor.fetchall()
        cursor.close()
        conn.close()

        return render_template('sales_invoices.html', sales_invoices=invoices_data)

    except Exception as e:
        flash(f'Error loading sales invoices: {str(e)}', 'error')
        return render_template('error.html', message=str(e))

# Sales Invoice CRUD Operations
@app.route('/sales_invoices/add', methods=['GET', 'POST'])
def add_sales_invoice():
    """Add new sales invoice"""
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'error')
                return redirect(url_for('sales_invoices'))

            cursor = conn.cursor()

            # Get form data
            inv_no = request.form['inv_no']
            inv_dt = request.form['inv_dt']
            customer_code = request.form['customer_code']
            remarks = request.form.get('remarks')

            # Insert sales invoice header
            cursor.execute("""
                INSERT INTO sales_invoice_head (company, inv_no, inv_dt, customer, remarks, active, created_by, updated)
                VALUES (1, %s, %s, %s, %s, true, 'admin', CURRENT_DATE)
            """, (inv_no, inv_dt, customer_code, remarks))

            # Get line items from form
            part_nums = request.form.getlist('part_num[]')
            quantities = request.form.getlist('quantity[]')
            rates = request.form.getlist('rate[]')

            # Insert line items
            for i, part_num in enumerate(part_nums):
                if part_num and quantities[i] and rates[i]:
                    quantity = float(quantities[i])
                    rate = float(rates[i])
                    amount = quantity * rate

                    cursor.execute("""
                        INSERT INTO sales_invoice_tran (company, inv_no, rowid, partnum, quantity, unit_price, amount, active, createdby, updated)
                        VALUES (1, %s, %s, %s, %s, %s, %s, true, 'admin', CURRENT_DATE)
                    """, (inv_no, i+1, part_num, quantity, rate, amount))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Sales Invoice created successfully!', 'success')
            return redirect(url_for('sales_invoices'))

        except Exception as e:
            flash(f'Error creating sales invoice: {str(e)}', 'error')
            return redirect(url_for('sales_invoices'))

    # GET request - show form
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('sales_invoices'))

        cursor = conn.cursor()

        # Get customers for dropdown
        cursor.execute("SELECT customer_code, customer_name FROM customer WHERE active = true ORDER BY customer_name")
        customers = cursor.fetchall()

        # Get parts for dropdown
        cursor.execute("SELECT part_num, part_desc FROM part WHERE active = true ORDER BY part_desc")
        parts = cursor.fetchall()

        cursor.close()
        conn.close()

        # Generate next invoice number
        next_inv_no = get_next_invoice_number()

        return render_template('add_sales_invoice.html', customers=customers, parts=parts, next_inv_no=next_inv_no)

    except Exception as e:
        flash(f'Error loading form: {str(e)}', 'error')
        return redirect(url_for('sales_invoices'))

@app.route('/sales_invoices/view/<int:inv_no>')
def view_sales_invoice(inv_no):
    """View sales invoice details"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('sales_invoices'))

        cursor = conn.cursor()

        # Get invoice header
        cursor.execute("""
            SELECT sih.*, c.customer_name, c.address1, c.city, c.state, c.phone, c.email
            FROM sales_invoice_head sih
            LEFT JOIN customer c ON sih.customer = c.customer_code AND sih.company = c.company
            WHERE sih.company = 1 AND sih.inv_no = %s
        """, (inv_no,))
        invoice_header = cursor.fetchone()

        if not invoice_header:
            flash('Sales Invoice not found', 'error')
            return redirect(url_for('sales_invoices'))

        # Get invoice line items
        cursor.execute("""
            SELECT sit.*, p.part_desc, u.unit_desc
            FROM sales_invoice_tran sit
            LEFT JOIN part p ON sit.partnum = p.part_num AND sit.company = p.company
            LEFT JOIN unit u ON p.unit_id = u.unit_id AND p.company = u.company
            WHERE sit.company = 1 AND sit.inv_no = %s AND sit.active = true
            ORDER BY sit.rowid
        """, (inv_no,))
        invoice_lines = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('view_sales_invoice.html', invoice_header=invoice_header, invoice_lines=invoice_lines)

    except Exception as e:
        flash(f'Error loading sales invoice: {str(e)}', 'error')
        return redirect(url_for('sales_invoices'))

@app.route('/sales_invoices/edit/<int:inv_no>', methods=['GET', 'POST'])
def edit_sales_invoice(inv_no):
    """Edit existing sales invoice"""
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'error')
                return redirect(url_for('sales_invoices'))

            cursor = conn.cursor()

            # Get form data
            inv_dt = request.form['inv_dt']
            customer_code = request.form['customer_code']
            remarks = request.form.get('remarks')
            active = request.form.get('active') == 'on'

            # Update sales invoice header
            cursor.execute("""
                UPDATE sales_invoice_head
                SET inv_dt = %s, customer = %s, remarks = %s, active = %s, updated = CURRENT_DATE
                WHERE company = 1 AND inv_no = %s
            """, (inv_dt, customer_code, remarks, active, inv_no))

            # Delete existing line items
            cursor.execute("""
                UPDATE sales_invoice_tran
                SET active = false, updated = CURRENT_DATE
                WHERE company = 1 AND inv_no = %s
            """, (inv_no,))

            # Get line items from form
            part_nums = request.form.getlist('part_num[]')
            quantities = request.form.getlist('quantity[]')
            rates = request.form.getlist('rate[]')

            # Insert updated line items
            for i, part_num in enumerate(part_nums):
                if part_num and quantities[i] and rates[i]:
                    quantity = float(quantities[i])
                    rate = float(rates[i])
                    amount = quantity * rate

                    cursor.execute("""
                        INSERT INTO sales_invoice_tran (company, inv_no, rowid, partnum, quantity, unit_price, amount, active, createdby, updated)
                        VALUES (1, %s, %s, %s, %s, %s, %s, true, 'admin', CURRENT_DATE)
                    """, (inv_no, i+1, part_num, quantity, rate, amount))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Sales Invoice updated successfully!', 'success')
            return redirect(url_for('sales_invoices'))

        except Exception as e:
            flash(f'Error updating sales invoice: {str(e)}', 'error')
            return redirect(url_for('sales_invoices'))

    # GET request - show form with existing data
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('sales_invoices'))

        cursor = conn.cursor()

        # Get invoice header
        cursor.execute("""
            SELECT * FROM sales_invoice_head WHERE company = 1 AND inv_no = %s
        """, (inv_no,))
        invoice_header = cursor.fetchone()

        if not invoice_header:
            flash('Sales Invoice not found', 'error')
            return redirect(url_for('sales_invoices'))

        # Get invoice line items
        cursor.execute("""
            SELECT sit.*, p.part_desc
            FROM sales_invoice_tran sit
            LEFT JOIN part p ON sit.partnum = p.part_num AND sit.company = p.company
            WHERE sit.company = 1 AND sit.inv_no = %s AND sit.active = true
            ORDER BY sit.rowid
        """, (inv_no,))
        invoice_lines = cursor.fetchall()

        # Get customers for dropdown
        cursor.execute("SELECT customer_code, customer_name FROM customer WHERE active = true ORDER BY customer_name")
        customers = cursor.fetchall()

        # Get parts for dropdown
        cursor.execute("SELECT part_num, part_desc FROM part WHERE active = true ORDER BY part_desc")
        parts = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('edit_sales_invoice.html', invoice_header=invoice_header, invoice_lines=invoice_lines, customers=customers, parts=parts)

    except Exception as e:
        flash(f'Error loading sales invoice: {str(e)}', 'error')
        return redirect(url_for('sales_invoices'))

@app.route('/sales_invoices/delete/<int:inv_no>', methods=['POST'])
def delete_sales_invoice(inv_no):
    """Delete sales invoice (soft delete)"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('sales_invoices'))

        cursor = conn.cursor()

        # Soft delete - set active to false for header and lines
        cursor.execute("""
            UPDATE sales_invoice_head SET active = false, updated = CURRENT_DATE
            WHERE company = 1 AND inv_no = %s
        """, (inv_no,))

        cursor.execute("""
            UPDATE sales_invoice_tran SET active = false, updated = CURRENT_DATE
            WHERE company = 1 AND inv_no = %s
        """, (inv_no,))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Sales Invoice deleted successfully!', 'success')
        return redirect(url_for('sales_invoices'))

    except Exception as e:
        flash(f'Error deleting sales invoice: {str(e)}', 'error')
        return redirect(url_for('sales_invoices'))

@app.route('/sales_history')
def sales_history():
    """View sales history with filtering options"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('dashboard'))

        cursor = conn.cursor()

        # Get filter parameters
        customer_filter = request.args.get('customer', '')
        part_filter = request.args.get('part', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')

        # Build WHERE clause
        where_conditions = ["sih.company = 1", "sit.active = true"]
        params = []

        if customer_filter:
            where_conditions.append("c.customer_name ILIKE %s")
            params.append(f"%{customer_filter}%")

        if part_filter:
            where_conditions.append("p.part_desc ILIKE %s")
            params.append(f"%{part_filter}%")

        if date_from:
            where_conditions.append("sih.inv_dt >= %s")
            params.append(date_from)

        if date_to:
            where_conditions.append("sih.inv_dt <= %s")
            params.append(date_to)

        where_clause = " AND ".join(where_conditions)

        # Get sales history
        cursor.execute(f"""
            SELECT sih.inv_no, sih.inv_dt, c.customer_name, p.part_num, p.part_desc,
                   sit.quantity, sit.unit_price, sit.amount, u.unit_desc
            FROM sales_invoice_tran sit
            JOIN sales_invoice_head sih ON sit.inv_no = sih.inv_no AND sit.company = sih.company
            LEFT JOIN customer c ON sih.customer = c.customer_code AND sih.company = c.company
            LEFT JOIN part p ON sit.partnum = p.part_num AND sit.company = p.company
            LEFT JOIN unit u ON p.unit_id = u.unit_id AND p.company = u.company
            WHERE {where_clause}
            ORDER BY sih.inv_dt DESC, sih.inv_no DESC
            LIMIT 100
        """, params)
        sales_data = cursor.fetchall()

        # Get summary statistics
        cursor.execute(f"""
            SELECT
                COUNT(DISTINCT sih.inv_no) as total_invoices,
                COUNT(*) as total_line_items,
                SUM(sit.quantity) as total_quantity,
                SUM(sit.amount) as total_value
            FROM sales_invoice_tran sit
            JOIN sales_invoice_head sih ON sit.inv_no = sih.inv_no AND sit.company = sih.company
            LEFT JOIN customer c ON sih.customer = c.customer_code AND sih.company = c.company
            LEFT JOIN part p ON sit.partnum = p.part_num AND sit.company = p.company
            WHERE {where_clause}
        """, params)
        summary_stats = cursor.fetchone()

        # Get customers for filter dropdown
        cursor.execute("SELECT customer_code, customer_name FROM customer WHERE company = 1 AND active = true ORDER BY customer_name")
        customers = cursor.fetchall()

        # Get parts for filter dropdown
        cursor.execute("SELECT part_num, part_desc FROM part WHERE company = 1 AND active = true ORDER BY part_desc")
        parts = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('sales_history.html',
                             sales_data=sales_data,
                             summary_stats=summary_stats,
                             customers=customers,
                             parts=parts,
                             filters={
                                 'customer': customer_filter,
                                 'part': part_filter,
                                 'date_from': date_from,
                                 'date_to': date_to
                             })

    except Exception as e:
        flash(f'Error loading sales history: {str(e)}', 'error')
        return redirect(url_for('sales_invoices'))

# Stock Management Routes
@app.route('/stock_management')
def stock_management():
    """Stock management page"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return render_template('error.html', message='Database connection failed')

        cursor = conn.cursor()

        # Get stock information with proper stock calculation
        cursor.execute("""
            SELECT p.part_num, p.part_desc, p.part_category, u.unit_desc,
                   COALESCE(stock_summary.current_stock, 0) as current_stock,
                   0 as reserved_stock,
                   COALESCE(stock_summary.current_stock, 0) as available_stock,
                   p.pur_price, p.sell_price
            FROM part p
            LEFT JOIN unit u ON p.unit_id = u.unit_id AND p.company = u.company
            LEFT JOIN (
                SELECT part_num,
                       SUM(CASE WHEN type = 'IN' THEN qty ELSE -qty END) as current_stock
                FROM stock_update
                WHERE company = 1 AND part_num IS NOT NULL
                GROUP BY part_num
            ) stock_summary ON p.part_num = stock_summary.part_num
            WHERE p.active = true AND p.company = 1
            ORDER BY p.part_desc
        """)

        stock_data = cursor.fetchall()
        cursor.close()
        conn.close()

        return render_template('stock_management.html', stock_data=stock_data)

    except Exception as e:
        flash(f'Error loading stock data: {str(e)}', 'error')
        return render_template('error.html', message=str(e))

@app.route('/stock_update', methods=['GET', 'POST'])
def stock_update():
    """Stock update page"""
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'error')
                return redirect(url_for('stock_management'))

            cursor = conn.cursor()

            # Get form data
            part_num = request.form['part_num']
            update_type = request.form['update_type']  # IN or OUT
            quantity = float(request.form['quantity'])
            remarks = request.form.get('remarks')

            # Insert stock update with part_num
            cursor.execute("""
                INSERT INTO stock_update (company, update_id, part_num, type, qty,
                                        update_date, created_by, updated)
                VALUES (1, (SELECT COALESCE(MAX(update_id), 0) + 1 FROM stock_update WHERE company = 1),
                        %s, %s, %s, CURRENT_DATE, 'admin', CURRENT_DATE)
            """, (part_num, update_type, quantity))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Stock updated successfully!', 'success')
            return redirect(url_for('stock_management'))

        except Exception as e:
            flash(f'Error updating stock: {str(e)}', 'error')
            return redirect(url_for('stock_management'))

    # GET request - show form
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('stock_management'))

        cursor = conn.cursor()

        # Get parts for dropdown
        cursor.execute("SELECT part_num, part_desc FROM part WHERE active = true ORDER BY part_desc")
        parts = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('stock_update.html', parts=parts)

    except Exception as e:
        flash(f'Error loading form: {str(e)}', 'error')
        return redirect(url_for('stock_management'))

# ===== INDENT MANAGEMENT ROUTES =====

@app.route('/indents')
def indents():
    """Indent management page"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return render_template('error.html', message='Database connection failed')

        cursor = conn.cursor()

        # Get summary statistics
        cursor.execute("SELECT COUNT(*) FROM indent_request_head WHERE active = true")
        total_indents = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM indent_request_head WHERE active = true AND status = 'PENDING'")
        pending_indents = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM indent_request_head WHERE active = true AND status = 'APPROVED'")
        approved_indents = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM indent_request_head WHERE active = true AND status = 'REJECTED'")
        rejected_indents = cursor.fetchone()[0]

        # Get all indents
        cursor.execute("""
            SELECT irh.indent_id, irh.indent_dt, irh.department, irh.requested_by,
                   irh.status, irh.active,
                   COUNT(irt.rowid) as line_items
            FROM indent_request_head irh
            LEFT JOIN indent_request_tran irt ON irh.indent_id = irt.indent_id AND irh.company = irt.company AND irt.active = true
            WHERE irh.company = 1
            GROUP BY irh.indent_id, irh.indent_dt, irh.department, irh.requested_by, irh.status, irh.active
            ORDER BY irh.indent_dt DESC
        """)

        indents_data = cursor.fetchall()

        stats = {
            'total_indents': total_indents,
            'pending_indents': pending_indents,
            'approved_indents': approved_indents,
            'rejected_indents': rejected_indents
        }

        cursor.close()
        conn.close()

        return render_template('indents.html', indents=indents_data, stats=stats)

    except Exception as e:
        flash(f'Error loading indents: {str(e)}', 'error')
        return render_template('error.html', message=str(e))

@app.route('/indents/add')
def add_indent():
    """Add new indent page"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('indents'))

        cursor = conn.cursor()

        # Get parts for dropdown
        cursor.execute("SELECT part_num, part_desc FROM part WHERE active = true ORDER BY part_desc")
        parts = cursor.fetchall()

        cursor.close()
        conn.close()

        # Generate next indent number
        next_indent_no = get_next_indent_number()

        # Get current date
        from datetime import date
        current_date = date.today().strftime('%Y-%m-%d')

        return render_template('add_indent.html',
                             parts=parts,
                             next_indent_no=next_indent_no,
                             current_date=current_date)

    except Exception as e:
        flash(f'Error loading add indent page: {str(e)}', 'error')
        return redirect(url_for('indents'))

@app.route('/indents/view/<int:indent_id>')
def view_indent(indent_id):
    """View indent details"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('indents'))

        cursor = conn.cursor()

        # Get indent details
        cursor.execute("""
            SELECT company, indent_id, indent_dt, department, requested_by,
                   status, remarks, active, created, updated
            FROM indent_request_head WHERE company = 1 AND indent_id = %s
        """, (indent_id,))
        indent_details = cursor.fetchone()

        if not indent_details:
            flash('Indent not found', 'error')
            return redirect(url_for('indents'))

        # Get indent line items
        cursor.execute("""
            SELECT irt.rowid, irt.partnum, irt.part_desc, irt.quantity,
                   irt.required_date, irt.remarks, irt.active
            FROM indent_request_tran irt
            WHERE irt.company = 1 AND irt.indent_id = %s AND irt.active = true
            ORDER BY irt.rowid
        """, (indent_id,))
        indent_items = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('view_indent.html',
                             indent_details=indent_details,
                             indent_items=indent_items)

    except Exception as e:
        flash(f'Error loading indent details: {str(e)}', 'error')
        return redirect(url_for('indents'))

@app.route('/indents/create', methods=['POST'])
def create_indent():
    """Create new indent"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('indents'))

        cursor = conn.cursor()

        # Get form data
        indent_id = request.form.get('indent_id')
        indent_dt = request.form.get('indent_dt')
        department = request.form.get('department')
        requested_by = request.form.get('requested_by')
        remarks = request.form.get('remarks', '')

        # Get line items
        part_nums = request.form.getlist('part_num[]')
        part_descs = request.form.getlist('part_desc[]')
        quantities = request.form.getlist('quantity[]')
        required_dates = request.form.getlist('required_date[]')
        item_remarks = request.form.getlist('item_remarks[]')

        # Validate at least one item
        valid_items = []
        for i in range(len(part_nums)):
            if part_nums[i] and quantities[i] and float(quantities[i]) > 0:
                valid_items.append(i)

        if not valid_items:
            flash('Please add at least one valid item', 'error')
            return redirect(url_for('add_indent'))

        # Insert indent header
        cursor.execute("""
            INSERT INTO indent_request_head
            (company, indent_id, indent_dt, department, requested_by, status, remarks, active, created, updated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (1, indent_id, indent_dt, department, requested_by, 'PENDING', remarks, True, datetime.now(), datetime.now()))

        # Insert line items
        for i in valid_items:
            cursor.execute("""
                INSERT INTO indent_request_tran
                (company, indent_id, rowid, partnum, part_desc, quantity, required_date, remarks, active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (1, indent_id, i + 1, int(part_nums[i]), part_descs[i], float(quantities[i]),
                  required_dates[i] if required_dates[i] else None, item_remarks[i], True))

        conn.commit()
        cursor.close()
        conn.close()

        flash(f'Indent {indent_id} created successfully!', 'success')
        return redirect(url_for('indents'))

    except Exception as e:
        flash(f'Error creating indent: {str(e)}', 'error')
        return redirect(url_for('add_indent'))

@app.route('/indents/approve/<int:indent_id>', methods=['POST'])
def approve_indent(indent_id):
    """Approve indent request"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'})

        cursor = conn.cursor()

        # Update indent status to APPROVED
        cursor.execute("""
            UPDATE indent_request_head
            SET status = 'APPROVED', updated = %s
            WHERE company = 1 AND indent_id = %s
        """, (datetime.now(), indent_id))

        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': 'Indent not found'})

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Indent approved successfully'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/indents/reject/<int:indent_id>', methods=['POST'])
def reject_indent(indent_id):
    """Reject indent request"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'})

        cursor = conn.cursor()

        # Update indent status to REJECTED
        cursor.execute("""
            UPDATE indent_request_head
            SET status = 'REJECTED', updated = %s
            WHERE company = 1 AND indent_id = %s
        """, (datetime.now(), indent_id))

        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': 'Indent not found'})

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Indent rejected successfully'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/indents/edit/<int:indent_id>')
def edit_indent(indent_id):
    """Edit indent page"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('indents'))

        cursor = conn.cursor()

        # Get indent details
        cursor.execute("""
            SELECT company, indent_id, indent_dt, department, requested_by,
                   status, remarks, active, created, updated
            FROM indent_request_head WHERE company = 1 AND indent_id = %s
        """, (indent_id,))
        indent_details = cursor.fetchone()

        if not indent_details:
            flash('Indent not found', 'error')
            return redirect(url_for('indents'))

        # Check if indent can be edited (only PENDING indents can be edited)
        if indent_details[5] != 'PENDING':
            flash('Only pending indents can be edited', 'error')
            return redirect(url_for('view_indent', indent_id=indent_id))

        # Get indent line items
        cursor.execute("""
            SELECT irt.rowid, irt.partnum, irt.part_desc, irt.quantity,
                   irt.required_date, irt.remarks, irt.active
            FROM indent_request_tran irt
            WHERE irt.company = 1 AND irt.indent_id = %s AND irt.active = true
            ORDER BY irt.rowid
        """, (indent_id,))
        indent_items = cursor.fetchall()

        # Get parts for dropdown
        cursor.execute("SELECT part_num, part_desc FROM part WHERE active = true ORDER BY part_desc")
        parts = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('edit_indent.html',
                             indent_details=indent_details,
                             indent_items=indent_items,
                             parts=parts)

    except Exception as e:
        flash(f'Error loading indent for editing: {str(e)}', 'error')
        return redirect(url_for('indents'))

@app.route('/indents/update/<int:indent_id>', methods=['POST'])
def update_indent(indent_id):
    """Update existing indent"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('indents'))

        cursor = conn.cursor()

        # Check if indent exists and is pending
        cursor.execute("""
            SELECT status FROM indent_request_head
            WHERE company = 1 AND indent_id = %s
        """, (indent_id,))
        result = cursor.fetchone()

        if not result:
            flash('Indent not found', 'error')
            return redirect(url_for('indents'))

        if result[0] != 'PENDING':
            flash('Only pending indents can be updated', 'error')
            return redirect(url_for('view_indent', indent_id=indent_id))

        # Get form data
        indent_dt = request.form.get('indent_dt')
        department = request.form.get('department')
        requested_by = request.form.get('requested_by')
        remarks = request.form.get('remarks')

        # Get line items
        part_nums = request.form.getlist('part_num[]')
        part_descs = request.form.getlist('part_desc[]')
        quantities = request.form.getlist('quantity[]')
        required_dates = request.form.getlist('required_date[]')
        item_remarks = request.form.getlist('item_remarks[]')

        # Validate line items
        valid_items = []
        for i in range(len(part_nums)):
            if part_nums[i] and quantities[i] and float(quantities[i]) > 0:
                valid_items.append(i)

        if not valid_items:
            flash('Please add at least one valid item', 'error')
            return redirect(url_for('edit_indent', indent_id=indent_id))

        # Update indent header
        cursor.execute("""
            UPDATE indent_request_head
            SET indent_dt = %s, department = %s, requested_by = %s,
                remarks = %s, updated = %s
            WHERE company = 1 AND indent_id = %s
        """, (indent_dt, department, requested_by, remarks, datetime.now(), indent_id))

        # Delete existing line items
        cursor.execute("""
            UPDATE indent_request_tran
            SET active = false
            WHERE company = 1 AND indent_id = %s
        """, (indent_id,))

        # Insert updated line items
        for i in valid_items:
            cursor.execute("""
                INSERT INTO indent_request_tran
                (company, indent_id, rowid, partnum, part_desc, quantity, required_date, remarks, active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (1, indent_id, i + 1, int(part_nums[i]), part_descs[i], float(quantities[i]),
                  required_dates[i] if required_dates[i] else None, item_remarks[i], True))

        conn.commit()
        cursor.close()
        conn.close()

        flash(f'Indent {indent_id} updated successfully!', 'success')
        return redirect(url_for('view_indent', indent_id=indent_id))

    except Exception as e:
        flash(f'Error updating indent: {str(e)}', 'error')
        return redirect(url_for('edit_indent', indent_id=indent_id))

# ===== API ENDPOINTS =====

@app.route('/api/part/<int:part_num>')
def get_part_details(part_num):
    """Get part details including tax percentage"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()

        # Get part details including tax percentage
        cursor.execute("""
            SELECT p.part_num, p.part_desc, p.pur_price, p.sell_price,
                   p.tax_percent, p.unit_id, u.unit_desc
            FROM part p
            LEFT JOIN unit u ON p.unit_id = u.unit_id
            WHERE p.company = 1 AND p.part_num = %s AND p.active = true
        """, (part_num,))

        part = cursor.fetchone()
        cursor.close()
        conn.close()

        if not part:
            return jsonify({'error': 'Part not found'}), 404

        return jsonify({
            'part_num': part[0],
            'part_desc': part[1],
            'pur_price': float(part[2]) if part[2] else 0,
            'sell_price': float(part[3]) if part[3] else 0,
            'tax_percent': float(part[4]) if part[4] else 0,
            'unit_id': part[5],
            'unit_desc': part[6] if part[6] else ''
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Reports Routes
@app.route('/reports')
def reports():
    """Reports dashboard"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return render_template('error.html', message='Database connection failed')

        cursor = conn.cursor()

        # Get report statistics
        stats = {}

        # Parts summary
        cursor.execute("SELECT COUNT(*) FROM part WHERE active = true")
        stats['total_parts'] = cursor.fetchone()[0]

        # Vendors summary
        cursor.execute("SELECT COUNT(*) FROM vendor WHERE active = true")
        stats['total_vendors'] = cursor.fetchone()[0]

        # Customers summary
        cursor.execute("SELECT COUNT(*) FROM customer WHERE active = true")
        stats['total_customers'] = cursor.fetchone()[0]

        # Purchase orders summary
        cursor.execute("SELECT COUNT(*) FROM purchase_order_head WHERE active = true")
        stats['total_pos'] = cursor.fetchone()[0]

        # Sales invoices summary
        cursor.execute("SELECT COUNT(*) FROM sales_invoice_head WHERE active = true")
        stats['total_invoices'] = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return render_template('reports.html', stats=stats)

    except Exception as e:
        flash(f'Error loading reports: {str(e)}', 'error')
        return render_template('error.html', message=str(e))

@app.route('/reports/parts')
def parts_report():
    """Parts report"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('reports'))

        cursor = conn.cursor()

        # Get detailed parts report
        cursor.execute("""
            SELECT p.part_num, p.part_desc, p.part_type, p.part_category,
                   u.unit_desc, p.pur_price, p.sell_price, p.hsn_code,
                   t.tax_desc, p.tax_percent, p.active
            FROM part p
            LEFT JOIN unit u ON p.unit_id = u.unit_id AND p.company = u.company
            LEFT JOIN tax t ON p.tax_id = t.tax_id AND p.company = t.company
            WHERE p.company = 1
            ORDER BY p.part_category, p.part_desc
        """)

        parts_data = cursor.fetchall()
        cursor.close()
        conn.close()

        return render_template('parts_report.html', parts_data=parts_data)

    except Exception as e:
        flash(f'Error loading parts report: {str(e)}', 'error')
        return redirect(url_for('reports'))

# Enhanced Stock Management with proper tracking
@app.route('/stock_history/<int:part_num>')
def stock_history(part_num):
    """View stock history for a specific part"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('stock_management'))

        cursor = conn.cursor()

        # Get part details
        cursor.execute("""
            SELECT p.part_num, p.part_desc, p.part_category, u.unit_desc
            FROM part p
            LEFT JOIN unit u ON p.unit_id = u.unit_id AND p.company = u.company
            WHERE p.company = 1 AND p.part_num = %s
        """, (part_num,))
        part_details = cursor.fetchone()

        if not part_details:
            flash('Part not found', 'error')
            return redirect(url_for('stock_management'))

        # Get stock history (simulated data for now)
        stock_history = [
            {
                'date': '2024-01-15',
                'type': 'IN',
                'quantity': 100,
                'reference': 'PO-001',
                'remarks': 'Initial stock'
            },
            {
                'date': '2024-01-20',
                'type': 'OUT',
                'quantity': 25,
                'reference': 'INV-001',
                'remarks': 'Sales order'
            },
            {
                'date': '2024-01-25',
                'type': 'IN',
                'quantity': 50,
                'reference': 'PO-002',
                'remarks': 'Restock'
            }
        ]

        cursor.close()
        conn.close()

        return render_template('stock_history.html', part_details=part_details, stock_history=stock_history)

    except Exception as e:
        flash(f'Error loading stock history: {str(e)}', 'error')
        return redirect(url_for('stock_management'))

@app.route('/stock_adjustment', methods=['GET', 'POST'])
def stock_adjustment():
    """Stock adjustment for corrections"""
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'error')
                return redirect(url_for('stock_management'))

            cursor = conn.cursor()

            # Get form data
            part_num = request.form['part_num']
            adjustment_type = request.form['adjustment_type']  # INCREASE or DECREASE
            quantity = float(request.form['quantity'])
            reason = request.form.get('reason')
            remarks = request.form.get('remarks')

            # Insert stock adjustment record
            cursor.execute("""
                INSERT INTO stock_update (company, update_id, part_num, type, qty,
                                        update_date, created_by, updated)
                VALUES (1, (SELECT COALESCE(MAX(update_id), 0) + 1 FROM stock_update WHERE company = 1),
                        %s, %s, %s, CURRENT_DATE, 'admin', CURRENT_DATE)
            """, (part_num, adjustment_type, quantity))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Stock adjustment completed successfully!', 'success')
            return redirect(url_for('stock_management'))

        except Exception as e:
            flash(f'Error processing stock adjustment: {str(e)}', 'error')
            return redirect(url_for('stock_management'))

    # GET request - show form
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('stock_management'))

        cursor = conn.cursor()

        # Get parts for dropdown
        cursor.execute("SELECT part_num, part_desc FROM part WHERE active = true ORDER BY part_desc")
        parts = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('stock_adjustment.html', parts=parts)

    except Exception as e:
        flash(f'Error loading form: {str(e)}', 'error')
        return redirect(url_for('stock_management'))

@app.route('/grn')
def grn_management():
    """GRN management page"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return render_template('error.html', message='Database connection failed')

        cursor = conn.cursor()

        # Get all GRNs with vendor and PO information
        cursor.execute("""
            SELECT grh.grn_no, grh.grn_dt, grh.po_no, v.vendor_name, grh.active,
                   COUNT(CASE WHEN grt.active = true THEN grt.rowid END) as line_items,
                   SUM(CASE WHEN grt.active = true THEN grt.amount ELSE 0 END) as total_amount
            FROM goods_receipt_head grh
            LEFT JOIN vendor v ON grh.vendor = v.vendor_code AND grh.company = v.company
            LEFT JOIN goods_receipt_tran grt ON grh.grn_no = grt.grn_no AND grh.company = grt.company
            WHERE grh.company = 1
            GROUP BY grh.grn_no, grh.grn_dt, grh.po_no, v.vendor_name, grh.active
            ORDER BY grh.grn_dt DESC
        """)

        grn_data = cursor.fetchall()

        # Get summary statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_grns,
                COUNT(CASE WHEN grh.active = true THEN 1 END) as active_grns,
                SUM(CASE WHEN grt.active = true THEN grt.amount ELSE 0 END) as total_value,
                COUNT(DISTINCT grh.vendor) as unique_vendors
            FROM goods_receipt_head grh
            LEFT JOIN goods_receipt_tran grt ON grh.grn_no = grt.grn_no AND grh.company = grt.company
            WHERE grh.company = 1
        """)
        summary_stats = cursor.fetchone()

        cursor.close()
        conn.close()

        return render_template('grn_management.html', grns=grn_data, stats=summary_stats)

    except Exception as e:
        flash(f'Error loading GRNs: {str(e)}', 'error')
        return render_template('error.html', message=str(e))

@app.route('/grn/create/<int:po_no>', methods=['GET', 'POST'])
def create_grn(po_no):
    """Create Goods Receipt Note from Purchase Order"""
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed', 'error')
                return redirect(url_for('purchase_orders'))

            cursor = conn.cursor()

            # Get form data
            grn_date = request.form['grn_date']
            remarks = request.form.get('remarks')

            # Get next GRN number
            cursor.execute("SELECT COALESCE(MAX(grn_no), 0) + 1 FROM goods_receipt_head WHERE company = 1")
            grn_no = cursor.fetchone()[0]

            # Get PO details
            cursor.execute("""
                SELECT vendor FROM purchase_order_head WHERE company = 1 AND po_no = %s
            """, (po_no,))
            po_details = cursor.fetchone()

            if not po_details:
                flash('Purchase Order not found', 'error')
                return redirect(url_for('purchase_orders'))

            # Create GRN header
            cursor.execute("""
                INSERT INTO goods_receipt_head (company, grn_no, grn_dt, po_no, vendor,
                                              active, created_by, updated)
                VALUES (1, %s, %s, %s, %s, true, 'admin', CURRENT_DATE)
            """, (grn_no, grn_date, po_no, po_details[0]))

            # Get line items from form
            part_nums = request.form.getlist('part_num[]')
            received_qtys = request.form.getlist('received_qty[]')
            rates = request.form.getlist('rate[]')

            # Insert GRN line items and update stock
            for i, part_num in enumerate(part_nums):
                if part_num and received_qtys[i] and rates[i]:
                    received_qty = float(received_qtys[i])
                    rate = float(rates[i])
                    amount = received_qty * rate

                    # Insert GRN line item
                    cursor.execute("""
                        INSERT INTO goods_receipt_tran (company, grn_no, rowid, partnum, quantity,
                                                      unit_price, amount, active, createdby, updated)
                        VALUES (1, %s, %s, %s, %s, %s, %s, true, 'admin', CURRENT_DATE)
                    """, (grn_no, i+1, part_num, received_qty, rate, amount))

                    # Update stock
                    cursor.execute("""
                        INSERT INTO stock_update (company, update_id, part_num, type, qty,
                                                update_date, created_by, updated)
                        VALUES (1, (SELECT COALESCE(MAX(update_id), 0) + 1 FROM stock_update WHERE company = 1),
                                %s, 'IN', %s, %s, 'admin', CURRENT_DATE)
                    """, (part_num, received_qty, grn_date))

            conn.commit()
            cursor.close()
            conn.close()

            flash(f'GRN {grn_no} created successfully and stock updated!', 'success')
            return redirect(url_for('grn_management'))

        except Exception as e:
            flash(f'Error creating GRN: {str(e)}', 'error')
            return redirect(url_for('grn_management'))

    # GET request - show form
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('purchase_orders'))

        cursor = conn.cursor()

        # Get PO details with line items
        cursor.execute("""
            SELECT poh.po_no, poh.po_date, v.vendor_name, poh.vendor
            FROM purchase_order_head poh
            LEFT JOIN vendor v ON poh.vendor = v.vendor_code AND poh.company = v.company
            WHERE poh.company = 1 AND poh.po_no = %s
        """, (po_no,))
        po_header = cursor.fetchone()

        if not po_header:
            flash('Purchase Order not found', 'error')
            return redirect(url_for('purchase_orders'))

        # Get PO line items with pending quantities
        cursor.execute("""
            SELECT pot.partnum, p.part_desc, pot.quantity, pot.unit_price, pot.amount,
                   u.unit_desc,
                   COALESCE(grn_received.total_received, 0) as already_received,
                   (pot.quantity - COALESCE(grn_received.total_received, 0)) as pending_qty
            FROM purchase_order_tran pot
            LEFT JOIN part p ON pot.partnum = p.part_num AND pot.company = p.company
            LEFT JOIN unit u ON p.unit_id = u.unit_id AND p.company = u.company
            LEFT JOIN (
                SELECT partnum, SUM(quantity) as total_received
                FROM goods_receipt_tran
                WHERE company = 1 AND active = true
                GROUP BY partnum
            ) grn_received ON pot.partnum = grn_received.partnum
            WHERE pot.company = 1 AND pot.po_no = %s AND pot.active = true
            ORDER BY pot.rowid
        """, (po_no,))
        po_lines = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('create_grn.html', po_header=po_header, po_lines=po_lines)

    except Exception as e:
        flash(f'Error loading GRN form: {str(e)}', 'error')
        return redirect(url_for('grn_management'))

@app.route('/grn/view/<int:grn_no>')
def view_grn(grn_no):
    """View GRN details"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('grn_management'))

        cursor = conn.cursor()

        # Get GRN header with vendor and PO information
        cursor.execute("""
            SELECT grh.*, v.vendor_name, v.address1, v.city, v.state, v.phone, v.email,
                   poh.po_date
            FROM goods_receipt_head grh
            LEFT JOIN vendor v ON grh.vendor = v.vendor_code AND grh.company = v.company
            LEFT JOIN purchase_order_head poh ON grh.po_no = poh.po_no AND grh.company = poh.company
            WHERE grh.company = 1 AND grh.grn_no = %s
        """, (grn_no,))
        grn_header = cursor.fetchone()

        if not grn_header:
            flash('GRN not found', 'error')
            return redirect(url_for('grn_management'))

        # Get GRN line items
        cursor.execute("""
            SELECT grt.*, p.part_desc, u.unit_desc
            FROM goods_receipt_tran grt
            LEFT JOIN part p ON grt.partnum = p.part_num AND grt.company = p.company
            LEFT JOIN unit u ON p.unit_id = u.unit_id AND p.company = u.company
            WHERE grt.company = 1 AND grt.grn_no = %s AND grt.active = true
            ORDER BY grt.rowid
        """, (grn_no,))
        grn_lines = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('view_grn.html', grn_header=grn_header, grn_lines=grn_lines)

    except Exception as e:
        flash(f'Error loading GRN: {str(e)}', 'error')
        return redirect(url_for('grn_management'))

@app.route('/grn/create_from_po')
def grn_create_from_po():
    """Show available POs for GRN creation"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('grn_management'))

        cursor = conn.cursor()

        # Get POs that don't have complete GRNs yet
        cursor.execute("""
            SELECT DISTINCT poh.po_no, poh.po_date, v.vendor_name, poh.active,
                   COUNT(pot.rowid) as total_items,
                   SUM(pot.amount) as total_amount
            FROM purchase_order_head poh
            LEFT JOIN vendor v ON poh.vendor = v.vendor_code AND poh.company = v.company
            LEFT JOIN purchase_order_tran pot ON poh.po_no = pot.po_no AND poh.company = pot.company
            WHERE poh.company = 1 AND poh.active = true AND pot.active = true
            GROUP BY poh.po_no, poh.po_date, v.vendor_name, poh.active
            ORDER BY poh.po_date DESC
        """)
        available_pos = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('grn_select_po.html', purchase_orders=available_pos)

    except Exception as e:
        flash(f'Error loading purchase orders: {str(e)}', 'error')
        return redirect(url_for('grn_management'))

# API endpoint to check if PO has line items
@app.route('/api/check_po_items/<int:po_no>')
def check_po_items(po_no):
    """Check if a purchase order has line items"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM purchase_order_tran
            WHERE po_no = %s AND company = 1
        """, (po_no,))

        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        return jsonify({'has_items': count > 0, 'item_count': count})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
