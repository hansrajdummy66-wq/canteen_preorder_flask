import os
from datetime import datetime
from typing import Optional
from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "orders.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["STAFF_KEY"] = os.environ.get("STAFF_KEY", "canteen123")

db = SQLAlchemy(app)

# ---- Menu ----
MENU_ITEMS = [
    ("Veg Sandwich", 40),
    ("Cheese Sandwich", 60),
    ("Masala Dosa", 80),
    ("Idli (2 pcs)", 35),
    ("Samosa (2 pcs)", 30),
    ("Pav Bhaji", 90),
    ("Maggi", 45),
    ("Aloo Paratha", 50),
    ("Fruit Bowl", 55),
    ("Cold Coffee", 70),
    ("Lassi", 50),
    ("Water Bottle", 20),
]

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(120), nullable=False)
    class_section = db.Column(db.String(50), nullable=False)
    item_name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    order_number = db.Column(db.String(32), unique=True, nullable=False, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "order_number": self.order_number,
            "student_name": self.student_name,
            "class_section": self.class_section,
            "item_name": self.item_name,
            "price": self.price,
            "created_at": self.created_at.isoformat(),
        }

def ensure_db():
    with app.app_context():
        db.create_all()

def generate_order_number(created: datetime, row_id_hint: Optional[int] = None) -> str:
    date_part = created.strftime("%Y%m%d")
    seq = f"{row_id_hint:04d}" if row_id_hint else f"{int(created.timestamp()) % 10000:04d}"
    return f"{date_part}-{seq}"

@app.route("/")
def student_form():
    return render_template("student.html", menu=MENU_ITEMS)

@app.route("/order", methods=["POST"])
def place_order():
    name = request.form.get("name", "").strip()
    class_section = request.form.get("class_section", "").strip()
    item = request.form.get("item")

    if not name or not class_section or not item:
        return render_template("student.html", menu=MENU_ITEMS, error="Fill all fields")

    try:
        idx = int(item)
        item_name, price = MENU_ITEMS[idx]
    except Exception:
        return render_template("student.html", menu=MENU_ITEMS, error="Invalid item selected")

    created = datetime.utcnow()
    temp = Order(
        student_name=name,
        class_section=class_section,
        item_name=item_name,
        price=price,
        created_at=created,
        order_number="temp"
    )
    db.session.add(temp)
    db.session.flush()
    temp.order_number = generate_order_number(created, temp.id)
    db.session.commit()

    return redirect(url_for("order_success", order_number=temp.order_number))

@app.route("/success/<order_number>")
def order_success(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template("order_success.html", order=order)

@app.route("/staff")
def staff_page():
    return render_template("staff.html")

@app.route("/api/orders")
def api_orders():
    key = request.args.get("key")
    if key != app.config["STAFF_KEY"]:
        abort(401)
    orders = [o.to_dict() for o in Order.query.order_by(Order.id.desc()).all()]
    return jsonify({"orders": orders})

if __name__ == "__main__":
    ensure_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

