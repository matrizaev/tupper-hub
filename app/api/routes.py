from app.api import bp
from flask import jsonify, request, Response
from app.api.auth import basic_auth
from app import db
from app.api.errors import BadRequest

'''
@bp.route('/stores/<int:id>', methods=['GET'])
@basic_auth.login_required
def GetStore(id):
	return jsonify(User.query.get_or_404(id).ToDict())
	
@bp.route('/stores/<int:id>', methods=['PUT'])
@basic_auth.login_required
def SetStore(id):
	user = User.query.get_or_404(id)
	data = request.get_json() or {}
	user.FromDict(data)
	return jsonify(user.ToDict())

@bp.route('/stores', methods=['GET'])
@basic_auth.login_required
def GetStores():
	page = request.args.get('page', 1, type=int)
	per_page = min(request.args.get('per_page', 10, type=int), 100)
	data = User.ToCollectionDict(User.query, page, per_page, 'api.GetStores')
	return jsonify(data)
	
@bp.route('/stores/<int:id>/products', methods=['GET'])
@basic_auth.login_required
def GetStoreProducts(id):
	page = request.args.get('page', 1, type=int)
	per_page = min(request.args.get('per_page', 10, type=int), 100)
	data = Product.ToCollectionDict(Product.query.filter(Product.store_id == id), page, per_page, 'api.GetStoreProducts', id=id)
	return jsonify(data)
	
@bp.route('/stores/<int:id>/orders', methods=['GET'])
@basic_auth.login_required
def GetStoreOrders(id):
	page = request.args.get('page', 1, type=int)
	per_page = min(request.args.get('per_page', 10, type=int), 100)
	data = Order.ToCollectionDict(Order.query.filter(Order.store_id == id), page, per_page, 'api.GetStoreOrders', id=id)
	return jsonify(data)
	
@bp.route('/core/products', methods=['GET'])
@basic_auth.login_required
def GetProducts():
	products = pd.read_sql(db.session.query((User.vendor_id + '-' + Product.sku).label('sku'), (User.section + '/' + Product.path).label('path'), Product.title, Product.price, Product.description, Product.picture).join(User, User.id == Product.store_id).statement, db.session.bind)
	csv = products.to_csv(sep = ';', index = False, encoding='utf-8')
	db.session.query(User).update({User.want_to_publish: ''})
	db.session.commit()
	return Response (csv, mimetype='text/csv', headers = {'Content-Disposition':'attachment;filename=core.csv'})
	
@bp.route('/stores/<int:id>/orders', methods=['POST'])
@basic_auth.login_required
def PlaceOrder(id):
	user = User.query.get_or_404(id)
	data = request.get_json() or {}
	order = Order()
	order.store_id = id
	for field in ['address', 'city', 'email', 'country', 'phone', 'comment', 'province', 'postal_code', 'name']:
		if not field in data:
			return BadRequest('Field {} is missing.'.format(field))
		else:
			setattr(order, field, data[field])
	if not 'products' in data:
		return BadRequest('Field products is missing.')
	products_sku = [x.strip() for x in data['products'].split(',') if x.strip() != '']
	products_sku = Counter(products_sku)
	orderProducts = list()
	for sku in products_sku:
		p = Product.query.filter(Product.sku == sku, Product.store_id == id).first()
		if p is None:
			return BadRequest('Wrong product sku {}.'.format(sku))
		op = OrderProducts (count=products_sku[sku], price=p.price, sku=sku, title=p.title, picture=p.picture, description=p.description)
		db.session.add(op)
		orderProducts.append(op)
	order.products = orderProducts
	db.session.add(order)
	db.session.commit()
	return jsonify(order.ToDict())
	
@bp.route('/orders/<int:id>', methods=['GET'])
@basic_auth.login_required
def GetOrder(id):
	return jsonify(Order.query.get_or_404(id).ToDict())
	
@bp.route('/orders', methods=['GET'])
@basic_auth.login_required
def GetOrders():
	page = request.args.get('page', 1, type=int)
	per_page = min(request.args.get('per_page', 10, type=int), 100)
	data = Order.ToCollectionDict(Order.query, page, per_page, 'api.GetOrders')
	return jsonify(data)
'''