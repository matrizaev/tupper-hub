from app import db
from flask import redirect, flash, render_template, request, url_for, Response, jsonify
from flask_login import current_user, login_required
from app.main import bp
import uuid
from app.models import User, Store
from app.ecwid import EcwidAPI
from app.main.forms import AddStoreForm

@bp.route('/')
@bp.route('/index/')
@login_required
def ShowIndex():
	api = EcwidAPI(client_id = current_user.client_id, client_secret = current_user.client_secret, partners_key = current_user.partners_key)
	form = AddStoreForm()
	stores_info = list()
	for store in current_user.stores:
		info = api.GetStoreInfo(store.id)
		info['orders_count'] = store.orders_count
		stores_info.append(info)
	return render_template('index.html', stores_info = stores_info, form = form)
	
@bp.route('/add', methods=['POST'])
@login_required
def AddStore():
	form = AddStoreForm(request.form)
	if form.validate_on_submit():
		api = EcwidAPI(client_id = current_user.client_id, client_secret = current_user.client_secret, partners_key = current_user.partners_key)
		store_id = api.CreateStore(name = form.name.data, email = form.email.data, password = form.password.data, plan = 'J_PUSHKIND_FREEDEMO')
		token = api.GetStoreToken(store_id)['access_token']
		store = Store(id = store_id, token = token, user_id = current_user.id)
		db.session.add(store)
		db.session.commit()
		flash('Магазин успешно добавлен.')
	else:
		for error in form.count.errors + form.discount.errors:
			flash(error)
	return redirect(url_for('main.ShowIndex'))

@bp.route('/delete/<store_id>', methods=['POST'])
@login_required
def DeleteStore(store_id):
	store = Store.query.filter(Store.id == store_id, store.user_id == current_user.id).first()
	if store:
		api = EcwidAPI(client_id = current_user.client_id, client_secret = current_user.client_secret, partners_key = current_user.partners_key)
		if api.DeleteStore(store_id):
			db.session.delete(store)
			db.session.commit()
			flash('Магазин успешно удалён.')
		else:
			flash('Не удалось удалить магазин.')
	else:
		flash('Магазин не найден.')
	return redirect(url_for('main.ShowIndex'))	
	