#include <json.h>

#include "rest.h"
#include "model.h"
#include "http.h"

static const char *_DISALLOWED_ORDERS_ITEM_FIELDS[] = {"productId", "id", "categoryId"};
static const char *_DISALLOWED_ORDERS_FIELDS[] = {"vendorOrderNumber", "customerId", "total", "subtotal", "totalBeforeGiftCardRedemption", "usdTotal", "orderNumber"};
static const char *_DISALLOWED_PRODUCTS_FIELDS[] = {"id", "categories", "defaultCategoryId", "relatedProducts",
													"combinations", "url", "productClassId","defaultCombinationId", "categoryIds",
													"tax", "galleryImages", "media", "files", "sku"};

#define ARRAY_SIZE(arr)     (sizeof(arr) / sizeof((arr)[0]))


char *TrimWhiteSpaces (char *str)
{
	char *end = NULL;

	if (str == NULL)
		return NULL;
	while (isspace (*str)) str++;
	if (*str == 0)
		return NULL;
	end = str + strlen (str) - 1;
	while (end > str && isspace (*end)) end--;
	*(end + 1) = 0;
	return str;
}

void FilterOrderFields(struct json_object *order){
	if (order == NULL)
		return;

	for (size_t i = 0; i < ARRAY_SIZE(_DISALLOWED_ORDERS_FIELDS); i++){
		
		json_object *order_field = NULL;
		json_object_object_get_ex(order, _DISALLOWED_ORDERS_FIELDS[i], &order_field);
		if (order_field != NULL)
			json_object_object_del(order, _DISALLOWED_ORDERS_FIELDS[i]);
	}
	
	json_object *order_products = NULL;
	json_object_object_get_ex(order, "items", &order_products);
	
	if (order_products != NULL){
		for (size_t i = 0; i < json_object_array_length(order_products); i++){
			json_object *product = json_object_array_get_idx(order_products, i);
			for (size_t j = 0; j < ARRAY_SIZE(_DISALLOWED_ORDERS_ITEM_FIELDS); j++){
				
				json_object *product_field = NULL;
				json_object_object_get_ex(product, _DISALLOWED_ORDERS_ITEM_FIELDS[j], &product_field);
				if (product_field != NULL)
					json_object_object_del(product, _DISALLOWED_ORDERS_ITEM_FIELDS[j]);
			}
		}
	}
}

void FilterProductFields(struct json_object *product){
	if (product == NULL)
		return;
	for (size_t i = 0; i < ARRAY_SIZE(_DISALLOWED_PRODUCTS_FIELDS); i++){
		json_object *product_field = NULL;
		json_object_object_get_ex(product, _DISALLOWED_PRODUCTS_FIELDS[i], &product_field);
		if (product_field != NULL)
			json_object_object_del(product, _DISALLOWED_PRODUCTS_FIELDS[i]);
	}
}

