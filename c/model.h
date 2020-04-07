#include <sqlite3.h>

typedef struct {
	uint64_t id;
	uint64_t hub_id;
	char *token;
	char *client_id;
	char *client_secret;
	char *partners_key;
	char *email;
	char *password;
	time_t orders_date;
} TUser;

typedef struct {
	uint64_t id;
	char *token;
	uint64_t user_id;
	uint64_t orders_count;
} TStore;

typedef struct {
	uint64_t id;
	char *sku;
	uint64_t user_id;
	char *category;
	char *description;
	char *imageUrl;
	double price;
	char *name;
} TProduct;

extern void FreeUser(TUser *user);
extern void FreeStores(TStore *stores, size_t stores_count);
extern void FreeProducts(TProduct *products, size_t products_count);
extern TUser *GetUser(sqlite3 *pDB, uint64_t id);
extern TStore *GetUserStores(sqlite3 *pDB, uint64_t user_id, size_t *stores_count);
extern TProduct *GetUserProducts(sqlite3 *pDB, uint64_t user_id, size_t *products_count);
extern int UpdateUserOrdersDate(sqlite3 *pDB, uint64_t user_id);
extern int UpdateStoreOrdersCount(sqlite3 *pDB, uint64_t store_id);
