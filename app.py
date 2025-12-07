from flask import Flask, render_template, request, send_file
import os, csv, json
from datetime import datetime
import inflect
from docxtpl import DocxTemplate

# ====== Configuration (आपके पुराने कोड जैसा ही) ======
TEMPLATE_FILE = "invoice.docx"
OUTPUT_FILE = "latest_invoice.docx"
HISTORY_FILE = "invoice_history.csv"
STATE_FILE = "app_state.json"

RATE = 950.00
SGST_RATE = 0.09
CGST_RATE = 0.09

# ====== Helper Functions (पुराने कोड से उठाए गए) ======
def indian_format(n):
    s, *d = str(f"{n:.2f}").partition(".")
    if len(s) > 3:
        s = s[:-3] + "," + s[-3:]
        i = len(s) - 6
        while i > 0:
            s = s[:i] + "," + s[i:]
            i -= 2
    return s + "".join(d)

def number_to_words(n):
    p = inflect.engine()
    words = p.number_to_words(n, andword="").title().replace("-", " ")
    return f"Rupees {words} Only"

def get_next_invoice_no(current_inv):
    if not current_inv:
        return "LSG/2526/1"
    try:
        parts = current_inv.rsplit('/', 1)
        if len(parts) == 2 and parts[1].isdigit():
            return f"{parts[0]}/{int(parts[1]) + 1}"
    except:
        pass
    return current_inv

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                return data.get("last_invoice", "LSG/2526/0")
        except:
            return "LSG/2526/0"
    return "LSG/2526/0"

def save_state(last_inv):
    with open(STATE_FILE, 'w') as f:
        json.dump({"last_invoice": last_inv}, f)

def save_to_history(data_dict):
    file_exists = os.path.isfile(HISTORY_FILE)
    with open(HISTORY_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Date", "Invoice No", "Truck No", "Qty", "Amount", "Grand Total"])
        writer.writerow([
            data_dict['date'],
            data_dict['invoice_no'],
            data_dict['truck_no'],
            data_dict['qty'],
            data_dict['amount'],
            data_dict['rounded']
        ])

# ====== Flask App ======
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    success = None
    preview = None

    last_inv = load_state()
    invoice_no = get_next_invoice_no(last_inv)
    today = datetime.today().strftime("%d/%m/%Y")

    if request.method == "POST":
        invoice_no = request.form.get("invoice_no", "").strip()
        date_val = request.form.get("date", "").strip()
        truck_no = request.form.get("truck_no", "").strip().upper()
        qty_str = request.form.get("qty", "").strip()

        if not (invoice_no and date_val and truck_no and qty_str):
            error = "कृपया सभी फ़ील्ड भरें।"
        else:
            try:
                qty = float(qty_str)
            except ValueError:
                error = "Quantity सही नहीं है।"
            else:
                amt = qty * RATE
                sgst = amt * SGST_RATE
                cgst = amt * CGST_RATE
                gtotal = amt + sgst + cgst
                rounded = round(gtotal)

                context = {
                    'invoice_no': invoice_no,
                    'date': date_val,
                    'truck_no': truck_no,
                    'qty': f"{qty:.2f}",
                    'amount': indian_format(amt),
                    'sgst': indian_format(sgst),
                    'cgst': indian_format(cgst),
                    'gtotal': indian_format(gtotal),
                    'rounded': indian_format(rounded),
                    'amount_words': number_to_words(rounded)
                }

                if not os.path.exists(TEMPLATE_FILE):
                    error = f"Template फाइल '{TEMPLATE_FILE}' नहीं मिली।"
                else:
                    # Word इनवॉइस बनाएं
                    doc = DocxTemplate(TEMPLATE_FILE)
                    doc.render(context)
                    doc.save(OUTPUT_FILE)

                    # हिस्ट्री और स्टेट सेव
                    save_to_history(context)
                    save_state(invoice_no)

                    success = f"Invoice {invoice_no} सफलतापूर्वक बन गई।"
                    preview = {
                        "amount": context['amount'],
                        "total": context['rounded']
                    }

    return render_template(
        "index.html",
        invoice_no=invoice_no,
        today=today,
        error=error,
        success=success,
        preview=preview
    )

@app.route("/download")
def download():
    if os.path.exists(OUTPUT_FILE):
        return send_file(OUTPUT_FILE, as_attachment=True)
    return "पहले कोई इनवॉइस जनरेट करें।"

if __name__ == "__main__":
    app.run(debug=True)

app.run(host="0.0.0.0", port=5000, debug=True)
