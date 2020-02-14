from flask_wtf import FlaskForm
from wtforms import Form, SubmitField, StringField, PasswordField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Email
	
class AddStoreForm(FlaskForm):
	name = StringField('ФИО', validators = [DataRequired(message='ФИО - обязательное поле.')])
	email = EmailField('Электронная почта', validators = [DataRequired(), Email()])
	password = PasswordField('Пароль', validators = [DataRequired()])
	plan = StringField('План', default = 'J_PUSHKIND_FREEDEMO', validators = [DataRequired(message='План - обязательное поле.')]) 
	submit = SubmitField('Сохранить')