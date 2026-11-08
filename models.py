from extensions import db
from datetime import datetime

class Cuenta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False)


class Foto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    imagen = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.String(255))
    fecha = db.Column(db.DateTime, default=datetime.utcnow)


class Mensaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)