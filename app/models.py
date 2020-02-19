from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import login
from hashlib import md5
from flask import url_for
from datetime import datetime

from requests import post, get, delete, put
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

_REST_API_URL = 'https://app.ecwid.com/api/v3/{store_id}/{endpoint}'
_PARTNERS_API_URL = 'https://my.ecwid.com/resellerapi/v1/'
_OAUTH_URL = 'https://my.ecwid.com/api/oauth/token/'

_ALLOWED_PRODUCTS_FIELDS = ['sku', 'thumbnailUrl', 'unlimited', 'inStock', 'name', 'price', 'isShippingRequired', 'weight',
							'enabled', 'options', 'imageUrl', 'smallThumbnailUrl', 'hdThumbnailUrl', 'originalImageUrl', 'originalImage',
							'description', 'nameTranslated', 'quantity', 'wholesalePrices', 'compareToPrice', 'tax', 'productClassId',
							'warningLimit', 'fixedShippingRateOnly', 'fixedShippingRate', 'shipping', 'descriptionTranslated',
							'attributes', 'dimensions', 'categoryIds']

_DISALLOWED_PRODUCTS_FIELDS = ['id', 'categories', 'defaultCategoryId', 'relatedProducts', 'combinations', 'url', 'productClassId',
							   'defaultCombinationId']

_DISALLOWED_CATEGORIES_FIELDS = ['id', 'url', 'productCount']

@login.user_loader
def load_user(id):
	return User.query.get(int(id))
	
