#include "model.h"

void FreeUser(TUser *user){
	if (user == NULL)
		return;
	if (user->token != NULL)
		free(user->token);
	if (user->client_id != NULL)
		free(user->client_id);
	if (user->client_secret != NULL)
		free(user->client_secret);
	if (user->partners_key != NULL)
		free(user->partners_key);
	if (user->email != NULL)
		free(user->email);
	if (user->password != NULL)
		free(user->password);
	free(user);
}

void FreeStores(TStore *stores, size_t stores_count){
	if (stores == NULL)
		return;
	for(size_t i = 0; i < stores_count; i++){
		if (stores[i].token != NULL)
			free(stores[i].token);
	}
	free(stores);
}

void FreeProducts(TProduct *products, size_t products_count){
	if (products == NULL)
		return;
	for(size_t i = 0; i < products_count; i++){
		if (products[i].sku != NULL)
			free(products[i].sku);		
		if (products[i].category != NULL)
			free(products[i].category);		
		if (products[i].description != NULL)
			free(products[i].description);		
		if (products[i].imageUrl != NULL)
			free(products[i].imageUrl);		
		if (products[i].name != NULL)
			free(products[i].name);
	}
	free(products);
}

TUser *GetUser(sqlite3 *pDB, uint64_t user_id){
	
	int result = -1;
	sqlite3_stmt *stmt = NULL;
	TUser *user = NULL;
	check(pDB != NULL, "Invalid function inputs.");
	result = sqlite3_prepare_v2(pDB, "select id,email,password,partners_key,client_id,client_secret,hub_id,token,strftime('%s', orders_date) from user where id = ? limit 1", -1, &stmt, NULL);
	check(result == SQLITE_OK, "Error while preparing SQLite statement.");
	result = sqlite3_bind_int64(stmt, 1, user_id);
	check(result == SQLITE_OK, "Error while binding SQLite statement.");	
	result = sqlite3_step(stmt);
	check(result == SQLITE_ROW, "No data available.");
	user = calloc(sizeof(TUser), 1);
	user->id = sqlite3_column_int64(stmt, 0);
	user->email = strdup((const char *)sqlite3_column_text(stmt, 1));
	user->password = strdup((const char *)sqlite3_column_text(stmt, 2));
	user->partners_key = strdup((const char *)sqlite3_column_text(stmt, 3));
	user->client_id = strdup((const char *)sqlite3_column_text(stmt, 4));
	user->client_secret = strdup((const char *)sqlite3_column_text(stmt, 5));
	user->hub_id = sqlite3_column_int64(stmt, 6);
	user->token = strdup((const char *)sqlite3_column_text(stmt, 7));
	user->orders_date = sqlite3_column_int64(stmt, 8);
	check_mem(user);
	result = 0;
error:
	sqlite3_finalize(stmt);
	if (result != 0){
		if (user != NULL){
			FreeUser(user);
			user = NULL;
		}
	}
	return user;
}

int UpdateUserOrdersDate(sqlite3 *pDB, uint64_t user_id){
	
	int result = -1;
	sqlite3_stmt *stmt = NULL;
	check(pDB != NULL, "Invalid function inputs.");
	
	result = sqlite3_prepare_v2(pDB, "update `user` set `orders_date` = datetime(\"now\") where id = ?", -1, &stmt, NULL);
	check(result == SQLITE_OK, "Error while preparing SQLite statement.");
	result = sqlite3_bind_int64(stmt, 1, user_id);
	check(result == SQLITE_OK, "Error while binding SQLite statement.");	
	result = sqlite3_step(stmt);
	check(result == SQLITE_DONE, "Error while executing SQLite statement.");
	result = 0;
error:
	sqlite3_finalize(stmt);
	return result;
}

