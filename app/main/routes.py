from app import db
from flask import redirect, flash, render_template, request, url_for, Response, jsonify
from flask_login import current_user, login_required
from app.main import bp
from app.models import User, Store
from app.main.forms import AddStoreForm
from app.api.routes import ProcessHubOrders, ProcessHubProducts, CleanDeletedProducts, UpdateHubProducts
from datetime import datetime

@bp.route('/')
@bp.route('/index/')
@login_required
def ShowIndex():
	form = AddStoreForm()
	stores_info = list()
	for store in current_user.stores:
		try:
			info = current_user.EcwidGetStoreInfo(store.id, store.token)
		except Exception as e:
			flash('Ошибка с магазином {}: {}'.format(store.id, e))
			continue
		info['orders_count'] = store.orders_count
		stores_info.append(info)
	return render_template('index.html', stores_info = stores_info, form = form)
	
@bp.route('/add', methods=['POST'])
@login_required
def AddStore():
	form = AddStoreForm(request.form)
	if form.validate_on_submit():
		try:
			store_id = current_user.EcwidCreateStore(name = form.name.data, email = form.email.data, password = form.password.data, plan = form.plan.data)
			token = current_user.EcwidGetStoreToken(store_id)['access_token']
		except Exception as e:
			flash('Ошибка API: {}'.format(e))
			return redirect(url_for('main.ShowIndex'))
		store = Store(id = store_id, token = token, user_id = current_user.id)
		db.session.add(store)
		db.session.commit()
		flash('Магазин успешно добавлен.')
	else:
		for error in form.count.errors + form.discount.errors:
			flash(error)
	return redirect(url_for('main.ShowIndex'))

@bp.route('/delete/<store_id>', methods=['GET'])
@login_required
def DeleteStore(store_id):
	store = Store.query.filter(Store.id == store_id, Store.user_id == current_user.id).first()
	if store:
		try:
			current_user.EcwidDeleteStore(store_id)
		except Exception as e:
			flash('Ошибка API: {}'.format(e))
			return redirect(url_for('main.ShowIndex'))
		db.session.delete(store)
		db.session.commit()
		flash('Магазин успешно удалён.')
	else:
		flash('Магазин не найден.')
	return redirect(url_for('main.ShowIndex'))

@bp.route('/show/<store_id>', methods=['GET'])
@login_required
def ShowStore(store_id):
	store = Store.query.filter(Store.id == store_id, Store.user_id == current_user.id).first()
	if store:
		orders = current_user.EcwidGetStoreOrders(store_id, store.token, limit = 3)
		products = current_user.EcwidGetStoreProducts(store_id, store.token)
		return render_template('store.html', orders = orders['items'])
	else:
		flash('Магазин не найден.')
	return redirect(url_for('main.ShowIndex'))

@bp.route('/process_orders/')
@login_required
def ProcessOrders():
	orders_processed = ProcessHubOrders(current_user)
	now = datetime.now()
	flash('Процедура успешно проведена: ' + now.strftime("%m/%d/%Y, %H:%M:%S"))
	flash('Создано {} заказов.'.format(orders_processed))
	return redirect(url_for('main.ShowIndex'))	

@bp.route('/process_products/')
@login_required
def ProcessProducts():
	for store in current_user.stores:
		ProcessHubProducts(current_user, store)
	now = datetime.now()
	flash('Процедура успешно проведена: ' + now.strftime("%m/%d/%Y, %H:%M:%S"))
	return redirect(url_for('main.ShowIndex'))	

@bp.route('/update_products/')
@login_required
def UpdateProducts():
	for store in current_user.stores:
		UpdateHubProducts(current_user, store)
	now = datetime.now()
	flash('Процедура успешно проведена: ' + now.strftime("%m/%d/%Y, %H:%M:%S"))
	return redirect(url_for('main.ShowIndex'))

@bp.route('/clean_products/')
@login_required
def CleanProducts():
	CleanDeletedProducts(current_user)
	now = datetime.now()
	flash('Процедура успешно проведена: ' + now.strftime("%m/%d/%Y, %H:%M:%S"))
	return redirect(url_for('main.ShowIndex'))