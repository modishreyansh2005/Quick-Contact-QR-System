import os
import csv
import io
import zipfile
import sqlite3
from io import BytesIO, StringIO

from flask import (
    Flask, render_template, request,
    redirect, session, send_file, Response
)

from PIL import Image, ImageDraw, ImageFont

# =====================================================
# APP CONFIG
# =====================================================

app = Flask(__name__)
app.secret_key = "vahaan_super_secret_key"

ADMIN_USERNAME = "shrey"
ADMIN_PASSWORD = "21928"

# =====================================================
# DATABASE INIT
# =====================================================

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS qr_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            status TEXT DEFAULT 'unused'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_number TEXT,
            owner_name TEXT,
            phone TEXT,
            emergency_phone TEXT,
            qr_code TEXT UNIQUE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS scan_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_code TEXT,
            scan_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT
        )
    """)

    conn.commit()
    conn.close()

with app.app_context():
    init_db()

# =====================================================
# HOME
# =====================================================

@app.route("/")
def home():
    return render_template("register.html")

# =====================================================
# REGISTER
# =====================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    qr_code = request.form["qr_code"]
    vehicle_number = request.form["vehicle_number"]
    owner_name = request.form["owner_name"]
    phone = request.form["phone"]
    emergency_phone = request.form["emergency_phone"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM qr_codes WHERE code=? AND status='unused'", (qr_code,))
    qr = c.fetchone()

    if not qr:
        conn.close()
        return "Invalid or Already Used QR Code"

    c.execute("""
        INSERT INTO vehicles
        (vehicle_number, owner_name, phone, emergency_phone, qr_code)
        VALUES (?, ?, ?, ?, ?)
    """, (vehicle_number, owner_name, phone, emergency_phone, qr_code))

    c.execute("UPDATE qr_codes SET status='assigned' WHERE code=?", (qr_code,))

    conn.commit()
    conn.close()

    return render_template("success.html",
                           vehicle_number=vehicle_number,
                           owner_name=owner_name,
                           qr_code=qr_code)

# =====================================================
# VEHICLE SCAN
# =====================================================

# @app.route("/v/<code>")
# def vehicle(code):

#     conn = sqlite3.connect("database.db")
#     c = conn.cursor()

#     c.execute("SELECT * FROM vehicles WHERE qr_code=?", (code,))
#     vehicle = c.fetchone()

#     if vehicle:
#         ip = request.remote_addr
#         c.execute("INSERT INTO scan_logs (qr_code, ip_address) VALUES (?, ?)", (code, ip))
#         conn.commit()
#         conn.close()
#         return render_template("vehicle.html", vehicle=vehicle)

#     conn.close()
#     return "⚠️ QR Not Activated Yet"



@app.route("/v/<code>")
def vehicle(code):

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row   # safer access
    c = conn.cursor()

    try:
        # Check vehicle activation
        c.execute(
            "SELECT * FROM vehicles WHERE qr_code = ?",
            (code,)
        )
        vehicle = c.fetchone()

        if not vehicle:
            return "⚠️ QR Not Activated Yet"

        # Log scan
        ip = request.remote_addr

        c.execute(
            "INSERT INTO scan_logs (qr_code, ip_address) VALUES (?, ?)",
            (code, ip)
        )
        conn.commit()

        return render_template("vehicle.html", vehicle=vehicle)

    except Exception as e:
        return f"Error: {str(e)}"

    finally:
        conn.close()
        

# ------------------------
# GENERATE QR
# ------------------------
@app.route('/admin/bulk_cards/<int:count>')
def bulk_cards(count):

    if session.get('admin') != True:
        return redirect('/admin')

    import zipfile
    import io

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute(
        "SELECT code FROM qr_codes WHERE status='unused' LIMIT ?",
        (count,)
    )

    codes = c.fetchall()
    conn.close()

    if not codes:
        return "No unused QR codes available"

    memory_file = io.BytesIO()

    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:

        for row in codes:

            code = row[0]
            qr_path = f"static/qr/{code}.png"

            if not os.path.exists(qr_path):
                continue

            qr_image = Image.open(qr_path).resize((260, 260))

            width = 1011
            height = 638

            card = Image.new("RGB", (width, height), "#E5E7EB")
            draw = ImageDraw.Draw(card)

            try:
                header_font = ImageFont.truetype("arialbd.ttf", 60)
                big_font = ImageFont.truetype("arialbd.ttf", 64)
                text_font = ImageFont.truetype("arial.ttf", 40)
                small_font = ImageFont.truetype("arial.ttf", 26)
            except:
                header_font = ImageFont.load_default()
                big_font = ImageFont.load_default()
                text_font = ImageFont.load_default()
                small_font = ImageFont.load_default()

            # HEADER BAR
            draw.rectangle([0, 0, width, 120], fill="#0F172A")

            header_text = "Quick Contact"
            bbox = draw.textbbox((0, 0), header_text, font=header_font)

            draw.text(
                ((width - (bbox[2]-bbox[0])) // 2, 30),
                header_text,
                fill="white",
                font=header_font
            )

            # DIVIDER LINE
            divider_x = width // 2

            draw.line(
                [(divider_x, 120), (divider_x, 560)],
                fill="#D1D5DB",
                width=4
            )

            # LEFT PANEL CENTER
            left_center = divider_x // 2

            # QR CODE ID
            id_text = f"QR Code ID: {code}"
            bbox = draw.textbbox((0,0), id_text, font=text_font)

            draw.text(
                (left_center - (bbox[2]-bbox[0])//2, 180),
                id_text,
                fill="#374151",
                font=text_font
            )

            # OWNER (LINE 1)
            owner_text = "OWNER"
            bbox = draw.textbbox((0,0), owner_text, font=big_font)

            draw.text(
                (left_center - (bbox[2]-bbox[0])//2, 280),
                owner_text,
                fill="#111827",
                font=big_font
            )

            # INFORMATION (LINE 2)
            info_text = "INFORMATION"
            bbox = draw.textbbox((0,0), info_text, font=big_font)

            draw.text(
                (left_center - (bbox[2]-bbox[0])//2, 360),
                info_text,
                fill="#111827",
                font=big_font
            )

            # AUTHORIZED TEXT
            auth_text = "Authorized Corporate Use"
            bbox = draw.textbbox((0,0), auth_text, font=text_font)

            draw.text(
                (left_center - (bbox[2]-bbox[0])//2, 470),
                auth_text,
                fill="#374151",
                font=text_font
            )

            # QR POSITION
            qr_x = divider_x + (divider_x - 260) // 2
            qr_y = 200

            card.paste(qr_image, (qr_x, qr_y))

            # FOOTER
            draw.rectangle([0, 560, width, height], fill="#CBD5E1")

            footer_text = "Scan to securely contact vehicle owner"
            bbox = draw.textbbox((0,0), footer_text, font=small_font)

            draw.text(
                ((width - (bbox[2]-bbox[0]))//2, 590),
                footer_text,
                fill="#475569",
                font=small_font
            )

            img_buffer = io.BytesIO()
            card.save(img_buffer, format="PNG", dpi=(300,300))

            zf.writestr(f"{code}_card.png", img_buffer.getvalue())

    memory_file.seek(0)

    return send_file(
        memory_file,
        as_attachment=True,
        download_name="vahaan_qr_cards.zip",
        mimetype="application/zip"
    )


# =====================================================
# DOWNLOAD PVC CARD
# =====================================================

@app.route("/download_card/<code>")
def download_card(code):

    qr_path = f"static/qr/{code}.png"
    if not os.path.exists(qr_path):
        return "QR image not found"

    qr_image = Image.open(qr_path).resize((260, 260))

    width, height = 1011, 638
    card = Image.new("RGB", (width, height), "#E5E7EB")
    draw = ImageDraw.Draw(card)

    try:
        header_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 60)
        big_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 54)
        text_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 40)
        small_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 26)
    except:
        header_font = ImageFont.load_default()
        big_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Header
    draw.rectangle([0, 0, width, 120], fill="#0F172A")
    header_text = "Quick Contact"
    bbox = draw.textbbox((0, 0), header_text, font=header_font)
    draw.text(((width - (bbox[2] - bbox[0])) // 2, 30),
              header_text, fill="white", font=header_font)

    divider_x = 540
    draw.line([(divider_x, 120), (divider_x, 560)], fill="#D1D5DB", width=4)

    # Left Panel
    y = 190
    left_margin = 60

    draw.text((left_margin, y),
              f"QR Code ID: {code}",
              fill="#374151", font=text_font)

    y += 90

    title1 = "OWNER"
    title2 = "INFORMATION"

    bbox1 = draw.textbbox((0, 0), title1, font=big_font)
    bbox2 = draw.textbbox((0, 0), title2, font=big_font)

    left_center = divider_x // 2

    draw.text((left_center - (bbox1[2] - bbox1[0]) // 2, y),
              title1, fill="#111827", font=big_font)

    draw.text((left_center - (bbox2[2] - bbox2[0]) // 2,
               y + (bbox1[3] - bbox1[1]) + 10),
              title2, fill="#111827", font=big_font)

    y += 200

    draw.text((left_margin, y),
              "Authorized Corporate Use",
              fill="#374151", font=text_font)

    # Right Panel
    card.paste(qr_image, (650, 190))

    # Footer
    draw.rectangle([0, 560, width, height], fill="#CBD5E1")
    draw.text((40, 590),
              "Scan to securely contact vehicle owner",
              fill="#475569", font=small_font)

    img_io = BytesIO()
    card.save(img_io, "PNG", dpi=(300, 300))
    img_io.seek(0)

    return send_file(img_io,
                     mimetype="image/png",
                     as_attachment=True,
                     download_name=f"{code}_pvc_card.png")

# =====================================================
# EXPORT CSV
# =====================================================

@app.route("/admin/export")
def export_csv():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, vehicle_number, owner_name, phone, qr_code FROM vehicles")
    rows = cursor.fetchall()
    conn.close()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["ID", "Vehicle Number", "Owner Name", "Phone", "QR Code"])
    writer.writerows(rows)

    return Response(si.getvalue(),
                    mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=vehicles.csv"})



# ------------------------
# ADMIN LOGIN
# ------------------------

@app.route('/admin', methods=['GET', 'POST'])
def admin():

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/admin/dashboard')
        else:
            return "Invalid credentials"

    return render_template('admin_login.html')


# ------------------------
# ADMIN DASHBOARD
# ------------------------

@app.route('/admin/dashboard')
def admin_dashboard():

    if session.get('admin') != True:
        return redirect('/admin')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    search = request.args.get('search')

    if search:
        c.execute("SELECT * FROM vehicles WHERE vehicle_number LIKE ?", ('%' + search + '%',))
    else:
        c.execute("SELECT * FROM vehicles")

    vehicles = c.fetchall()

    c.execute("SELECT * FROM qr_codes")
    qr_codes = c.fetchall()

    c.execute("SELECT * FROM scan_logs")
    scans = c.fetchall()

    conn.close()

    total_registered = len(vehicles)
    activated_count = len(vehicles)
    unused_count = len([q for q in qr_codes if q[2] == 'unused'])

    return render_template(
        'admin_dashboard.html',
        vehicles=vehicles,
        qr_codes=qr_codes,
        scans=scans,
        total_registered=total_registered,
        activated_count=activated_count,
        unused_count=unused_count
    )


# ------------------------
# DELETE VEHICLE
# ------------------------

@app.route('/admin/delete_vehicle/<int:id>')
def delete_vehicle(id):

    if session.get('admin') != True:
        return redirect('/admin')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("DELETE FROM vehicles WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/admin/dashboard')

# ------------------------
# LOGOUT
# ------------------------

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/admin')





# # =====================================================
# # ADMIN LOGIN
# # =====================================================

# @app.route("/admin", methods=["GET", "POST"])
# def admin():

#     if request.method == "POST":
#         username = request.form.get("username")
#         password = request.form.get("password")

#         if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
#             session["admin"] = True
#             return redirect("/admin/dashboard")

#         return "Invalid credentials"

#     return render_template("admin_login.html")

# # =====================================================
# # ADMIN DASHBOARD
# # =====================================================

# @app.route("/admin/dashboard")
# def admin_dashboard():

#     if session.get("admin") != True:
#         return redirect("/admin")

#     conn = sqlite3.connect("database.db")
#     c = conn.cursor()

#     c.execute("SELECT * FROM vehicles")
#     vehicles = c.fetchall()

#     c.execute("SELECT * FROM qr_codes")
#     qr_codes = c.fetchall()

#     c.execute("SELECT * FROM scan_logs")
#     scans = c.fetchall()

#     conn.close()

#     return render_template("admin_dashboard.html",
#                            vehicles=vehicles,
#                            qr_codes=qr_codes,
#                            scans=scans)

# =====================================================
# RUN (Render Compatible)
# =====================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))