#pragma once
#include "esp_err.h"
/* Serialize HTTP requests, USB commands and idle locking. Initialize before tasks. */
esp_err_t vault_runtime_init(void);
void vault_runtime_enter(void);
void vault_runtime_leave(void);
void vault_runtime_touch(void);
void vault_runtime_poll(void);
