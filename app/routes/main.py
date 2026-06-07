import json
from flask import Blueprint, Response, abort, redirect, render_template, request, session, url_for

from ..db import create_registration, get_settings, get_table_bookings, get_ticket_counts
from ..email import send_confirmation

bp = Blueprint("main", __name__)


def _counts():
    total, sold, remaining = get_ticket_counts()
    return {"total": total, "sold": sold, "remaining": remaining}


def _fcfs_active(settings: dict) -> bool:
    return settings.get("fcfs_block_enabled", "false").lower() == "true"


@bp.route("/")
def index():
    settings = get_settings()
    total, sold, remaining = get_ticket_counts()
    fcfs = _fcfs_active(settings)
    return render_template(
        "index.html",
        settings=settings,
        total=total,
        sold=sold,
        remaining=remaining,
        sold_out=fcfs and remaining <= 0,
    )


@bp.route("/api/ticket-count")
def ticket_count_stream():
    """
    Short-lived SSE: sends one update, sets retry=10s, closes.
    Browser auto-reconnects every 10 s. No worker starvation.
    """
    settings = get_settings()
    total, sold, remaining = get_ticket_counts()
    data = json.dumps({
        "total": total,
        "sold": sold,
        "remaining": remaining,
        "fcfs": _fcfs_active(settings),
    })

    def generate():
        yield f"retry: 10000\ndata: {data}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@bp.route("/api/table-counts")
def table_counts():
    _, sold, _ = get_ticket_counts()
    return {"bookings": get_table_bookings(), "total_booked": sold}


@bp.route("/register", methods=["POST"])
def register():
    if request.form.get("csrf_token") != session.get("csrf_token"):
        abort(403)

    settings = get_settings()
    if settings.get("registration_open", "false").lower() != "true":
        return render_template(
            "index.html",
            settings=settings,
            errors=["Die Registrierung ist aktuell geschlossen."],
            **_counts(),
        )

    f = request.form
    registrant_name = f.get("registrant_name", "").strip()
    email = f.get("email", "").strip()
    desired_table_raw = f.get("desired_table", "").strip()

    try:
        companion_count = int(f.get("companion_count", "0") or "0")
    except ValueError:
        companion_count = 0

    errors: list[str] = []
    if not registrant_name:
        errors.append("Dein Name ist erforderlich.")
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        errors.append("Eine gültige E-Mail-Adresse ist erforderlich.")
    if companion_count < 1:
        errors.append("Mindestens 1 Begleitperson ist erforderlich.")

    desired_table: int | None = None
    if desired_table_raw:
        try:
            desired_table = int(desired_table_raw)
            if desired_table < 1:
                desired_table = None
        except ValueError:
            desired_table = None

    # Only companions count as tickets – the registrant already has one from round 1.
    persons: list[dict] = []
    for i in range(1, companion_count + 1):
        c_name = f.get(f"companion_name_{i}", "").strip()
        c_over18 = f.get(f"companion_over18_{i}") == "yes"
        c_food = f.get(f"companion_food_{i}", "")
        if not c_name:
            errors.append(f"Name der Begleitperson {i} fehlt.")
        if c_food not in ("meat", "vegetarian"):
            errors.append(f"Essenswahl für Begleitperson {i} fehlt.")
        persons.append(
            {
                "name": c_name,
                "is_over_18": c_over18,
                "food_preference": c_food,
                "is_registrant": False,
            }
        )

    if errors:
        return render_template(
            "index.html",
            settings=settings,
            errors=errors,
            form_data=f,
            **_counts(),
        )

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()

    try:
        reg_id = create_registration(
            registrant_name=registrant_name,
            email=email,
            desired_table=desired_table,
            persons=persons,
            ip_address=ip,
        )
    except ValueError as exc:
        if str(exc) == "no_tickets":
            return render_template(
                "index.html",
                settings=settings,
                errors=["Leider sind alle Tickets vergeben (First-Come-First-Serve aktiv)."],
                **_counts(),
            )
        raise

    price = int(settings.get("ticket_price", 60))
    total_price = companion_count * price
    session["payment"] = {
        "reg_id": reg_id,
        "name": registrant_name,
        "total_tickets": companion_count,
        "total_price": total_price,
    }

    send_confirmation(
        to_email=email,
        registrant_name=registrant_name,
        reg_id=reg_id,
        total_tickets=companion_count,
        total_price=total_price,
        settings=settings,
    )

    return redirect(url_for("main.payment"))


@bp.route("/payment")
def payment():
    payment_info = session.get("payment")
    if not payment_info:
        return redirect(url_for("main.index"))
    settings = get_settings()
    return render_template("payment.html", payment=payment_info, settings=settings)
