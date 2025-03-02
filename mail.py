from flask import Flask, jsonify, request
import mysql.connector
from datetime import datetime, timedelta
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

# Database Connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="vijay",
    database="finance"
)
cursor = db.cursor()

# Function to get the previous month in 'YYYY-MM' format
def get_previous_month():
    today = datetime.today()
    first_day_of_current_month = today.replace(day=1)
    last_month = first_day_of_current_month - timedelta(days=1)
    return last_month.strftime('%Y-%m')

# Function to fetch transactions for a given user and month
def get_transactions(user_id, month_year):
    query = """SELECT Category, Amount, Month_Year, Description 
               FROM Transactions 
               WHERE User_ID = %s AND Month_Year LIKE %s"""
    cursor.execute(query, (user_id, month_year + '%'))
    transactions = cursor.fetchall()
    return transactions

# Function to generate a PDF report
def generate_pdf(user_id, month_year, transactions):
    pdf_filename = f"Transaction_Report_{user_id}_{month_year}.pdf"
    pdf_path = os.path.join(os.getcwd(), pdf_filename)
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 50, f"Transaction Report - {month_year}")
    c.line(50, height - 60, 550, height - 60)
    c.setFont("Helvetica-Bold", 12)
    y_position = height - 100
    c.drawString(50, y_position, "Category")
    c.drawString(200, y_position, "Amount")
    c.drawString(300, y_position, "Date")
    c.drawString(420, y_position, "Description")
    y_position -= 20
    c.line(50, y_position, 550, y_position)
    y_position -= 20
    c.setFont("Helvetica", 11)
    for t in transactions:
        if y_position < 50:
            c.showPage()
            y_position = height - 100
            c.setFont("Helvetica", 11)
        c.drawString(50, y_position, str(t[0]))
        c.drawString(200, y_position, f"{t[1]}")
        c.drawString(300, y_position, str(t[2]))
        c.drawString(420, y_position, str(t[3]))
        y_position -= 20
    c.save()
    return pdf_path

# Function to generate report
def generate_report(user_id, month_year):
    transactions = get_transactions(user_id, month_year)
    if not transactions:
        return None
    return generate_pdf(user_id, month_year, transactions)

# Function to send email
def send_email(to_email, pdf_path):
    from_email = "mname5121@gmail.com"
    from_password = "gswv gtqg txjw tuzk"
    msg = MIMEMultipart()
    msg['Subject'] = "Monthly Transaction Report"
    msg['From'] = from_email
    msg['To'] = to_email
    body = "Please find your monthly transaction report attached."
    msg.attach(MIMEText(body, 'plain'))
    with open(pdf_path, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f"attachment; filename={os.path.basename(pdf_path)}",
    )
    msg.attach(part)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(from_email, from_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        return "Email sent successfully"
    except Exception as e:
        return str(e)
def delete_old_transactions():
    # Calculate the date three months before today
    three_months_ago = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

    query = """DELETE FROM Transactions WHERE Month_Year < %s"""
    cursor.execute(query, (three_months_ago,))
    db.commit()

    return f"Deleted transactions before {three_months_ago}"

def reset_budgets():
    try:

        # Update query to reset budgets
        query = "UPDATE Budgets SET Remaining_Monthly_Limit = Monthly_Limit"
        cursor.execute(query)
        db.commit()

        cursor.close()
        # conn.close()
        return {"message": "Budgets reset successfully"}
    except Exception as e:
        return {"error": str(e)}

# API Route to generate and send reports for all users (Automatically for the previous month)
@app.route('/send_reports', methods=['POST'])
def send_reports():
    month_year = get_previous_month()
    cursor.execute("SELECT User_ID, Email FROM Users")
    users = cursor.fetchall()
    results = []
    for user_id, user_email in users:
        report = generate_report(user_id, month_year)
        if report:
            response = send_email(user_email, report)
            results.append({"user_id": user_id, "email": user_email, "status": response})
        else:
            results.append({"user_id": user_id, "email": user_email, "status": "No transactions for this month"})
    return jsonify({"reports_sent": results})

@app.route('/delete_old_transactions', methods=['GET'])
def delete_transactions():
    result = delete_old_transactions()
    return jsonify({"message": result})

@app.route('/reset_budgets', methods=['POST'])
def reset_budget_route():
    result = reset_budgets()
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
