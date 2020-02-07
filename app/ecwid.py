from requests import post, get, delete, put
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

class InvalidAPIKeys(Exception):
    pass

class InvalidStore(Exception):
    pass
	
class InvalidOrder(Exception):
    pass

class EcwidAPI():
	
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

	_DISALLOWED_ORDERS_FIELDS = ['vendorOrderNumber', 'customerId']

	_DISALLOWED_CATEGORIES_FIELDS = ['id', 'url', 'productCount']

	_DISALLOWED_ORDERS_ITEM_FIELDS = ['productId', 'id', 'categoryId']
	
	def __init__(self, partners_key, client_id, client_secret):
		self.partners_key = partners_key
		self.client_id = client_id
		self.client_secret = client_secret
		
	def GetStoreInfo(self, store_id):
		'''Gets store information using Partners API, returns dict'''
		params = {'storeid' : store_id, 'key' : self.partners_key}
		response = get(urljoin(self._PARTNERS_API_URL, 'stores'), params = params)
		if response.status_code != 200:
			raise InvalidAPIKeys
		xml = ET.fromstring(response.text)
		store_info = {}
		for store in xml.findall('./stores'):
			id = store.find('id')
			if id.text == str(store_id):
				store_info['id'] = store_id
				store_info['name']  = store.find('name').text
				store_info['email'] = store.find('email').text
				store_info['plan'] = store.find('planName').text
		if not 'name' in store_info:
			raise InvalidStore
		return store_info
		
	def GetStoresByEmail(self, email):
		'''Gets store registered to the email using Partners API, returns XML'''
		payload = {'email.substring':email, 'key':self.partners_key}
		response = post(urljoin(self._PARTNERS_API_URL, 'stores'), data = payload)
		if response.status_code != 200:
			raise InvalidAPIKeys
		return ET.fromstring(response.text)

	def GetStoreEndpoint(self, store_id, token, endpoint, **kwargs):
		'''Gets store's orders using REST API, returns JSON'''
		params = {'token':token, **kwargs}
		response = get(self._REST_API_URL.format(store_id = store_id,endpoint = endpoint), params = params)
		if response.status_code != 200:
			raise InvalidAPIKeys
		result = response.json()
		received = result['count']
		while received < result['total']:
			params['offset'] = received
			response = get(self._REST_API_URL.format(store_id = store_id,endpoint = endpoint), params = params)
			if response.status_code != 200:
				raise InvalidAPIKeys
			next = response.json()
			received += result['count']
			result['items'] += next['items']
		result['total'] = received
		result['count'] = received
		return result

	def GetStoreProducts(self, store_id, token, **kwargs):
		'''Gets store's products using REST API, returns JSON'''
		return self.GetStoreEndpoint(store_id, token, 'products', **kwargs)
	def GetStoreOrders(self, store_id, token, **kwargs):
		'''Gets store's orders using REST API, returns JSON'''
		return self.GetStoreEndpoint(store_id, token, 'orders', **kwargs)
	def GetStoreCategories(self, store_id, token, **kwargs):
		'''Gets store's categories using REST API, returns JSON'''
		return self.GetStoreEndpoint(store_id, token, 'categories', **kwargs)
		
	def SetStoreProduct(self, store_id, token, template):
		'''Adds or updates store's product using REST API, returns JSON'''
		params = {'token':token}
		product = {}
		for key in self._ALLOWED_PRODUCTS_FIELDS:
			if key in template:
				product[key] = template[key]
		store_product = self.GetStoreProducts(store_id, token, sku = product['sku'])
		if (store_product['count'] > 0):
			product_id = store_product['items'][0]['id']
			response = put(self._REST_API_URL.format(store_id = store_id,endpoint = 'products/{}'.format(product_id)), json = product, params=params)
			result = response.json()
			result['id'] = product_id
		else:
			response = post(self._REST_API_URL.format(store_id = store_id,endpoint = 'products'), json = product, params=params)
			result = response.json()
		if response.status_code != 200:
			raise InvalidAPIKeys
		return result
		
	def DeleteStoreProduct(self, store_id, token, product_id):
		'''Deletes store's product using REST API, returns JSON'''
		params = {'token':token}
		response = delete(self._REST_API_URL.format(store_id = store_id,endpoint = 'products/{}'.format(product_id)), params = params)
		if response.status_code != 200:
			raise InvalidAPIKeys
		return response.json()
		
	def SetStoreProductImage(self, store_id, token, product_id, img_url):
		'''Deletes store's product using REST API, returns JSON'''
		params = {'token':token, 'externalUrl':img_url}
		response = post(self._REST_API_URL.format(store_id = store_id,endpoint = 'products/{}/image'.format(product_id)), params = params)
		if response.status_code != 200:
			raise InvalidAPIKeys
		return response.json()
		
	def SetStoreOrder(self, store_id, token, order):
		'''Sets store's order using REST API, returns JSON
		   isku must be store_id-product_sku'''
		for key in self._DISALLOWED_ORDERS_FIELDS:
			order.pop(key, None)
		products = list()
		totalPrice = 0
		for product in order['items']:
			for key in self._DISALLOWED_ORDERS_ITEM_FIELDS:
				product.pop(key, None)
			sku = product['sku'].split('-')
			if sku[0] == str(store_id):
				product['sku'] = sku[1]
				products.append(product)
				totalPrice += product['price'] * product['quantity']
		if len(products) == 0:
			return {}
		order['items'] = products
		order['subtotal'] = totalPrice
		order['total'] = totalPrice
		params = {'token':token}
		response = post(self._REST_API_URL.format(store_id = store_id,endpoint = 'orders'), json = order, params=params)
		if response.status_code != 200:
			raise InvalidAPIKeys
		return response.json()
	
	def SetStoreCategory(self, store_id, token, category):
		'''Adds or updates store's category using REST API, returns JSON'''
		params = {'token':token}
		for key in self._DISALLOWED_CATEGORIES_FIELDS:
			category.pop(key, None)
		response = post(self._REST_API_URL.format(store_id = store_id,endpoint = 'categories'), json = category, params=params)
		if response.status_code != 200:
			raise InvalidAPIKeys
		return response.json()

	def GetStoreToken(self, store_id):
		'''Gets store token using REST API, returns JSON'''
		payload = {'client_id':self.client_id, 'client_secret':self.client_secret, 'grant_type':'authorization_code'}
		response = post(urljoin(self._OAUTH_URL, str(store_id)), data = payload)
		if response.status_code != 200:
			raise InvalidAPIKeys
		return response.json()

	def CreateStore(self, name, email, password, plan):
		'''Gets store token using Partners API, returns store_id'''
		payload = {'name':name, 'email':email, 'password':password, 'plan':plan, 'key':self.partners_key}
		response = post(urljoin(self._PARTNERS_API_URL, 'register?register=y'), data = payload)
		if response.status_code != 200:
			raise InvalidAPIKeys
		xml = ET.fromstring(response.text)
		return int(xml.text)
		
	def DeleteStore(self, store_id):
		'''Gets store token using Partners API, returns Boolean'''
		payload = {'ownerid':store_id, 'key':self.partners_key}
		response = post(urljoin(self._PARTNERS_API_URL, 'delete'), data = payload)
		if response.status_code != 200:
			raise InvalidAPIKeys
		return True