idf_component_register(
    SRCS "main.c" "status_led.c" "vault_config.c" "vault_runtime.c"
         "vault_crypto.c" "vault_storage.c" "vault_web.c" "cdc_protocol.c"
    INCLUDE_DIRS "."
    EMBED_TXTFILES "vault_index.html"
    PRIV_REQUIRES driver led_strip esp_lcd sdmmc fatfs vfs esp_tinyusb
                  esp_lvgl_port nvs_flash esp_wifi esp_netif esp_event
                  esp_http_server esp_timer mbedtls json)
