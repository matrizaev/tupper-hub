from flask import render_template, redirect, url_for, flash, request
from app import db
from app.auth import bp
from flask_login import login_user, logout_user, current_user
from werkzeug.urls import url_parse
from app.auth.forms import LoginForm, RegistrationForm
from app.models import User, Store
from app.ecwid import EcwidAPI

@bp.route('/login/', methods = ['GET', 'POST'])
def PerformLogin():
	if current_user.is_authenticated:
		return redirect(url_for('main.ShowIndex'))
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email = form.email.data).first()
		if user is None or not user.CheckPassword(form.password.data):
			flash('Некорректный логин или пароль')
			return render_template ('auth/login.html', form = form)
		login_user(user, remember=form.remember_me.data)
		next_page = request.args.get('next')
		if not next_page or url_parse(next_page).netloc != '':
			next_page = url_for('main.ShowIndex')
		return redirect(next_page)
	return render_template ('auth/login.html', form = form)

@bp.route('/register/', methods = ['GET', 'POST'])
def PerformRegistration():
	if current_user.is_authenticated:
		return redirect(url_for('main.ShowIndex'))
	form = RegistrationForm()
	if form.validate_on_submit():
		api = EcwidAPI(client_id = form.client_id.data, client_secret = form.client_secret.data, partners_key = form.partners_key.data)
		try:
			token = api.GetStoreToken(form.hub_id.data)['access_token']
			store_info = api.GetStoreInfo(form.hub_id.data)
		except:
			flash('Введённые API ключи не действительны.')
			return render_template ('auth/register.html', form = form)
		user = User(email = form.email.data, hub_id = form.hub_id.data, client_id = form.client_id.data, client_secret = form.client_secret.data, partners_key = form.partners_key.data, token = token)
		user.SetPassword(form.password.data)		
		db.session.add(user)
		db.session.commit()
		flash ('Теперь вы можете войти.')
		return redirect(url_for('auth.PerformLogin'))
	return render_template ('auth/register.html', form = form)

@bp.route('/logout/')
def PerformLogout():
	logout_user()
	return redirect(url_for('auth.PerformLogin'))