bool ProcessStoreOrder(TStore store, struct json_object *order){
	
	struct json_object *new_products = NULL, *rest_products = NULL, *params = NULL;
	double total = 0;
	bool result = false;
	
	check(order != NULL, "Invalid function inputs.");
	new_products = json_object_new_array();
	check_mem(new_products);
	rest_products = json_object_new_array();
	check_mem(rest_products);
	
	json_object *order_products = NULL;
	json_object_object_get_ex(order, "items", &order_products);
	if (order_products != NULL){
		for (size_t i = 0; i < json_object_array_length(order_products); i++){
			json_object *product = json_object_array_get_idx(order_products, i);
			json_object *product_sku = NULL, *product_price = NULL, *product_quantity = NULL;
			
			json_object_object_get_ex(product,"sku", &product_sku);
			json_object_object_get_ex(product,"price", &product_price);
			json_object_object_get_ex(product,"quantity", &product_quantity);
			
			if (product_sku == NULL || product_price == NULL || product_quantity == NULL)
				continue;
			char *product_sku_val = (char *)json_object_get_string(product_sku);
			double product_quantity_val = (double)json_object_get_double(product_quantity);
			double product_price_val = (double)json_object_get_double(product_price);
			if (product_sku_val == NULL)
				continue;
			char *delim = strchr(product_sku_val, '-');
			if (delim == NULL)
				continue;
			if ((uint64_t)atoi(product_sku_val) != store.id){
				json_object_array_add(rest_products, json_object_get(product));
				continue;
			}
			json_object_object_add(product, "sku", json_object_new_string(++delim));
			json_object_array_add(new_products, json_object_get(product));
			total += product_quantity_val * product_price_val;
		}
		if (json_object_array_length(new_products) != 0){
			json_object_object_add(order, "subtotal", json_object_new_double(total));
			json_object_object_add(order, "total", json_object_new_double(total));
			json_object_object_add(order, "items", json_object_get(new_products));
			
			params = json_object_new_object();
			check_mem(params);
			json_object_object_add(params, "token", json_object_new_string(store.token));
			
			const char *buffer = json_object_to_json_string(order);
			struct json_object *json = RESTcall(store.id, POST_ORDER, params, (uint8_t *)buffer, strlen(buffer));
			if (json != NULL){
				json_object_put(json);
			}else{
				log_err("Failed to place order to store %lu", store.id);
			}
			json_object_object_add(order, "items", rest_products);
			rest_products = NULL;
			result = true;
		}
	}
error:
	if (params != NULL)
		json_object_put(params);
	if (new_products != NULL)
		json_object_put(new_products);
	if (rest_products != NULL)
		json_object_put(rest_products);
	return result;
}

int CreateHubCategory(TUser user, int parent_id, char *name){
	struct json_object *payload = NULL, *json = NULL, *tmp = NULL, *params = NULL;
	int result = -1;
	
	check(name != NULL && strlen(name) > 0, "Invalid function inputs.");
	payload = json_object_new_object();
	check_mem(payload);
	params = json_object_new_object();
	check_mem(params);

	json_object_object_add(params, "parent", json_object_new_int(parent_id));
	json_object_object_add(params, "token", json_object_new_string(user.token));
	
	json = RESTcall(user.hub_id, GET_CATEGORIES, params, NULL, 0);
	check_mem(json);
	json_object_object_get_ex(json, "items", &tmp);
	if (tmp != NULL && json_object_get_type(tmp) == json_type_array && json_object_array_length(tmp) > 0){
		for (size_t i = 0; i < json_object_array_length(tmp); i++){
			json_object *category_id = NULL, *category = json_object_array_get_idx(tmp, i);
			json_object_object_get_ex(category,"name", &category_id);
			if (strcmp(name, (char *)json_object_get_string(category_id)) == 0){
				json_object_object_get_ex(category,"id", &category_id);
				result = (int)json_object_get_int(category_id);
				break;
			}
		}
	}
	if (result == -1){
		json_object_object_add(payload, "parentId", json_object_new_int(parent_id));
		json_object_object_add(payload, "name", json_object_new_string(name));
		const char *buffer = json_object_to_json_string(payload);
		json = RESTcall(user.hub_id, POST_CATEGORY, params, (uint8_t *)buffer, strlen(buffer));
		check_mem(json);
		json_object *category_id = NULL;
		json_object_object_get_ex(json, "id", &category_id);
		result = (int)json_object_get_int(category_id);
	}
error:
	if (params != NULL)
		json_object_put(params);
	if (payload != NULL)
		json_object_put(payload);
	if (json != NULL)
		json_object_put(json);
	return result;
}

int CreateHubProductCategory(TUser user, TProduct product, int parent_id){
	char *name = product.category;
	int result = -1;
	
	check(name != NULL && strlen(name) > 0, "Invalid function inputs");
	
	char *delimiter = strchr(name, '/');
	while (delimiter != NULL){
		*delimiter = '\0';
		parent_id = CreateHubCategory(user, parent_id, name);
		*delimiter = '/';
		name = delimiter + 1;
		delimiter = strchr(name, '/');
	}
	parent_id = CreateHubCategory(user, parent_id, name);
	result = parent_id;
error:
	return result;
}


