import os
from functools import wraps
from datetime import datetime
from flask import g, session, redirect, url_for


AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "true").lower() in ("true", "1", "yes", "on")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not AUTH_ENABLED:
            g.user = "admin"
            return f(*args, **kwargs)
        if "user" not in session:
            return redirect(url_for("auth.login"))
        g.user = session["user"]
        return f(*args, **kwargs)
    return decorated


def audit_log(data, accion, detalle=""):
    """Registra una accion en el log de auditoria."""
    if "auditoria" not in data:
        data["auditoria"] = []
    data["auditoria"].append({
        "fecha": datetime.now().isoformat(),
        "usuario": session.get("user", getattr(g, "user", "anonimo")),
        "accion": accion,
        "detalle": detalle,
    })
    return data
