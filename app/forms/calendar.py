from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired


class CalendarSettingsForm(FlaskForm):
    calendar_id = SelectField("Calendário sincronizado", validators=[DataRequired()])
    sync_enabled = BooleanField("Bloquear oportunidades quando houver conflito", default=True)
    create_booking_events = BooleanField("Criar evento quando uma reserva IDDUN for confirmada", default=True)
    submit = SubmitField("Salvar integração")
