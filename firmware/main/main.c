#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_system.h"

static const char *TAG = "vault";

/*
 * Development scaffold only.
 * No SD access, PIN entry, USB command handling, or cryptography is implemented.
 * Do not enable eFuse security features from this placeholder.
 */

void app_main(void)
{
    ESP_LOGI(TAG, "ESP32 vault development scaffold starting");
    ESP_LOGW(TAG, "NOT SECURE STORAGE: no encryption or authentication is implemented");
    ESP_LOGI(TAG, "Next: pin ESP-IDF release, verify board revision/pinout, then add hardware drivers.");

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
