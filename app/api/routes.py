from app.api import bp
from flask import jsonify, request, Response, g
from app.api.auth import basic_auth
from app import db
from app.api.errors import BadRequest
from datetime import datetime
from app.models import User, Store
from requests import get

_DISALLOWED_ORDERS_ITEM_FIELDS = ['productId', 'id', 'categoryId']
_DISALLOWED_ORDERS_FIELDS = ['vendorOrderNumber', 'customerId']

@bp.route('/orders/', methods=['GET'])
@basic_auth.login_required
def ProcessHubOrdersRequest():
	user = User.query.get_or_404(g.user_id)
	ProcessHubOrders(user)
	return jsonify({'result':'success'})

def ProcessHubOrders(user):
	orders = user.EcwidGetStoreOrders(user.hub_id, user.token, createdFrom = int(user.orders_date.timestamp()))
	user.orders_date = datetime.now()
	db.session.commit()
	orders_processed = 0
	for order in orders['items']:
		for key in _DISALLOWED_ORDERS_FIELDS:
			order.pop(key, None)
		for product in order['items']:
			for key in _DISALLOWED_ORDERS_ITEM_FIELDS:
				product.pop(key, None)
		for store in user.stores:
			products = list()
			totalPrice = 0
			for product in order['items']:
				sku = product['sku'].split('-')
				if len(sku) > 1 and sku[0] == str(store.id):
					product_new = product.copy()
					product_new['sku'] = sku[1]
					products.append(product_new)
					totalPrice += product_new['price'] * product_new['quantity']
			if len(products) == 0:
				continue
			items = order['items']
			order['items'] = products
			order['subtotal'] = totalPrice
			order['total'] = totalPrice		
			result = user.EcwidSetStoreOrder(store.id, store.token, order)
			if 'id' in result:
				store.orders_count += 1
				orders_processed += 1
			order['items'] = items
			db.session.add(store)
	db.session.commit()
	return orders_processed

@bp.route('/products/', methods=['GET'])
@basic_auth.login_required
def ProcessHubProductsRequest():
	user = User.query.get_or_404(g.user_id)
	ProcessHubProducts2(user)
	return jsonify({'result':'success'})

def ProcessHubProducts(user, store, parent = 0, hub_parent = 0):
	categories = user.EcwidGetStoreCategories(store.id, store.token, parent = parent)
	products = user.EcwidGetStoreProducts(store.id, store.token, category = parent)
	#ProcessHubProducts
	for product in products['items']:
		product['sku'] = '{}-{}'.format(store.id, product['sku'])
		if hub_parent != 0:
			product['categoryIds'] = [hub_parent]
		else:
			product['categoryIds'] = []
		product_id = user.EcwidSetStoreProduct(user.hub_id, user.token, product)['id']
		if 'imageUrl' in product:
			user.EcwidSetStoreProductImage(user.hub_id, user.token, product_id, product['imageUrl'])
	#ProcessStoreCategories
	hub_categories = user.EcwidGetStoreCategories(user.hub_id, user.token, parent = hub_parent)
	for category in categories['items']:
		hub_category_id = None
		for hub_category in hub_categories['items']:
			if category['name'] == hub_category['name']:
				hub_category_id = hub_category['id']
				break
		if not hub_category_id:
			hub_category = user.EcwidSetStoreCategory(user.hub_id, user.token, {'parentId' : hub_parent, 'name' : category['name']})
			hub_category_id = hub_category['id']
		ProcessHubProducts(user, store, category['id'], hub_category_id)
	return True


def CreateStoreCategoriesPath(user, store_id, store_token, path):
	path = path.split('/')
	parent = 0
	for cat in path:
		categories = user.EcwidGetStoreCategories(store_id, store_token, parent = parent)
		for item in categories['items']:
			if cat == item['name']:
				parent = item['id']
				found = True
				break
		else:
			item = user.EcwidSetStoreCategory(store_id, store_token, {'parentId' : parent, 'name' : cat})
			parent = item['id']
	return parent
	
def ProcessHubProducts2(user):
	for product in user.products:
		parent = CreateStoreCategoriesPath(user, user.hub_id, user.token, product.category)
		d = product.ToDict()
		d['categoryIds'] = [parent]
		response = get(d['imageUrl'])
		for store in user.stores:
			store_products = user.EcwidGetStoreProducts(store.id, store.token, sku = product.sku)
			if(store_products['count'] == 0):
				continue
			d['price'] = store_products['items'][0]['price']
			d['showOnFrontpage'] = 3
			d['sku'] = '{}-{}'.format(store.id, product.sku)
			product_id = user.EcwidSetStoreProduct(user.hub_id, user.token, d)['id']
			user.EcwidSetStoreProductImage(user.hub_id, user.token, product_id, data = response.content)

@bp.route('/updates/', methods=['GET'])
@basic_auth.login_required
def UpdateHubProductsRequest():
	user = User.query.get_or_404(g.user_id)
	for store in user.stores:
		UpdateHubProducts(user, store)
	return jsonify({'result':'success'})
		
def UpdateHubProducts(user, store):
	products = user.EcwidGetStoreProducts(store.id, store.token)
	for product in products['items']:
		product['sku'] = '{}-{}'.format(store.id, product['sku'])
		user.EcwidUpdateStoreProduct(user.hub_id, user.token, product)
	return True

@bp.route('/clean/', methods=['GET'])
@basic_auth.login_required
def CleanDeletedProductsRequest():
	user = User.query.get_or_404(g.user_id)
	CleanDeletedProducts(user)
	return jsonify({'result':'success'})

def CleanDeletedProducts(user):
	products = user.EcwidGetStoreProducts(user.hub_id, user.token)
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
				store_products = user.EcwidGetStoreProducts(store.id, store.token, sku = sku)
				if store_products['total'] == 0:
					user.EcwidDeleteStoreProduct(user.hub_id, user.token, product['id'])
	return True
	
@bp.route('/fillup/<int:store_id>', methods=['GET'])
@basic_auth.login_required
def FillUpProductsRequest(store_id):
	user = User.query.get_or_404(g.user_id)
	store = Store.query.filter(Store.user_id == user.id, Store.id == store_id).first()
	if not store:
		return jsonify({'result':'not found'})
	FillUpProducts(user, store)
	return jsonify({'result':'success'})
	
def FillUpProducts(user, store):
	for product in user.products:
		parent = CreateStoreCategoriesPath(user, store.id, store.token, product.category)
		d = product.ToDict()
		d['categoryIds'] = [parent]
		d['showOnFrontpage'] = 3
		product_id = user.EcwidSetStoreProduct(store.id, store.token, d)['id']
		response = get(d['imageUrl'])
		user.EcwidSetStoreProductImage(store.id, store.token, product_id, data = response.content)
		
	