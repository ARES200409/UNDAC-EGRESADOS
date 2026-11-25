"""Blueprint de capacitaciones, eventos institucionales y centro de notificaciones."""

from flask import Blueprint

capacitaciones = Blueprint('capacitaciones', __name__)

from app.capacitaciones import routes  # noqa: E402, F401
