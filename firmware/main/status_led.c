#include "status_led.h"

#include <stdbool.h>
#include <stdint.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "led_strip.h"
#include "portmacro.h"

/* Waveshare ESP32-S3-LCD-1.47 schematic: onboard WS2812B-0807 data is GPIO38.
 * This is not the 1.47B variant's LCD backlight pin map; confirm the board label.
 */
#define VAULT_RGB_GPIO          38
#define VAULT_RGB_LED_COUNT     1
#define VAULT_LED_TASK_STACK    3072
#define VAULT_LED_TASK_PRIORITY 3
#define VAULT_LED_TICK_MS       25
#define VAULT_LED_MAX_BRIGHTNESS 40U

static const char *TAG = "vault_status_led";
static led_strip_handle_t s_strip;
static portMUX_TYPE s_state_mux = portMUX_INITIALIZER_UNLOCKED;
static vault_led_state_t s_state = VAULT_LED_LOCKED;
static uint32_t s_generation;
static vault_led_mode_t s_mode;
static bool s_initialized;
static uint8_t s_last_red = 0xFF, s_last_green = 0xFF, s_last_blue = 0xFF;

static uint8_t breathe(uint32_t elapsed_ms, uint32_t period_ms,
                       uint8_t low, uint8_t high)
{
    uint32_t phase = elapsed_ms % period_ms;
    uint32_t half = period_ms / 2U;
    uint32_t distance = (phase <= half) ? phase : (period_ms - phase);
    return (uint8_t)(low + ((uint32_t)(high - low) * distance) / half);
}

static void set_rgb(uint8_t red, uint8_t green, uint8_t blue)
{
    if (s_strip == NULL) {
        return;
    }
    /* Avoid repeatedly refreshing an unchanged color (especially steady states). */
    if (red == s_last_red && green == s_last_green && blue == s_last_blue) {
        return;
    }
    /* Keep brightness deliberately low for a small onboard indicator LED. */
    if (red == 0 && green == 0 && blue == 0) {
        if (led_strip_clear(s_strip) == ESP_OK) {
            s_last_red = red; s_last_green = green; s_last_blue = blue;
        }
        return;
    }
    if (red > VAULT_LED_MAX_BRIGHTNESS) red = VAULT_LED_MAX_BRIGHTNESS;
    if (green > VAULT_LED_MAX_BRIGHTNESS) green = VAULT_LED_MAX_BRIGHTNESS;
    if (blue > VAULT_LED_MAX_BRIGHTNESS) blue = VAULT_LED_MAX_BRIGHTNESS;
    if (led_strip_set_pixel(s_strip, 0, red, green, blue) == ESP_OK &&
        led_strip_refresh(s_strip) == ESP_OK) {
        s_last_red = red; s_last_green = green; s_last_blue = blue;
    }
}

static void render_pattern(vault_led_state_t state, uint32_t elapsed_ms,
                           uint8_t *red, uint8_t *green, uint8_t *blue,
                           bool *auto_transition, vault_led_state_t *next_state)
{
    *red = *green = *blue = 0;
    *auto_transition = false;
    *next_state = state;

    switch (state) {
    case VAULT_LED_LOCKED: {
        uint8_t level = breathe(elapsed_ms, 1800, 3, 20);
        *blue = level;
        break;
    }
    case VAULT_LED_PIN_ENTRY:
        *red = 30;
        *green = 12;
        break;
    case VAULT_LED_AUTH_SUCCESS:
        *green = 35;
        if (elapsed_ms >= 700) {
            *auto_transition = true;
            *next_state = VAULT_LED_UNLOCKED;
        }
        break;
    case VAULT_LED_AUTH_FAILURE:
        /* Two short red flashes, then return to PIN entry. */
        if (elapsed_ms < 150 || (elapsed_ms >= 300 && elapsed_ms < 450)) {
            *red = 35;
        }
        if (elapsed_ms >= 800) {
            *auto_transition = true;
            *next_state = VAULT_LED_PIN_ENTRY;
        }
        break;
    case VAULT_LED_UNLOCKED:
        *green = breathe(elapsed_ms, 2200, 4, 20);
        break;
    case VAULT_LED_TRANSFER: {
        uint8_t level = breathe(elapsed_ms, 900, 8, 28);
        *red = (uint8_t)(level * 2U / 3U);
        *blue = level;
        break;
    }
    case VAULT_LED_TRANSFER_COMPLETE:
        *green = 35;
        if (elapsed_ms >= 650) {
            *auto_transition = true;
            *next_state = VAULT_LED_UNLOCKED;
        }
        break;
    case VAULT_LED_RECOVERY_ERROR: {
        /* Repeating triple white flash; remains until explicitly cleared. */
        uint32_t phase = elapsed_ms % 1600U;
        if (phase < 120U || (phase >= 240U && phase < 360U) ||
            (phase >= 480U && phase < 600U)) {
            *red = *green = *blue = 28;
        }
        break;
    }
    default:
        /* Unknown state fails closed visually. */
        *red = *green = *blue = 28;
        break;
    }
}

