from flask_wtf import FlaskForm
from wtforms import Form, SubmitField, StringField, PasswordField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Email
	
class AddStoreForm(FlaskForm):
	name = StringField('Название', validators = [DataRequired(message='Название - обязательное поле.')])
	email = EmailField('Электронная почта', validators = [DataRequired(), Email()])
	password = PasswordField('Пароль', validators = [DataRequired()])
	submit = SubmitField('Сохранить')