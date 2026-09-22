from flask_wtf import FlaskForm
from wtforms import RadioField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


RATING_CHOICES = [(str(value), f"{value} estrela" if value == 1 else f"{value} estrelas") for value in range(5, 0, -1)]
RECOMMEND_CHOICES = [("yes", "Sim, recomendo"), ("no", "Não recomendo")]


class BookingReviewForm(FlaskForm):
    professional_rating = RadioField(
        "Como você avalia o atendimento profissional?",
        choices=RATING_CHOICES,
        validators=[DataRequired()],
    )
    professional_recommended = RadioField(
        "Você recomendaria este profissional?",
        choices=RECOMMEND_CHOICES,
        validators=[DataRequired()],
    )
    professional_comment = TextAreaField(
        "Conte como foi a experiência",
        validators=[Optional(), Length(max=1200)],
    )
    establishment_rating = RadioField(
        "Como você avalia o estabelecimento?",
        choices=RATING_CHOICES,
        validators=[Optional()],
    )
    establishment_recommended = RadioField(
        "Você recomendaria o estabelecimento?",
        choices=RECOMMEND_CHOICES,
        validators=[Optional()],
    )
    establishment_comment = TextAreaField(
        "Conte como foi o local",
        validators=[Optional(), Length(max=1200)],
    )
    submit = SubmitField("Publicar avaliação")