int UpdateStoreOrdersCount(sqlite3 *pDB, uint64_t store_id){
	
	int result = -1;
	sqlite3_stmt *stmt = NULL;
	check(pDB != NULL, "Invalid function inputs.");
	
	result = sqlite3_prepare_v2(pDB, "update `store` set `orders_count` = `orders_count`+1 where id = ?", -1, &stmt, NULL);
	check(result == SQLITE_OK, "Error while preparing SQLite statement.");
	result = sqlite3_bind_int64(stmt, 1, store_id);
	check(result == SQLITE_OK, "Error while binding SQLite statement.");	
	result = sqlite3_step(stmt);
	check(result == SQLITE_DONE, "Error while executing SQLite statement.");
	result = 0;
error:
	sqlite3_finalize(stmt);
	return result;
}

TStore *GetUserStores(sqlite3 *pDB, uint64_t user_id, size_t *stores_count){
	
	int result = -1;
	sqlite3_stmt *stmt = NULL;
	TStore *stores = NULL;
	check(pDB != NULL && stores_count != NULL, "Invalid function inputs.");
	result = sqlite3_prepare_v2(pDB, "select * from store where user_id = ?", -1, &stmt, NULL);
	check(result == SQLITE_OK, "Error while preparing SQLite statement.");
	result = sqlite3_bind_int64(stmt, 1, user_id);
	check(result == SQLITE_OK, "Error while binding SQLite statement.");
	while (sqlite3_step(stmt) == SQLITE_ROW){
		if (stores == NULL){
			stores = calloc(sizeof(TStore), 1);
			check_mem(stores);
			*stores_count = 1;
		}else{
			stores = realloc(stores, (*stores_count + 1) * sizeof(TStore));
			check_mem(stores);
			*stores_count += 1;
		}
		stores[*stores_count - 1].id = sqlite3_column_int64(stmt, 0);
		stores[*stores_count - 1].token = strdup((const char *)sqlite3_column_text(stmt, 1));
		stores[*stores_count - 1].user_id = sqlite3_column_int64(stmt, 2);
		stores[*stores_count - 1].orders_count = sqlite3_column_int64(stmt, 3);
	}
	result = 0;
error:
	sqlite3_finalize(stmt);
	if (result != 0){
		if (stores != NULL){
			FreeStores(stores, *stores_count);
			stores = NULL;
		}
	}
	return stores;
}

TProduct *GetUserProducts(sqlite3 *pDB, uint64_t user_id, size_t *products_count){
	
	int result = -1;
	sqlite3_stmt *stmt = NULL;
	TProduct *products = NULL;
	
	check(pDB != NULL && products_count != NULL, "Invalid function inputs.");
	result = sqlite3_prepare_v2(pDB, "select * from product where user_id = ?", -1, &stmt, NULL);
	check(result == SQLITE_OK, "Error while preparing SQLite statement.");
	result = sqlite3_bind_int64(stmt, 1, user_id);
	check(result == SQLITE_OK, "Error while binding SQLite statement.");
	while (sqlite3_step(stmt) == SQLITE_ROW){
		if (products == NULL){
			products = calloc(sizeof(TProduct), 1);
			check_mem(products);
			*products_count = 1;
		}else{
			products = realloc(products, (*products_count + 1) * sizeof(TProduct));
			check_mem(products);
			*products_count += 1;
		}
		products[*products_count - 1].id = sqlite3_column_int64(stmt, 0);
		products[*products_count - 1].sku = strdup((const char *)sqlite3_column_text(stmt, 1));
		products[*products_count - 1].user_id = sqlite3_column_int64(stmt, 2);
		products[*products_count - 1].category = strdup((const char *)sqlite3_column_text(stmt, 3));
		products[*products_count - 1].description = strdup((const char *)sqlite3_column_text(stmt, 4));
		products[*products_count - 1].imageUrl = strdup((const char *)sqlite3_column_text(stmt, 5));
		products[*products_count - 1].price = sqlite3_column_double(stmt, 6);
		products[*products_count - 1].name = strdup((const char *)sqlite3_column_text(stmt, 7));
	}
	result = 0;
error:
	sqlite3_finalize(stmt);
	if (result != 0){
		if (products != NULL){
			FreeProducts(products, *products_count);
			products = NULL;
		}
	}
	return products;
}