idf_component_register(SRCS "main.c" "status_led.c"
                INCLUDE_DIRS "."
                PRIV_REQUIRES driver led_strip esp_lcd sdmmc fatfs vfs tinyusb esp_lvgl_port nvs_flash esp_wifi esp_netif esp_event esp_http_server)