bool SetHubProductImage(int store_id, char *token, int product_id, char *img_url){
	uint8_t *response = NULL;
	bool result = false;
	struct json_object *json = NULL, *params = NULL;
	char *encoded_url = NULL;
	size_t response_len = 0;
	
	check(img_url != NULL, "Invalid function inputs");
	
	check(HTTPcall(HTTP_GET, img_url, NULL, 0, &response, &response_len) == 0, "Invalid HTTP response");
	
	params = json_object_new_object();
	check_mem(params);
	json_object_object_add(params, "token", json_object_new_string(token));
	json_object_object_add(params, "productId", json_object_new_int(product_id));
	
	json = RESTcall(store_id, POST_IMAGE, params, response, response_len);
	check(json != NULL, "Cannot create hub product.");
	
	result = true;
error:
	if (params != NULL)
		json_object_put(params);
	if (json != NULL)
		json_object_put(json);
	if (response != NULL)
		free(response);
	if (encoded_url != NULL)
		free(encoded_url);
	return result;
}

bool CreateHubProduct(TUser user, TStore store, TProduct product){
	
	bool result = false;
	struct json_object *json = NULL, *payload = NULL, *params = NULL;
	char *hub_sku = NULL;

	params = json_object_new_object();
	check_mem(params);
	json_object_object_add(params, "token", json_object_new_string(store.token));

	json = RESTcall(store.id, GET_PROFILE, params, NULL, 0);
	check(json != NULL, "Cannot retrieve store's profile.");
	json_object *tmp = NULL;
	json_object_object_get_ex(json,"company", &tmp);
	check(tmp != NULL, "Cannot retrieve store's proile");
	json_object_object_get_ex(tmp,"city", &tmp);
	check(tmp != NULL, "Cannot retrieve store's proile");
	int category_id = CreateHubCategory(user, 0, TrimWhiteSpaces((char *)json_object_get_string(tmp)));
	check(category_id > 0, "Cannot create categories.");
	category_id = CreateHubProductCategory(user, product, category_id);
	
	payload = json_object_new_object();
	check_mem(payload);
	
	hub_sku = calloc(strlen(product.sku) + ceil(log10(store.id > 0 ? store.id : 1)) + 2, 1);
	check_mem(hub_sku);			
	sprintf(hub_sku, "%ld-%s", store.id, product.sku);
	
	json_object_object_add(payload, "sku", json_object_new_string(hub_sku));
	json_object_object_add(payload, "name", json_object_new_string(product.name));
	json_object_object_add(payload, "price", json_object_new_double(product.price));
	json_object_object_add(payload, "description", json_object_new_string(product.description));
	tmp = json_object_new_array();
	
	json_object_array_add(tmp, json_object_new_int(category_id));
	json_object_object_add(payload, "categoryIds", tmp);
	json_object_object_add(payload, "defaultCategoryId", json_object_new_int(category_id));

	
	json_object_put(json);
	
	json_object_object_add(params, "token", json_object_new_string(user.token));
	const char *buffer = json_object_to_json_string(payload);
	json = RESTcall(user.hub_id, POST_PRODUCT, params, (uint8_t *)buffer, strlen(buffer));
	check(json != NULL, "Cannot create hub product.");
	
	json_object *product_id = NULL;
	json_object_object_get_ex(json, "id", &product_id);
	check(product_id != NULL && json_object_get_type(product_id) == json_type_int, "Invalid function inputs.");
	check(SetHubProductImage(user.hub_id, user.token, (int)json_object_get_int(product_id), product.imageUrl) == true, "Cannot set product picture.");
	result = true;
error:
	if (params != NULL)
		json_object_put(params);
	if (payload != NULL)
		json_object_put(payload);
	if (json != NULL)
		json_object_put(json);
	if (hub_sku != NULL)
		free(hub_sku);
	return result;
}

