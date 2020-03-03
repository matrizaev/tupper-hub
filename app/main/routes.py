from app import db
from flask import redirect, flash, render_template, request, url_for, Response, jsonify
from flask_login import current_user, login_required
from app.main import bp
from app.models import User, Store, Product, _DEFAULT_STORE_PROFILE
from app.main.forms import AddStoreForm, UploadProductsForm
from app.api.routes import ProcessHubOrders, ProcessHubProducts2, CleanDeletedProducts, UpdateHubProducts, FillUpProducts
from datetime import datetime
import pandas as pd


@bp.route('/')
@bp.route('/index/')
@login_required
def ShowIndex():
	add_form = AddStoreForm()
	upload_form = UploadProductsForm()
	stores_info = list()
	for store in current_user.stores:
		try:
			info = current_user.EcwidGetStoreProfile(store.id, store.token)
		except Exception as e:
			flash('Ошибка с магазином {}: {}'.format(store.id, e))
			continue
		info['orders_count'] = store.orders_count
		stores_info.append(info)
	return render_template('index.html', stores_info = stores_info, add_form = add_form, upload_form = upload_form)
	
@bp.route('/add', methods=['POST'])
@login_required
def AddStore():
	form = AddStoreForm(request.form)
	if form.validate_on_submit():
		try:
			store_id = current_user.EcwidCreateStore(name = form.name.data, email = form.email.data, password = form.password.data, plan = form.plan.data,
													 defaultlanguage='ru')
			token = current_user.EcwidGetStoreToken(store_id)['access_token']
		except Exception as e:
			flash('Ошибка API: {}'.format(e))
			return redirect(url_for('main.ShowIndex'))
		store = Store(id = store_id, token = token, user_id = current_user.id)
		db.session.add(store)
		db.session.commit()
		flash('Магазин успешно добавлен.')
		try:
			template = _DEFAULT_STORE_PROFILE
			template['city'] = form.city.data
			current_user.EcwidUpdateStoreProfile(store_id, token, template)
		except Exception as e:
			flash('Ошибка UpdateProfile: {}'.format(e))
	else:
		for error in form.name.errors + form.email.errors + form.password.errors + form.plan.errors + form.city.errors:
			flash(error)
	return redirect(url_for('main.ShowIndex'))

@bp.route('/delete/<int:store_id>', methods=['GET'])
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

@bp.route('/show/<int:store_id>', methods=['GET'])
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
	flash('Процедура успешно проведена: ' + now.strftime("%d-%m-%Y, %H:%M:%S"))
	flash('Создано {} заказов.'.format(orders_processed))
	return redirect(url_for('main.ShowIndex'))	

@bp.route('/process_products/')
@login_required
def ProcessProducts():
	ProcessHubProducts2(current_user)
	now = datetime.now()
	flash('Процедура успешно проведена: ' + now.strftime("%d-%m-%Y, %H:%M:%S"))
	return redirect(url_for('main.ShowIndex'))	

@bp.route('/update_products/')
@login_required
def UpdateProducts():
	for store in current_user.stores:
		UpdateHubProducts(current_user, store)
	now = datetime.now()
	flash('Процедура успешно проведена: ' + now.strftime("%d-%m-%Y, %H:%M:%S"))
	return redirect(url_for('main.ShowIndex'))

@bp.route('/clean_products/')
@login_required
def CleanProducts():
	CleanDeletedProducts(current_user)
	now = datetime.now()
	flash('Процедура успешно проведена: ' + now.strftime("%d-%m-%Y, %H:%M:%S"))
	return redirect(url_for('main.ShowIndex'))
	
@bp.route('/upload_products/', methods=['POST'])
@login_required
def UploadProducts():
	form = UploadProductsForm()
	if form.validate_on_submit():
		try:
			df = pd.read_csv(form.products.data, sep = ';')
			df = df.groupby('sku', as_index = False).agg({'category': lambda s: max(s, key=len), 'name': 'first', 'price':'first', 'description':'first', 'imageUrl':'first'})
			df['user_id'] = current_user.id
			df.fillna(value={'description' : '', 'price' : 0}, inplace = True)
			df['price'] = df['price'].astype('float64')
			Product.query.filter(Product.user_id == current_user.id).delete()
			db.session.commit()
			df.to_sql(name = 'product', con = db.engine, if_exists = 'append', index = False)
			flash('Файл успешно загружен.')
		except:
			flash('Не удалось обработать файл.')
	else:
		flash(form.products.error)
	return redirect(url_for('main.ShowIndex'))
	
@bp.route('/fillup_store/<int:store_id>')
@login_required
def FillUpStore(store_id):
	store = Store.query.filter(Store.user_id == current_user.id, Store.id == store_id).first()
	if not store:
		flash('Магазин не найден.')
	else:
		try:
			FillUpProducts(current_user, store)
			now = datetime.now()
			flash('Процедура успешно проведена: ' + now.strftime("%d-%m-%Y, %H:%M:%S"))
		except Exception as e:
			flash('Ошибка API: {}'.format(e))
	return redirect(url_for('main.ShowIndex'))