static void status_led_task(void *arg)
{
    (void)arg;
    vault_led_state_t active_state = VAULT_LED_LOCKED;
    uint32_t active_generation = UINT32_MAX;
    TickType_t state_started = xTaskGetTickCount();

    for (;;) {
        vault_led_state_t requested_state;
        uint32_t requested_generation;
        portENTER_CRITICAL(&s_state_mux);
        requested_state = s_state;
        requested_generation = s_generation;
        portEXIT_CRITICAL(&s_state_mux);

        if (requested_generation != active_generation) {
            active_generation = requested_generation;
            active_state = requested_state;
            state_started = xTaskGetTickCount();
        }

        uint32_t elapsed_ms = (uint32_t)((xTaskGetTickCount() - state_started) * portTICK_PERIOD_MS);
        uint8_t red, green, blue;
        bool auto_transition;
        vault_led_state_t next_state;
        render_pattern(active_state, elapsed_ms, &red, &green, &blue,
                       &auto_transition, &next_state);
        portENTER_CRITICAL(&s_state_mux);
        vault_led_mode_t mode = s_mode;
        portEXIT_CRITICAL(&s_state_mux);
        if (mode == VAULT_LED_MODE_STEALTH) red = green = blue = 0;
        else if (mode == VAULT_LED_MODE_DIM) { red /= 4; green /= 4; blue /= 4; }
        set_rgb(red, green, blue);

        if (auto_transition) {
            portENTER_CRITICAL(&s_state_mux);
            if (s_generation == active_generation && s_state == active_state) {
                s_state = next_state;
                ++s_generation;
            }
            portEXIT_CRITICAL(&s_state_mux);
        }
        vTaskDelay(pdMS_TO_TICKS(VAULT_LED_TICK_MS));
    }
}

esp_err_t vault_status_led_init(void)
{
    if (s_initialized) {
        return ESP_OK;
    }

    const led_strip_config_t strip_config = {
        .strip_gpio_num = VAULT_RGB_GPIO,
        .max_leds = VAULT_RGB_LED_COUNT,
        .led_model = LED_MODEL_WS2812,
        .color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_GRB,
        .flags = { .invert_out = false },
    };
    const led_strip_rmt_config_t rmt_config = {
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = 10 * 1000 * 1000,
        .mem_block_symbols = 64,
        .flags = { .with_dma = false },
    };

    esp_err_t err = led_strip_new_rmt_device(&strip_config, &rmt_config, &s_strip);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Could not initialize RGB LED: %s", esp_err_to_name(err));
        s_strip = NULL;
        return err;
    }

    s_initialized = true;
    err = xTaskCreate(status_led_task, "vault_led", VAULT_LED_TASK_STACK,
                      NULL, VAULT_LED_TASK_PRIORITY, NULL) == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
    if (err != ESP_OK) {
        s_initialized = false;
        (void)led_strip_clear(s_strip);
        ESP_LOGE(TAG, "Could not create status LED task");
        return err;
    }
    vault_status_led_set_state(VAULT_LED_LOCKED);
    ESP_LOGI(TAG, "Status LED initialized on GPIO%d", VAULT_RGB_GPIO);
    return ESP_OK;
}

void vault_status_led_set_state(vault_led_state_t state)
{
    if (state < VAULT_LED_LOCKED || state > VAULT_LED_RECOVERY_ERROR) {
        state = VAULT_LED_RECOVERY_ERROR;
    }
    portENTER_CRITICAL(&s_state_mux);
    /* Security/recovery faults are latched; ordinary progress cannot hide them. */
    if (s_state != VAULT_LED_RECOVERY_ERROR || state == VAULT_LED_RECOVERY_ERROR) {
        s_state = state;
        ++s_generation;
    }
    portEXIT_CRITICAL(&s_state_mux);
}

void vault_status_led_clear_recovery_fault(vault_led_state_t next_state)
{
    if (next_state < VAULT_LED_LOCKED || next_state >= VAULT_LED_RECOVERY_ERROR) {
        next_state = VAULT_LED_LOCKED;
    }
    portENTER_CRITICAL(&s_state_mux);
    if (s_state == VAULT_LED_RECOVERY_ERROR) {
        s_state = next_state;
        ++s_generation;
    }
    portEXIT_CRITICAL(&s_state_mux);
}

void vault_status_led_set_mode(vault_led_mode_t mode) {
    portENTER_CRITICAL(&s_state_mux);
    s_mode = mode;
    portEXIT_CRITICAL(&s_state_mux);
}