bool ProcessStoreProducts(TUser user, TStore store, TProduct product, struct json_object *hub_products, struct json_object *store_products){
	
	bool result = false;
	char *hub_sku = NULL;
	struct json_object *json = NULL, *params = NULL;
	
	check(hub_products != NULL && store_products != NULL, "Invalid function inputs.");

	hub_sku = calloc(strlen(product.sku) + ceil(log10(store.id > 0 ? store.id : 1)) + 2, 1);
	check_mem(hub_sku);			
	sprintf(hub_sku, "%ld-%s", store.id, product.sku);

	params = json_object_new_object();
	check_mem(params);
	json_object_object_add(params, "token", json_object_new_string(user.token));

	for (size_t i = 0; i < json_object_array_length(store_products); i++) {
		json_object *store_product_sku = NULL, *store_product = json_object_array_get_idx(store_products, i);
		json_object_object_get_ex(store_product,"sku", &store_product_sku);
		if (store_product_sku == NULL)
			continue;
		if (strcmp((char *)json_object_get_string(store_product_sku), product.sku) == 0){
			
			for (size_t j = 0; j < json_object_array_length(hub_products); j++) {
				json_object *hub_product_sku = NULL, *hub_product = json_object_array_get_idx(hub_products, j);
				json_object *hub_product_id = NULL;
				json_object_object_get_ex(hub_product,"sku", &hub_product_sku);
				json_object_object_get_ex(hub_product,"id", &hub_product_id);
				if (hub_product_sku == NULL || hub_product_id == NULL)
					continue;
				if (strcmp((char *)json_object_get_string(hub_product_sku), hub_sku) == 0){
					FilterProductFields(store_product);
					json_object_object_add(params, "productId", json_object_get(hub_product_id));
					const char *buffer = json_object_to_json_string(store_product);
					json = RESTcall(user.hub_id, PUT_PRODUCT, params, (uint8_t *)buffer, strlen(buffer));
					check(json != NULL, "Setting product %d failed", (int)json_object_get_int(hub_product_id));
					//SetHubProductImage(user.hub_id, user.token, (int)json_object_get_int(hub_product_id), product.imageUrl);
					result = true;
					goto error;
				}
			}
			/*The product has not been found in the hub. Create the product and corresponging categories in the hub and return.*/
			check(CreateHubProduct(user, store, product) == true, "Cannot create hub product.");
			result = true;
			goto error;
			
		}
	}
	/*The product has not been found in the agent's store. Check if it exists in the hub and remove the product from it.*/
	for (size_t j = 0; j < json_object_array_length(hub_products); j++) {
		json_object *hub_product_sku = NULL, *hub_product = json_object_array_get_idx(hub_products, j);
		json_object *hub_product_id = NULL;
		json_object_object_get_ex(hub_product,"sku", &hub_product_sku);
		json_object_object_get_ex(hub_product,"id", &hub_product_id);
		if (hub_product_sku == NULL || hub_product_id == NULL)
			continue;
		if (strcmp((char *)json_object_get_string(hub_product_sku), hub_sku) == 0){
			json_object_object_add(params, "productId", json_object_get(hub_product_id));
			json = RESTcall(user.hub_id, DELETE_PRODUCT, params, NULL, 0);
			check(json != NULL, "Removing product %d failed", (int)json_object_get_int(hub_product_id));
		}
	}
	result = true;
error:
	if (params != NULL)
		json_object_put(params);	
	if (json != NULL)
		json_object_put(json);
	if (hub_sku != NULL)
		free(hub_sku);
	return result;
}

