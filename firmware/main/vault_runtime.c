#include "vault_runtime.h"
#include "vault_config.h"
#include "vault_storage.h"
#include "vault_drive.h"
#include "status_led.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "esp_timer.h"
static SemaphoreHandle_t s_mutex;
static int64_t s_activity;
esp_err_t vault_runtime_init(void) {
    s_mutex = xSemaphoreCreateMutex();
    s_activity = esp_timer_get_time();
    return s_mutex ? ESP_OK : ESP_ERR_NO_MEM;
}
void vault_runtime_enter(void) { xSemaphoreTake(s_mutex, portMAX_DELAY); }
void vault_runtime_leave(void) { xSemaphoreGive(s_mutex); }
void vault_runtime_touch(void) { s_activity = esp_timer_get_time(); }
void vault_runtime_poll(void) {
    vault_config_t cfg;
    vault_config_get(&cfg);
    if (vault_storage_is_unlocked() && !vault_drive_ready() && cfg.auto_lock_sec &&
        esp_timer_get_time() - s_activity >= (int64_t)cfg.auto_lock_sec * 1000000) {
        vault_storage_lock();
        vault_status_led_set_state(VAULT_LED_LOCKED);
    }
}
