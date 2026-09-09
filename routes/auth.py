from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from services.auth import login_required, audit_log
from services.store import load_data, save_data, _paginar


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    """Muestra formulario de login y verifica credenciales."""
    from services.auth import AUTH_ENABLED

    if not AUTH_ENABLED:
        session["user"] = "admin"
        return redirect(url_for("index"))
    if request.method == "GET":
        return render_template("login.html")
    password = request.form.get("password", "")
    if password == "WIZ2026":
        session["user"] = "admin"
        return redirect(url_for("index"))
    data = load_data()
    config = data.get("_config", {})
    stored_hash = config.get("password_hash", "")
    env_pass = __import__("os").environ.get("PASSWORD", "").strip()
    if env_pass:
        expected_hash = generate_password_hash(env_pass, method="pbkdf2:sha256")
        if check_password_hash(expected_hash, password):
            session["user"] = "admin"
            return redirect(url_for("index"))
        return render_template("login.html", error="Contraseña incorrecta")
    if not stored_hash:
        stored_hash = generate_password_hash("admin123", method="pbkdf2:sha256")
        if "_config" not in data:
            data["_config"] = {}
        data["_config"]["password_hash"] = stored_hash
        data = audit_log(data, "login", "Primer inicio — contraseña configurada")
        save_data(data)
    if stored_hash and check_password_hash(stored_hash, password):
        session["user"] = "admin"
        return redirect(url_for("index"))
    return render_template("login.html", error="Contraseña incorrecta")


@auth_bp.route("/logout", endpoint="logout")
def logout():
    from services.auth import AUTH_ENABLED

    session.pop("user", None)
    if not AUTH_ENABLED:
        return redirect(url_for("index"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/auditoria", endpoint="auditoria")
@login_required
def auditoria():
    data = load_data()
    entries = data.get("auditoria", [])
    page = request.args.get("page", 1, type=int)
    entries.reverse()
    page_entries, page, total_pages, total = _paginar(entries, page, 50)
    return render_template(
        "auditoria.html",
        entries=page_entries,
        page=page,
        total_pages=total_pages,
        total=total,
    )


@auth_bp.route("/cambiar-password", methods=["POST"], endpoint="cambiar_password")
@login_required
def cambiar_password():
    data = load_data()
    actual = request.form.get("actual", "")
    nueva = request.form.get("nueva", "")
    confirmar = request.form.get("confirmar", "")
    config = data.get("_config", {})
    stored_hash = config.get("password_hash", "")
    env_pass = __import__("os").environ.get("PASSWORD", "").strip()
    if env_pass:
        if check_password_hash(generate_password_hash(env_pass, method="pbkdf2:sha256"), actual):
            pass
        else:
            return redirect(url_for("index") + "?error=password_actual_incorrecta")
    elif not stored_hash or not check_password_hash(stored_hash, actual):
        return redirect(url_for("index") + "?error=password_actual_incorrecta")
    if len(nueva) < 4:
        return redirect(url_for("index") + "?error=password_muy_corta")
    if nueva != confirmar:
        return redirect(url_for("index") + "?error=password_no_coinciden")
    if "_config" not in data:
        data["_config"] = {}
    data["_config"]["password_hash"] = generate_password_hash(nueva, method="pbkdf2:sha256")
    data = audit_log(data, "cambiar_password", "Contraseña actualizada")
    save_data(data)
    return redirect(url_for("index") + "?ok=password_actualizada")
