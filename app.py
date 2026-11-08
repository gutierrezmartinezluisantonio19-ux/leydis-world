import os
import random
from functools import wraps

import cloudinary
import cloudinary.uploader
from cloudinary import CloudinaryImage

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)

from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from extensions import db
from models import Cuenta, Foto, Mensaje


MENSAJES_INICIALES = [
    "Eres una de las cosas más bonitas que me ha pasado. ❤️",
    "Si pudiera elegir nuevamente, volvería a elegirte. 💗",
    "Mi lugar favorito siempre será donde estés tú. 🎀",
    "Nunca olvides lo especial que eres para mí. 🌷",
    "Entre millones de personas, mi corazón te eligió a ti. 💕",
    "Quiero seguir creando recuerdos bonitos contigo. 🥹",
    "Eres mi casualidad favorita. ❤️",
    "Este pequeño mundo siempre tendrá un lugar para ti. 🎀"
]

EXTENSIONES = {"png", "jpg", "jpeg", "webp"}


def crear_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

    db.init_app(app)
    cloudinary.config(secure=True)

    with app.app_context():
        db.create_all()

        admin = Cuenta.query.filter_by(rol="admin").first()
        leydi = Cuenta.query.filter_by(rol="leydi").first()

        admin_usuario = os.getenv("ADMIN_USER", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "")
        leydi_password = os.getenv("LEYDI_PASSWORD", "")

        if not admin:
            admin = Cuenta(
                usuario=admin_usuario,
                password_hash=generate_password_hash(
                    admin_password or "cambiar-esto"
                ),
                rol="admin"
            )
            db.session.add(admin)

        if not leydi:
            leydi = Cuenta(
                usuario="leydi",
                password_hash=generate_password_hash(
                    leydi_password or "cambiar-esto"
                ),
                rol="leydi"
            )
            db.session.add(leydi)

        if os.getenv("RESET_CREDENTIALS", "false").lower() == "true":
            if admin_password:
                admin.usuario = admin_usuario
                admin.password_hash = generate_password_hash(admin_password)

            if leydi_password:
                leydi.password_hash = generate_password_hash(leydi_password)

        if Mensaje.query.count() == 0:
            for texto in MENSAJES_INICIALES:
                db.session.add(Mensaje(contenido=texto))

        db.session.commit()

    @app.context_processor
    def funciones_fotos():
        def foto_url(imagen):
            ruta_local = os.path.join(
                app.static_folder, "uploads", imagen
            )

            if os.path.isfile(ruta_local):
                return url_for(
                    "static",
                    filename="uploads/" + imagen
                )

            return CloudinaryImage(imagen).build_url(secure=True)

        return {"foto_url": foto_url}

    def requiere_rol(rol):
        def decorador(funcion):
            @wraps(funcion)
            def verificar(*args, **kwargs):
                if session.get("rol") != rol:
                    return redirect(url_for("acceso"))
                return funcion(*args, **kwargs)
            return verificar
        return decorador

    @app.route("/")
    def inicio():
        return render_template("index.html")

    @app.route("/acceso")
    def acceso():
        return render_template("login.html")

    @app.route("/login", methods=["POST"])
    def login():
        password = request.form.get("password", "")
        rol = request.form.get("rol", "")

        if rol not in ("admin", "leydi"):
            flash("Selecciona quién desea entrar.")
            return redirect(url_for("acceso"))

        cuenta = Cuenta.query.filter_by(rol=rol).first()

        if cuenta and check_password_hash(cuenta.password_hash, password):
            session.clear()
            session["rol"] = cuenta.rol
            session["usuario"] = cuenta.usuario

            if rol == "admin":
                return redirect(url_for("admin"))

            return redirect(url_for("privado"))

        flash("Contraseña incorrecta. Comprueba que esté bien escrita.")
        return redirect(url_for("acceso"))

    @app.route("/privado")
    @requiere_rol("leydi")
    def privado():
        fotos = Foto.query.order_by(Foto.fecha.desc()).all()
        mensajes = Mensaje.query.all()

        mensaje = random.choice(mensajes).contenido if mensajes else (
            "Eres muy especial para mí. ❤️"
        )

        return render_template(
            "privado.html",
            fotos=fotos,
            mensaje=mensaje
        )

    @app.route("/admin")
    @requiere_rol("admin")
    def admin():
        fotos = Foto.query.order_by(Foto.fecha.desc()).all()
        mensajes = Mensaje.query.order_by(Mensaje.fecha.desc()).all()

        return render_template(
            "admin.html",
            fotos=fotos,
            mensajes=mensajes
        )

    @app.route("/subir-foto", methods=["POST"])
    @requiere_rol("admin")
    def subir_foto():
        archivo = request.files.get("foto")
        descripcion = request.form.get("descripcion", "").strip()

        if not archivo or not archivo.filename:
            flash("Selecciona una fotografía.")
            return redirect(url_for("admin"))

        extension = archivo.filename.rsplit(".", 1)[-1].lower()

        if extension not in EXTENSIONES:
            flash("Formato no permitido. Usa JPG, PNG o WEBP.")
            return redirect(url_for("admin"))

        try:
            resultado = cloudinary.uploader.upload(
                archivo,
                folder="leydis_world"
            )

            foto = Foto(
                imagen=resultado["public_id"],
                descripcion=descripcion
            )

            db.session.add(foto)
            db.session.commit()

            flash("¡Fotografía guardada correctamente! ❤️")

        except Exception as error:
            db.session.rollback()
            print("ERROR AL SUBIR FOTO:", error)
            flash("No se pudo subir la fotografía. Revisa Cloudinary.")

        return redirect(url_for("admin"))

    @app.route("/eliminar-foto/<int:id>", methods=["POST"])
    @requiere_rol("admin")
    def eliminar_foto(id):
        foto = db.session.get(Foto, id)

        if foto:
            ruta_local = os.path.join(
                app.static_folder, "uploads", foto.imagen
            )

            try:
                if os.path.isfile(ruta_local):
                    os.remove(ruta_local)
                else:
                    cloudinary.uploader.destroy(foto.imagen)

                db.session.delete(foto)
                db.session.commit()
                flash("Fotografía eliminada.")

            except Exception as error:
                db.session.rollback()
                print("ERROR AL ELIMINAR FOTO:", error)
                flash("No se pudo eliminar la fotografía.")

        return redirect(url_for("admin"))

    @app.route("/agregar-mensaje", methods=["POST"])
    @requiere_rol("admin")
    def agregar_mensaje():
        contenido = request.form.get("contenido", "").strip()

        if contenido:
            db.session.add(Mensaje(contenido=contenido))
            db.session.commit()
            flash("Mensaje agregado correctamente. 💗")

        return redirect(url_for("admin"))

    @app.route("/eliminar-mensaje/<int:id>", methods=["POST"])
    @requiere_rol("admin")
    def eliminar_mensaje(id):
        mensaje = db.session.get(Mensaje, id)

        if mensaje:
            db.session.delete(mensaje)
            db.session.commit()

        return redirect(url_for("admin"))

    @app.route("/cambiar-password", methods=["POST"])
    @requiere_rol("admin")
    def cambiar_password():
        nueva = request.form.get("password", "")

        if len(nueva) < 8:
            flash("La contraseña debe tener al menos 8 caracteres.")
            return redirect(url_for("admin"))

        cuenta = Cuenta.query.filter_by(rol="leydi").first()

        if not cuenta:
            flash("No se encontró la cuenta de Leydi.")
            return redirect(url_for("admin"))

        cuenta.password_hash = generate_password_hash(nueva)
        db.session.commit()

        flash("Contraseña de Leydi actualizada. ❤️")
        return redirect(url_for("admin"))

    @app.route("/salir")
    def salir():
        session.clear()
        return redirect(url_for("inicio"))

    @app.errorhandler(413)
    def archivo_demasiado_grande(error):
        flash("La fotografía supera el límite de 8 MB.")
        return redirect(url_for("admin"))

    return app


app = crear_app()

if __name__ == "__main__":
    app.run(debug=True)