class User(UserMixin, db.Model):
	id  = db.Column(db.Integer, primary_key = True)
	email	= db.Column(db.String(120), index = True, unique = True, nullable=False)
	password = db.Column(db.String(128), nullable=False)
	stores = db.relationship('Store', backref = 'user')
	products = db.relationship('Product', backref = 'user')
	partners_key = db.Column(db.String(128), nullable=False)
	client_id = db.Column(db.String(128), nullable=False)
	client_secret = db.Column(db.String(128), nullable=False)
	hub_id = db.Column(db.Integer, unique = True, nullable=False)
	token = db.Column(db.String(128), nullable=False)
	orders_date = db.Column(db.DateTime,nullable=False, default=datetime.utcnow)
	
	def __repr__(self):
		return '<User {}>'.format(self.email)
	
	def SetPassword(self, password):
		self.password = generate_password_hash(password)
		
	def CheckPassword(self, password):
		return check_password_hash(self.password, password)
		
	def GetAvatar(self, size):
		digest = md5(self.email.lower().encode('utf-8')).hexdigest()
		return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, size)
	
	def EcwidCreateStore(self, name, email, password, plan):
		'''Create store using Partners API, returns store_id'''
		payload = {'name':name, 'email':email, 'password':password, 'plan':plan, 'key':self.partners_key}
		params = {'register':'y'}
		response = post(urljoin(_PARTNERS_API_URL, 'register'), data = payload, params = params)
		if response.status_code == 409:
			raise Exception('Электронный адрес уже используется.')
		elif response.status_code == 400:
			raise Exception('Некорретный электронный адрес.')
		elif response.status_code == 403:
			raise Exception('Некорретный ключ partners_key.')
		elif response.status_code != 200:
			raise Exception('Неизвестная ошибка API.')
		xml = ET.fromstring(response.text)
		return int(xml.text)
	
	def EcwidTestPartnersKey(self):
		params = {'store.id':self.hub_id, 'key':self.partners_key}
		response = get(urljoin(_PARTNERS_API_URL, 'stores'), params = params)
		if response.status_code != 200:
			raise Exception('Неизвестная ошибка API.')
		return ET.fromstring(response.text)
		
	def EcwidGetStoreToken(self, store_id):
		'''Gets store token using REST API, returns JSON'''
		payload = {'client_id':self.client_id, 'client_secret':self.client_secret, 'grant_type':'authorization_code'}
		response = post(urljoin(_OAUTH_URL, str(store_id)), data = payload)
		if response.status_code != 200:
			raise Exception('Неизвестная ошибка API.')
		return response.json()
		
	def EcwidDeleteStore(self, store_id):
		'''Removes store using Partners API, returns Boolean'''
		payload = {'ownerid':store_id, 'key':self.partners_key}
		response = post(urljoin(_PARTNERS_API_URL, 'delete'), data = payload)
		if response.status_code == 403:
			raise Exception('Недостаточно прав на удаление этого магазина.')
		elif response.status_code != 200:
			raise Exception('Неизвестная ошибка API.')

	def _EcwidGetErrorMessage(self, error):
		if error == 400:
			message = 'Неверные параметры запроса.'
		elif error == 402 or error == 403:
			message = 'Недостаточно прав на выполнение запроса.'
		elif error == 404:
			message = 'Пользователь, магазин или товар не найден.'
		elif error == 409:
			message = 'Значения полей товара не верные.'
		elif error == 415 or error == 422:
			message = 'Неверные тип запроса.'
		elif error != 200:
			message = 'Неизвестная ошибка API.'
		return '{}: {}'.format(error, message)

	def EcwidGetStoreEndpoint(self, store_id, token, endpoint, **kwargs):
		'''Gets store's endpoint using REST API, returns JSON'''
		params = {'token':token, **kwargs}
		response = get(_REST_API_URL.format(store_id = store_id,endpoint = endpoint), params = params)
		if response.status_code != 200:
			raise Exception(self._EcwidGetErrorMessage(response.status_code))
		result = response.json()
		received = result['count']
		while received < result['total']:
			params['offset'] = received
			response = get(_REST_API_URL.format(store_id = store_id,endpoint = endpoint), params = params)
			if response.status_code != 200:
				raise Exception(self._EcwidGetErrorMessage(response.status_code))
			next = response.json()
			received += result['count']
			result['items'] += next['items']
		result['total'] = received
		result['count'] = received
		return result
		
	def EcwidGetStoreInfo(self, store_id, token):
		'''Gets store's endpoint using REST API, returns JSON'''
		params = {'token':token}
		response = get(_REST_API_URL.format(store_id = store_id,endpoint = 'profile'), params = params)
		if response.status_code != 200:
			raise Exception(self._EcwidGetErrorMessage(response.status_code))
		return response.json()
		
	def EcwidGetStoreProducts(self, store_id, token, **kwargs):
		'''Gets store's products using REST API, returns JSON'''
		return self.EcwidGetStoreEndpoint(store_id, token, 'products', **kwargs)
	def EcwidGetStoreOrders(self, store_id, token, **kwargs):
		'''Gets store's orders using REST API, returns JSON'''
		return self.EcwidGetStoreEndpoint(store_id, token, 'orders', **kwargs)
	def EcwidGetStoreCategories(self, store_id, token, **kwargs):
		'''Gets store's categories using REST API, returns JSON'''
		return self.EcwidGetStoreEndpoint(store_id, token, 'categories', **kwargs)
	
	def EcwidSetStoreOrder(self, store_id, token, order):
		'''Sets store's order using REST API, returns JSON
		   sku must be store_id-product_sku'''
		params = {'token':token}
		response = post(_REST_API_URL.format(store_id = store_id,endpoint = 'orders'), json = order, params=params)
		if response.status_code != 200:
			raise Exception(self._EcwidGetErrorMessage(response.status_code))
		return response.json()

	def EcwidUpdateStoreProduct(self, store_id, token, template):
		'''Updates store's product using REST API, returns JSON'''
		params = {'token':token}
		product = {}
		template.pop('categoryIds', None)
		for key in _ALLOWED_PRODUCTS_FIELDS:
			if key in template:
				product[key] = template[key]
		store_product = self.EcwidGetStoreProducts(store_id, token, sku = product['sku'])
		if(store_product['count'] > 0):
			product_id = store_product['items'][0]['id']
			response = put(_REST_API_URL.format(store_id = store_id,endpoint = 'products/{}'.format(product_id)), json = product, params=params)
			result = response.json()
			if response.status_code != 200:
				raise Exception(self._EcwidGetErrorMessage(response.status_code))
			result = response.json()
		else:
			result = {}
		return result
				
	def EcwidDeleteStoreProduct(self, store_id, token, product_id):
		'''Deletes store's product using REST API, returns JSON'''
		params = {'token':token}
		response = delete(_REST_API_URL.format(store_id = store_id,endpoint = 'products/{}'.format(product_id)), params = params)
		if response.status_code != 200:
			raise Exception(self._EcwidGetErrorMessage(response.status_code))
		return response.json()
		
	def EcwidSetStoreProduct(self, store_id, token, template):
		'''Adds or updates store's product using REST API, returns JSON'''
		params = {'token':token}
		product = {}
		for key in _ALLOWED_PRODUCTS_FIELDS:
			if key in template:
				product[key] = template[key]
		store_product = self.EcwidGetStoreProducts(store_id, token, sku = product['sku'])
		if(store_product['count'] > 0):
			product_id = store_product['items'][0]['id']
			response = put(_REST_API_URL.format(store_id = store_id,endpoint = 'products/{}'.format(product_id)), json = product, params=params)
			result = response.json()
			result['id'] = product_id
		else:
			response = post(_REST_API_URL.format(store_id = store_id,endpoint = 'products'), json = product, params=params)
			result = response.json()
		if response.status_code != 200:
			raise Exception(self._EcwidGetErrorMessage(response.status_code))
		return result
		
	def EcwidSetStoreProductImage(self, store_id, token, product_id, img_url=None, data=None):
		'''Deletes store's product using REST API, returns JSON'''
		params = {'token':token}
		if img_url:
			params['externalUrl'] = img_url
		response = post(_REST_API_URL.format(store_id = store_id,endpoint = 'products/{}/image'.format(product_id)), params = params, data=data)
		if response.status_code != 200:
			raise Exception(self._EcwidGetErrorMessage(response.status_code))
		return response.json()
		
	def EcwidSetStoreCategory(self, store_id, token, category):
		'''Adds or updates store's category using REST API, returns JSON'''
		params = {'token':token}
		for key in _DISALLOWED_CATEGORIES_FIELDS:
			category.pop(key, None)
		response = post(_REST_API_URL.format(store_id = store_id,endpoint = 'categories'), json = category, params=params)
		if response.status_code != 200:
			raise Exception(self._EcwidGetErrorMessage(response.status_code))
		return response.json()

class Store(db.Model):
	id = db.Column(db.Integer, primary_key = True)
	token = db.Column(db.String(128), nullable=False)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
	orders_count = db.Column(db.Integer, nullable=False, default = 0, server_default='0')
	
class Product(db.Model):
	id = db.Column(db.Integer, primary_key = True)
	sku = db.Column(db.String(128), unique = True)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
	category = db.Column(db.Text, nullable=False)
	description = db.Column(db.Text, nullable=False)
	imageUrl = db.Column(db.String(128), nullable=False)
	price = db.Column(db.Float, nullable=False)
	name = db.Column(db.String(128), nullable=False)

	def ToDict(self):
		data = {
			'sku': self.sku,
			'name': self.name,
			'price': self.price,
			'description': self.description,
			'imageUrl': self.imageUrl,
			'category': self.category
		}
		return data
	
