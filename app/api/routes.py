from app.api import bp
from flask import jsonify, request, Response, g
from app.api.auth import basic_auth
from app import db
from app.api.errors import BadRequest
from datetime import datetime
from app.models import User, Store

@bp.route('/orders/', methods=['GET'])
@basic_auth.login_required
def ProcessHubOrdersRequest():
	user = User.query.get_or_404(g.user_id)
	ProcessHubOrders(user)
	return jsonify({'result':'success'})

def ProcessHubOrders(user):
	api = user.GetEcwidAPI()
	orders = api.GetStoreOrders(user.hub_id, user.token, createdFrom = int(user.orders_date.timestamp()))
	user.orders_date = datetime.now()
	orders_processed = 0
	for order in orders['items']:
		for store in user.stores:
			result = api.SetStoreOrder(store.id, store.token, order)
			if 'id' in result:
				store.orders_count += 1
				orders_processed += 1
	db.session.commit()
	return True

@bp.route('/products/', methods=['GET'])
@basic_auth.login_required
def ProcessHubProductsRequest():
	user = User.query.get_or_404(g.user_id)
	for store in user.stores:
		ProcessHubProducts(user, store)
	return jsonify({'result':'success'})
		
def ProcessHubProducts(user, store, parent = 0, hub_parent = 0):
	api = user.GetEcwidAPI()
	categories = api.GetStoreCategories(store.id, store.token, parent = parent)
	products = api.GetStoreProducts(store.id, store.token, category = parent)
	#ProcessHubProducts
	for product in products['items']:
		product['sku'] = '{}-{}'.format(store.id, product['sku'])
		if hub_parent != 0:
			product['categoryIds'] = [hub_parent]
		else:
			product['categoryIds'] = []
		product_id = api.SetStoreProduct(user.hub_id, user.token, product)['id']
		if 'imageUrl' in product:
			api.SetStoreProductImage(user.hub_id, user.token, product_id, product['imageUrl'])
	#ProcessStoreCategories
	hub_categories = api.GetStoreCategories(user.hub_id, user.token, parent = hub_parent)
	for category in categories['items']:
		hub_category_id = None
		for hub_category in hub_categories['items']:
			if category['name'] == hub_category['name']:
				hub_category_id = hub_category['id']
				break
		if not hub_category_id:
			hub_category = api.SetStoreCategory(user.hub_id, user.token, {'parentId' : hub_parent, 'name' : category['name']})
			hub_category_id = hub_category['id']
		ProcessHubProducts(user, store, category['id'], hub_category_id)
	return True

@bp.route('/clean/', methods=['GET'])
@basic_auth.login_required
def CleanDeletedProductsRequest():
	user = User.query.get_or_404(g.user_id)
	CleanDeletedProducts(user)
	return jsonify({'result':'success'})

def CleanDeletedProducts(user):
	api = user.GetEcwidAPI()
	products = api.GetStoreProducts(user.hub_id, user.token)
	for product in products['items']:
		sku = product['sku'].split('-')
		if len(sku) > 1:
			try:
				store_id = int(sku[0])
			except:
				continue
			sku = '-'.join(sku[1:])
			store = Store.query.filter(Store.user_id == user.id, Store.id == store_id).first()
			if store:
				store_products = api.GetStoreProducts(store.id, store.token, sku = sku)
				if store_products['total'] == 0:
					api.DeleteStoreProduct(user.hub_id, user.token, product['id'])
	return True