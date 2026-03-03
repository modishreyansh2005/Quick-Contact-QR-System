import sqlite3
import qrcode
import os

BASE_URL = "http://127.0.0.1:5000/v/"   # change later to domain

if not os.path.exists("static/qr"):
    os.makedirs("static/qr")

conn = sqlite3.connect('database.db')
c = conn.cursor()

for i in range(1, 101):  # create 100 QR codes
    code = f"VS{i:06d}"

    # Insert into DB
    c.execute("INSERT OR IGNORE INTO qr_codes (code) VALUES (?)", (code,))

    # Generate QR image
    url = BASE_URL + code
    img = qrcode.make(url)
    img.save(f"static/qr/{code}.png")

conn.commit()
conn.close()

print("QR Pool Generated Successfully")