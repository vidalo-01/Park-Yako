"""
app.py
------
Web layer (Flask). Ties the database + algorithms modules together and
exposes them as a browser-based system, per the brief's "running as a
web-based system" requirement.

Routes:
    GET  /                 -> dashboard: visual slot display + entry form
    POST /entry             -> Vehicle Entry module (park a car)
    GET  /checkout           -> preview fee for a plate before paying
    POST /checkout/confirm   -> Vehicle Exit + Payment + Barrier module
    GET  /history            -> log of completed sessions (from the DB)
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session

from database import init_db, get_conn
from algorithms import SlotManager
from mpesa import MpesaError, initiate_stk_push, normalize_phone
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "park-yako-change-this-secret")
STAFF_USERNAME = os.getenv("STAFF_USERNAME", "staff")
STAFF_PASSWORD = os.getenv("STAFF_PASSWORD", "ParkYako@123")

# One SlotManager instance shared for the app's lifetime - it is the live
# in-memory brain of the car park, backed by SQLite (see algorithms.py).
init_db()
manager = SlotManager()


def staff_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("staff_logged_in"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == STAFF_USERNAME and password == STAFF_PASSWORD:
            session["staff_logged_in"] = True
            session["staff_username"] = username
            next_url = request.args.get("next") or url_for("dashboard")
            if not next_url.startswith("/") or next_url.startswith("//"):
                next_url = url_for("dashboard")
            return redirect(next_url)
        flash("Invalid staff username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/")
@staff_required
def dashboard():
    slots = manager.get_slot_display()
    return render_template(
        "index.html",
        slots=slots,
        available=manager.available_count(),
        total=len(slots),
    )


@app.route("/entry", methods=["POST"])
@staff_required
def entry():
    plate = request.form.get("plate_number", "")
    if not plate.strip():
        flash("Please enter a number plate.", "error")
        return redirect(url_for("dashboard"))

    ok, result = manager.park_vehicle(plate)
    if ok:
        flash(f"Vehicle {plate.strip().upper()} parked in slot {result}.", "success")
    else:
        flash(result, "error")
    return redirect(url_for("dashboard"))


@app.route("/checkout", methods=["GET"])
@staff_required
def checkout_preview():
    plate = request.args.get("plate_number", "")
    preview = manager.preview_fee(plate) if plate else None
    if plate and not preview:
        flash("No active session found for that plate.", "error")
    return render_template("checkout.html", preview=preview, plate=plate)


@app.route("/checkout/pay", methods=["POST"])
@staff_required
def checkout_pay():
    plate = request.form.get("plate_number", "")
    phone = request.form.get("phone_number", "")

    ok, preview = manager.begin_checkout(plate)
    if not ok:
        flash(preview, "error")
        return redirect(url_for("checkout_preview", plate_number=plate))

    # No M-Pesa prompt is needed when the parking fee is zero.
    if preview["fee"] == 0:
        ok, receipt = manager.complete_free_checkout(plate)
        if ok:
            return render_template("receipt.html", receipt=receipt)
        flash(receipt, "error")
        return redirect(url_for("checkout_preview", plate_number=plate))

    try:
        phone = normalize_phone(phone)
        stk = initiate_stk_push(
            phone=phone,
            amount=int(preview["fee"]),
            account_reference=f"PARK{preview['session_id']}",
            description="Parking payment",
        )
        manager.mark_payment_initiated(
            preview["session_id"],
            stk["checkout_request_id"],
            stk["merchant_request_id"],
            phone,
        )
    except MpesaError as exc:
        manager.mark_payment_failed(preview["session_id"], str(exc))
        flash(str(exc), "error")
        return redirect(url_for("checkout_preview", plate_number=plate))

    return render_template(
        "payment_pending.html",
        payment=preview,
        customer_message=stk["customer_message"],
    )


@app.route("/payments/callback", methods=["POST"])
def payments_callback():
    """Daraja callback: only a ResultCode of 0 completes the parking session."""
    payload = request.get_json(silent=True) or {}
    callback = payload.get("Body", {}).get("stkCallback", {})
    checkout_request_id = callback.get("CheckoutRequestID")
    result_code = callback.get("ResultCode")

    if not checkout_request_id:
        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

    if str(result_code) == "0":
        receipt = None
        metadata = callback.get("CallbackMetadata", {}).get("Item", [])
        for item in metadata:
            if item.get("Name") == "MpesaReceiptNumber":
                receipt = item.get("Value")
                break
        manager.complete_payment(checkout_request_id, receipt)
    else:
        payment = manager.get_payment_status_by_checkout(checkout_request_id)
        if payment:
            manager.mark_payment_failed(
                payment["session_id"],
                callback.get("ResultDesc", "M-Pesa payment was cancelled or failed."),
            )

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200


@app.route("/payment/status/<int:session_id>")
@staff_required
def payment_status(session_id):
    status = manager.get_payment_status(session_id)
    if not status:
        return jsonify({"error": "Payment session not found."}), 404
    return jsonify(status)


@app.route("/receipt/<int:session_id>")
@staff_required
def receipt(session_id):
    status = manager.get_payment_status(session_id)
    if not status or not status.get("receipt"):
        flash("Receipt is not available yet.", "error")
        return redirect(url_for("dashboard"))
    return render_template("receipt.html", receipt=status["receipt"])


@app.route("/history")
@staff_required
def history():
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT s.plate_number, sl.slot_number, s.entry_time, s.exit_time, s.fee, s.status
            FROM sessions s
            JOIN slots sl ON sl.id = s.slot_id
            ORDER BY s.id DESC
            LIMIT 100
            """
        ).fetchall()
    return render_template("history.html", rows=rows)


if __name__ == "__main__":
    # host=0.0.0.0 so it's reachable on a local network (e.g. a barrier
    # kiosk / display screen at the gate), debug=True for development only.
    app.run(host="0.0.0.0", port=5000, debug=True)
