from flask_wtf import FlaskForm
from wtforms import Form, SubmitField, StringField, PasswordField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Email
from flask_wtf.file import FileField, FileRequired, FileAllowed
	
class AddStoreForm(FlaskForm):
	name = StringField('ФИО', validators = [DataRequired(message='ФИО - обязательное поле.')])
	email = EmailField('Электронная почта', validators = [DataRequired(), Email()])
	password = PasswordField('Пароль', validators = [DataRequired()])
	plan = StringField('План', default = 'J_PUSHKIND_FREEDEMO', validators = [DataRequired(message='План - обязательное поле.')])
	city = StringField('Город', default = 'Москва', validators = [DataRequired(message='Город - обязательное поле.')])
	submit = SubmitField('Сохранить')
	
class UploadProductsForm(FlaskForm):
	products = FileField (label = 'Шаблон товаров', validators=[FileRequired(), FileAllowed(['csv'], 'Разрешены только CSV.')])
	submit = SubmitField('Загрузить')