bool ProcessHubProducts(uint64_t user_id){
	
	bool result = false;
	sqlite3 *pDB = NULL;
	TUser *user = NULL;
	TStore *stores = NULL;
	TProduct *products = NULL;
	size_t stores_count = 0, products_count = 0;
	struct json_object *hub_json = NULL, *store_json = NULL, *hub_products = NULL, *store_products = NULL, *params = NULL;
	
	check(sqlite3_open_v2("app.db", &pDB, SQLITE_OPEN_READWRITE | SQLITE_OPEN_WAL, NULL) == SQLITE_OK, "Error while opening DB.");
	user = GetUser(pDB, user_id);
	check(user != NULL, "There is no such user.");
	stores = GetUserStores(pDB, user->id, &stores_count);
	check(stores != NULL && stores_count > 0, "User don't have stores.");
	products = GetUserProducts(pDB, user->id, &products_count);
	check(products != NULL && products_count > 0, "User don't have products.");
	
	params = json_object_new_object();
	check_mem(params);
	json_object_object_add(params, "token", json_object_new_string(user->token));
	
	hub_json = RESTcall(user->hub_id, GET_PRODUCTS, params, NULL, 0);
	check(hub_json != NULL, "JSON is invalid.");
	json_object_object_get_ex(hub_json, "items", &hub_products);
	check(hub_products != NULL && json_object_get_type(hub_products) == json_type_array, "JSON is invalid.");
	for (size_t i = 0; i < stores_count; i++){
		json_object_object_add(params, "token", json_object_new_string(stores[i].token));
		store_json = RESTcall(stores[i].id, GET_PRODUCTS, params, NULL, 0);
		if (store_json == NULL)
			continue;
		json_object_object_get_ex(store_json, "items", &store_products);
		if (store_products == NULL || json_object_get_type(store_products) != json_type_array || json_object_array_length(store_products) == 0)
			continue;
		for (size_t j = 0; j < products_count; j++){
			ProcessStoreProducts(*user, stores[i], products[j], hub_products, store_products);
		}
		json_object_put(store_json);
		store_json = NULL;
	}
	result = true;
error:
	if (params != NULL)
		json_object_put(params);
	if (store_json != NULL)
		json_object_put(store_json);
	if (hub_json != NULL)
		json_object_put(hub_json);
	if (stores != NULL)
		FreeStores(stores, stores_count);
	if (products != NULL)
		FreeProducts(products, products_count);
	if (user != NULL)
		FreeUser(user);
	if (pDB != NULL)
		sqlite3_close_v2(pDB);
	return result;
}

bool ProcessHubOrders(uint64_t user_id){
	
	bool result = false;
	struct json_object *params = NULL, *hub_orders = NULL;
	sqlite3 *pDB = NULL;
	TUser *user = NULL;
	TStore *stores = NULL;
	size_t stores_count = 0;
	struct json_object *json = NULL;
	
	check(sqlite3_open_v2("app.db", &pDB, SQLITE_OPEN_READWRITE | SQLITE_OPEN_WAL, NULL) == SQLITE_OK, "Error while opening DB.");
	user = GetUser(pDB, user_id);
	check(user != NULL, "There is no such user.");
	stores = GetUserStores(pDB, user->id, &stores_count);
	check(stores != NULL && stores_count > 0, "User don't have stores.");
	
	params = json_object_new_object();
	check_mem(params);
	json_object_object_add(params, "createdFrom", json_object_new_int(user->orders_date));
	json_object_object_add(params, "token", json_object_new_string(user->token));
	
	json = RESTcall(user->hub_id, GET_ORDERS, params, NULL, 0);
	check(json != NULL, "JSON is invalid.");
	json_object_object_get_ex(json, "items", &hub_orders);
	check(hub_orders != NULL && json_object_get_type(hub_orders) == json_type_array, "JSON is invalid.");

	if (json_object_array_length(hub_orders) > 0){
		check(UpdateUserOrdersDate(pDB, user_id) == 0, "Cannot set user's orders date.");
		for (size_t i = 0; i < json_object_array_length(hub_orders); i++) {
			json_object *order = json_object_array_get_idx(hub_orders, i);
			FilterOrderFields(order);
			for (size_t j = 0; j < stores_count; j++){
				if (ProcessStoreOrder(stores[j], order)){
					if (UpdateStoreOrdersCount(pDB, stores[j].id) != 0){
						log_err("Cannot set store's orders count.");
					}
				}
			}
		}
	}
	result = true;
error:
	if (params != NULL)
		json_object_put(params);
	if (json != NULL)
		json_object_put(json);
	if (stores != NULL)
		FreeStores(stores, stores_count);
	if (user != NULL)
		FreeUser(user);
	if (pDB != NULL)
		sqlite3_close_v2(pDB);
	return result;
}