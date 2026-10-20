#pragma once
#include <stddef.h>
#include <sys/types.h>
#include "esp_err.h"
#define HTTP_GET 0
#define HTTP_POST 1
#define HTTPD_RESP_USE_STRLEN -1
typedef void *httpd_handle_t;
typedef struct httpd_req { const char *uri; int method; size_t content_len; void *user_ctx;
 const char *body, *token, *marker, *host, *origin; size_t offset; char response[32768], status[64]; } httpd_req_t;
typedef struct { const char *uri; int method; esp_err_t (*handler)(httpd_req_t *); void *user_ctx; } httpd_uri_t;
typedef struct { int max_uri_handlers, stack_size; } httpd_config_t;
#define HTTPD_DEFAULT_CONFIG() ((httpd_config_t){0})
int httpd_req_recv(httpd_req_t *, char *, size_t);
esp_err_t httpd_resp_set_type(httpd_req_t *, const char *);
esp_err_t httpd_resp_set_status(httpd_req_t *, const char *);
esp_err_t httpd_resp_set_hdr(httpd_req_t *, const char *, const char *);
esp_err_t httpd_resp_send(httpd_req_t *, const char *, ssize_t);
esp_err_t httpd_resp_send_chunk(httpd_req_t *, const char *, ssize_t);
esp_err_t httpd_req_get_hdr_value_str(httpd_req_t *, const char *, char *, size_t);
size_t httpd_req_get_hdr_value_len(httpd_req_t *, const char *);
esp_err_t httpd_req_get_url_query_str(httpd_req_t *, char *, size_t);
esp_err_t httpd_query_key_value(const char *, const char *, char *, size_t);
esp_err_t httpd_start(httpd_handle_t *, const httpd_config_t *);
esp_err_t httpd_stop(httpd_handle_t);
esp_err_t httpd_register_uri_handler(httpd_handle_t, const httpd_uri_t *);
esp_err_t httpd_resp_send_500(httpd_req_t *);
esp_err_t httpd_resp_send_404(httpd_req_t *);
