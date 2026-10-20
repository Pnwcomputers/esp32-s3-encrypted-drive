#pragma once

#include "esp_err.h"
#include "vault_config.h"

typedef enum {
    VAULT_LED_LOCKED = 0,
    VAULT_LED_PIN_ENTRY,
    VAULT_LED_AUTH_SUCCESS,
    VAULT_LED_AUTH_FAILURE,
    VAULT_LED_UNLOCKED,
    VAULT_LED_TRANSFER,
    VAULT_LED_TRANSFER_COMPLETE,
    VAULT_LED_RECOVERY_ERROR,
} vault_led_state_t;

/* Initializes the onboard WS2812 RGB LED and starts its non-blocking pattern task.
 * A failure is reported to the log but does not prevent the vault UI from starting.
 */
esp_err_t vault_status_led_init(void);

/* Safe to call from ordinary tasks and HTTP handlers. Never waits for a pattern. */
void vault_status_led_set_state(vault_led_state_t state);

/* Explicitly clear a latched recovery/security fault after it has been handled. */
void vault_status_led_clear_recovery_fault(vault_led_state_t next_state);

void vault_status_led_set_mode(vault_led_mode_t mode);
