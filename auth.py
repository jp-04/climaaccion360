"""Registro, acceso y perfil de usuarios."""

import re
import sqlite3

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db, get_recent_predictions


bp = Blueprint("auth", __name__)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def current_user():
    if "current_user" not in g:
        user_id = session.get("usuario_id")
        g.current_user = (
            get_db().execute(
                "SELECT id, nombre, correo, fecha_registro FROM usuarios WHERE id = ?",
                (user_id,),
            ).fetchone()
            if user_id is not None
            else None
        )
        if user_id is not None and g.current_user is None:
            session.clear()
    return g.current_user


@bp.app_context_processor
def inject_current_user():
    return {"current_user": current_user()}


@bp.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        contrasena = request.form.get("contrasena", "")
        confirmacion = request.form.get("confirmacion", "")
        error = None

        if not all((nombre, correo, contrasena.strip(), confirmacion.strip())):
            error = "Completa todos los campos."
        elif len(nombre) > 120 or len(correo) > 254:
            error = "El nombre o el correo es demasiado largo."
        elif not EMAIL_PATTERN.fullmatch(correo):
            error = "Introduce un correo electrónico válido."
        elif contrasena != confirmacion:
            error = "Las contraseñas no coinciden."
        elif len(contrasena) < 8:
            error = "La contraseña debe tener al menos 8 caracteres."
        elif get_db().execute("SELECT id FROM usuarios WHERE correo = ?", (correo,)).fetchone():
            error = "Este correo ya está registrado."

        if error is None:
            try:
                get_db().execute(
                    "INSERT INTO usuarios (nombre, correo, password_hash) VALUES (?, ?, ?)",
                    (nombre, correo, generate_password_hash(contrasena)),
                )
                get_db().commit()
            except sqlite3.IntegrityError:
                get_db().rollback()
                error = "Este correo ya está registrado."
            else:
                flash("Cuenta creada. Ya puedes iniciar sesión.", "success")
                return redirect(url_for("auth.login"))

        return render_template("registro.html", error=error, nombre=nombre, correo=correo), 400

    return render_template("registro.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()
        contrasena = request.form.get("contrasena", "")
        if not correo or not contrasena:
            error = "Introduce tu correo y contraseña."
        else:
            user = get_db().execute(
                "SELECT id, password_hash FROM usuarios WHERE correo = ?", (correo,)
            ).fetchone()
            if user is None or not check_password_hash(user["password_hash"], contrasena):
                error = "Correo o contraseña incorrectos."
            else:
                session.clear()
                session["usuario_id"] = user["id"]
                return redirect(url_for("auth.perfil"))
        return render_template("login.html", error=error, correo=correo), 400

    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@bp.route("/perfil")
def perfil():
    user = current_user()
    if user is None:
        return redirect(url_for("auth.login"))
    return render_template(
        "perfil.html",
        usuario=user,
        predicciones=get_recent_predictions(user["id"]),
        modelos={"regresion_lineal": "Regresión lineal", "arbol_decision": "Árbol de decisión"},
    )
