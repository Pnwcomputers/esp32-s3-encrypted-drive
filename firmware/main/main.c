Here is the complete, consolidated `main.c` containing all hardware fixes, clean ST7789 display parameters, LVGL 9 full-refresh settings, 180° orientation adjustment, stealth Wi-Fi pairing server, and the air-gapped TinyUSB CDC transition:

```c
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_wifi.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_http_server.h"
#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "driver/sdmmc_host.h"
#include "sdmmc_cmd.h"
#include "esp_vfs_fat.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_vendor.h"
#include "esp_lcd_panel_ops.h"
#include "tinyusb.h"
#include "tinyusb_default_config.h"
#include "tinyusb_cdc_acm.h"
#include "esp_lvgl_port.h"
#include "lvgl.h"

static const char *TAG = "vault_main";

#define WIFI_SSID      "MyEarPods"
#define WIFI_PASS      "53cur3ty"
#define VAULT_PIN      "pin=123456"

// --- WAVESHARE 1.47" HARDWARE PINS ---
#define LCD_MOSI  45
#define LCD_SCLK  40
#define LCD_CS    42
#define LCD_DC    41
#define LCD_RST   39
#define LCD_BL    48

#define SD_CLK    14
#define SD_CMD    15
#define SD_D0     16
#define SD_D1     18
#define SD_D2     17
#define SD_D3     21

static esp_lcd_panel_io_handle_t io_handle = NULL;
static esp_lcd_panel_handle_t panel_handle = NULL;
static lv_obj_t *ui_status_label = NULL;
static lv_obj_t *ui_prompt_label = NULL;
volatile bool vault_unlocked = false;
static httpd_handle_t server = NULL;

const char* html_page = "<!DOCTYPE html><html><head><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
"<style>body{font-family:sans-serif;text-align:center;background:#f4f4f9;color:#333;margin-top:50px;}"
"input[type=password]{font-size:2em;width:80%;margin:20px;text-align:center;padding:10px;border-radius:8px;border:1px solid #ccc;}"
"input[type=submit]{font-size:1.5em;padding:15px 40px;background:#007aff;color:#fff;border:none;border-radius:8px;font-weight:bold;cursor:pointer;}</style></head>"
"<body><h2>EarPods Configuration</h2><p>Enter device PIN to connect</p><form action=\"/unlock\" method=\"POST\">"
"<input type=\"password\" name=\"pin\" inputmode=\"numeric\" placeholder=\"PIN\" autofocus required><br>"
"<input type=\"submit\" value=\"Connect\"></form></body></html>";

static esp_err_t root_get_handler(httpd_req_t *req) {
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, html_page, HTTPD_RESP_USE_STRLEN);
}

static esp_err_t unlock_post_handler(httpd_req_t *req) {
    char buf[100];
    int ret, remaining = req->content_len;

    if (remaining >= sizeof(buf)) {
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }
    ret = httpd_req_recv(req, buf, remaining);
    if (ret <= 0) return ESP_FAIL;
    buf[ret] = '\0';

    if (strcmp(buf, VAULT_PIN) == 0) {
        vault_unlocked = true;
        const char* success_resp = "<!DOCTYPE html><html><body style=\"background:#f4f4f9;color:#333;text-align:center;font-family:sans-serif;margin-top:50px;\"><h2>Connected.</h2><p>You may close this page.</p></body></html>";
        httpd_resp_send(req, success_resp, HTTPD_RESP_USE_STRLEN);
    } else {
        const char* fail_resp = "<!DOCTYPE html><html><body style=\"background:#f4f4f9;color:#d9534f;text-align:center;font-family:sans-serif;margin-top:50px;\"><h2>Pairing Failed.</h2><a href=\"/\" style=\"color:#007aff;\">Try Again</a></body></html>";
        httpd_resp_send(req, fail_resp, HTTPD_RESP_USE_STRLEN);
    }
    return ESP_OK;
}

void start_webserver(void) {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    if (httpd_start(&server, &config) == ESP_OK) {
        httpd_uri_t root = { .uri = "/", .method = HTTP_GET, .handler = root_get_handler, .user_ctx = NULL };
        httpd_uri_t unlock = { .uri = "/unlock", .method = HTTP_POST, .handler = unlock_post_handler, .user_ctx = NULL };
        httpd_register_uri_handler(server, &root);
        httpd_register_uri_handler(server, &unlock);
        ESP_LOGI(TAG, "Web server started.");
    }
}

void wifi_init_softap(void) {
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    wifi_config_t wifi_config = {
        .ap = {
            .ssid = WIFI_SSID,
            .ssid_len = strlen(WIFI_SSID),
            .channel = 1,
            .password = WIFI_PASS,
            .max_connection = 1,
            .authmode = WIFI_AUTH_WPA2_PSK
        },
    };

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_LOGI(TAG, "Wi-Fi SoftAP active. SSID:%s", WIFI_SSID);
}

void init_lcd(void) {
    ESP_LOGI(TAG, "Initializing LCD hardware...");
    gpio_config_t bk_gpio_config = {
        .mode = GPIO_MODE_OUTPUT,
        .pin_bit_mask = (1ULL << LCD_BL)
    };
    gpio_config(&bk_gpio_config);

    spi_bus_config_t buscfg = {
        .sclk_io_num = LCD_SCLK,
        .mosi_io_num = LCD_MOSI,
        .miso_io_num = -1,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 172 * 320 * 2 + 8
    };
    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &buscfg, SPI_DMA_CH_AUTO));

    esp_lcd_panel_io_spi_config_t io_config = {
        .dc_gpio_num = LCD_DC,
        .cs_gpio_num = LCD_CS,
        .pclk_hz = 20 * 1000 * 1000,
        .lcd_cmd_bits = 8,
        .lcd_param_bits = 8,
        .spi_mode = 0,
        .trans_queue_depth = 10,
    };
    ESP_ERROR_CHECK(esp_lcd_new_panel_io_spi((esp_lcd_spi_bus_handle_t)SPI2_HOST, &io_config, &io_handle));

    esp_lcd_panel_dev_config_t panel_config = {
        .reset_gpio_num = LCD_RST,
        .rgb_ele_order = LCD_RGB_ELEMENT_ORDER_RGB,
        .bits_per_pixel = 16,
    };
    ESP_ERROR_CHECK(esp_lcd_new_panel_st7789(io_handle, &panel_config, &panel_handle));

    ESP_ERROR_CHECK(esp_lcd_panel_reset(panel_handle));
    ESP_ERROR_CHECK(esp_lcd_panel_init(panel_handle));

    ESP_ERROR_CHECK(esp_lcd_panel_set_gap(panel_handle, 34, 0));
    ESP_ERROR_CHECK(esp_lcd_panel_invert_color(panel_handle, true));
    ESP_ERROR_CHECK(esp_lcd_panel_disp_on_off(panel_handle, true));

    gpio_set_level(LCD_BL, 1);
}

void init_sd_card(void) {
    ESP_LOGI(TAG, "Initializing SD Card...");
    esp_vfs_fat_sdmmc_mount_config_t mount_config = {
        .format_if_mount_failed = false, .max_files = 5, .allocation_unit_size = 16 * 1024
    };
    sdmmc_card_t *card;
    sdmmc_host_t host = SDMMC_HOST_DEFAULT();
    
    sdmmc_slot_config_t slot_config = SDMMC_SLOT_CONFIG_DEFAULT();
    slot_config.width = 4; slot_config.clk = SD_CLK; slot_config.cmd = SD_CMD;
    slot_config.d0 = SD_D0; slot_config.d1 = SD_D1; slot_config.d2 = SD_D2; slot_config.d3 = SD_D3;

    esp_err_t ret = esp_vfs_fat_sdmmc_mount("/sdcard", &host, &slot_config, &mount_config, &card);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SD mount failed.");
    } else {
        ESP_LOGI(TAG, "SD Card mounted successfully.");
    }
}

void init_ui(void) {
    ESP_LOGI(TAG, "Initializing LVGL engine...");
    const lvgl_port_cfg_t lvgl_cfg = ESP_LVGL_PORT_INIT_CONFIG();
    ESP_ERROR_CHECK(lvgl_port_init(&lvgl_cfg));

    const lvgl_port_display_cfg_t disp_cfg = {
        .io_handle = io_handle,
        .panel_handle = panel_handle,
        .buffer_size = 172 * 320,
        .double_buffer = false,
        .hres = 172,
        .vres = 320,
        .monochrome = false,
        .color_format = LV_COLOR_FORMAT_RGB565,
        .flags = { 
            .buff_dma = true,
            .full_refresh = true
        }
    };
    
    lvgl_port_lock(0);

    lv_display_t *disp = lvgl_port_add_disp(&disp_cfg);

    // 180° rotation setting
    lv_display_set_rotation(disp, LV_DISPLAY_ROTATION_180);

    lv_obj_t *scr = lv_scr_act();
    lv_obj_set_style_bg_color(scr, lv_color_hex(0x000000), LV_PART_MAIN);

    ui_status_label = lv_label_create(scr);
    lv_label_set_text(ui_status_label, "PAIRING MODE");
    lv_obj_set_style_text_color(ui_status_label, lv_color_hex(0xFF8800), LV_PART_MAIN);
    lv_obj_align(ui_status_label, LV_ALIGN_TOP_MID, 0, 20);

    ui_prompt_label = lv_label_create(scr);
    lv_label_set_text(ui_prompt_label, "Wi-Fi AP Active:\nMyEarPods\n\nIP Address:\n192.168.4.1");
    lv_obj_set_style_text_align(ui_prompt_label, LV_TEXT_ALIGN_CENTER, LV_PART_MAIN);
    lv_obj_set_style_text_color(ui_prompt_label, lv_color_hex(0xFFFFFF), LV_PART_MAIN);
    lv_obj_align(ui_prompt_label, LV_ALIGN_CENTER, 0, 10);
    
    lvgl_port_unlock();
}

void update_ui_unlocked(void) {
    lvgl_port_lock(0);
    lv_label_set_text(ui_status_label, "CONNECTED");
    lv_obj_set_style_text_color(ui_status_label, lv_color_hex(0x00FF00), LV_PART_MAIN);
    
    lv_label_set_text(ui_prompt_label, "USB Data Interface Active");
    lvgl_port_unlock();
}

void init_usb_cdc(void) {
    ESP_LOGI(TAG, "Initializing USB CDC...");
    const tinyusb_config_t tusb_cfg = TINYUSB_DEFAULT_CONFIG();
    ESP_ERROR_CHECK(tinyusb_driver_install(&tusb_cfg));

    tinyusb_config_cdcacm_t acm_cfg = { 0 }; 
    if (!tinyusb_cdcacm_initialized(TINYUSB_CDC_ACM_0)) {
        ESP_ERROR_CHECK(tinyusb_cdcacm_init(&acm_cfg));
    }
}

void app_main(void) {
    ESP_LOGI(TAG, "Booting ESP32 Vault...");
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
      ESP_ERROR_CHECK(nvs_flash_erase());
      ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    init_lcd();
    init_ui();
    init_sd_card();
    
    wifi_init_softap();
    start_webserver();

    while (!vault_unlocked) {
        vTaskDelay(pdMS_TO_TICKS(500));
    }

    if (server) {
        httpd_stop(server);
    }
    esp_wifi_stop();
    esp_wifi_deinit();

    update_ui_unlocked();
    init_usb_cdc();

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

```
