#include <curl/curl.h>
#include <sqlite3.h>
#include <sys/file.h>

#include "model.h"
#include "ecwid.h"

#define USAGE_STRING "ecwid-api (products|prices) user_id"

int main(int argc, char* argv[]){
	int result = -1;
	uint64_t user_id = 0;
	sqlite3_initialize();
	curl_global_init(CURL_GLOBAL_ALL);
	int pid_file = -1;
	

	check(argc == 3, USAGE_STRING);
	user_id = atoi(argv[2]);
	check(user_id != 0, USAGE_STRING);
	if (strcmp(argv[1], "products") == 0){
		
		pid_file = open("ecwid-api-products.pid", O_RDWR | O_CREAT, 0666);
		check(pid_file > 0, "You are not allowed to run multiple instance of the program.");
		int rc = flock(pid_file, LOCK_EX | LOCK_NB);
		check(rc != -1, "You are not allowed to run multiple instance of the program.");
		check(ProcessHubProducts(user_id) == true, "Cannot process hub prices.");
	}else if (strcmp(argv[1], "orders") == 0){
		
		pid_file = open("ecwid-api-orders.pid", O_RDWR | O_CREAT, 0666);
		check(pid_file > 0, "You are not allowed to run multiple instance of the program.");
		int rc = flock(pid_file, LOCK_EX | LOCK_NB);
		check(rc != -1, "You are not allowed to run multiple instance of the program.");		
		check(ProcessHubOrders(user_id) == true, "Cannot process hub orders.");
	}else{
		log_err(USAGE_STRING);
		goto error;
	}
	result = 0;
error:
	if (pid_file != -1)
		close(pid_file);
	sqlite3_shutdown();
	curl_global_cleanup();
	return result;
}
