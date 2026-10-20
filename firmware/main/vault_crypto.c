#include "vault_crypto.h"
#include <string.h>
#include "esp_random.h"
#include "esp_log.h"
#include "mbedtls/gcm.h"
#include "mbedtls/md.h"
#include "mbedtls/pkcs5.h"

static const char *TAG = "vault_crypto";

void vault_secure_zero(void *v, size_t n) {
    if (!v || n == 0) return;
    volatile uint8_t *p = (volatile uint8_t *)v;
    while (n--) {
        *p++ = 0;
    }
}

esp_err_t vault_crypto_random(uint8_t *dest, size_t length) {
    if (!dest) return ESP_ERR_INVALID_ARG;
    esp_fill_random(dest, length);
    return ESP_OK;
}

esp_err_t vault_crypto_kdf(const char *pin, size_t pin_len,
                           const uint8_t *salt, size_t salt_len,
                           uint32_t iterations,
                           uint8_t *out_key) {
    if (!pin || pin_len == 0 || !salt || salt_len == 0 || !out_key) {
        return ESP_ERR_INVALID_ARG;
    }

    int ret = mbedtls_pkcs5_pbkdf2_hmac_ext(MBEDTLS_MD_SHA256,
        (const unsigned char *)pin, pin_len, salt, salt_len,
        iterations, VAULT_KEY_SIZE, out_key);
    if (ret != 0) {
        ESP_LOGE(TAG, "PBKDF2 derivation failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

    return ESP_OK;
}

esp_err_t vault_crypto_aes_gcm_encrypt(const uint8_t *key,
                                       const uint8_t *iv, size_t iv_len,
                                       const uint8_t *aad, size_t aad_len,
                                       const uint8_t *input, size_t length,
                                       uint8_t *output,
                                       uint8_t *tag, size_t tag_len) {
    if (!key || !iv || !tag || (length > 0 && (!input || !output))) {
        return ESP_ERR_INVALID_ARG;
    }

    /* ESP-IDF's accelerated GCM update requires non-null buffers even for an
     * empty message. Keep length zero so only the AAD and tag are processed. */
    uint8_t empty = 0;
    if (length == 0) input = output = &empty;

    mbedtls_gcm_context gcm_ctx;
    mbedtls_gcm_init(&gcm_ctx);

    int ret = mbedtls_gcm_setkey(&gcm_ctx, MBEDTLS_CIPHER_ID_AES, key, 256);
    if (ret != 0) {
        ESP_LOGE(TAG, "mbedtls_gcm_setkey failed: -0x%04x", -ret);
        mbedtls_gcm_free(&gcm_ctx);
        return ESP_FAIL;
    }

    ret = mbedtls_gcm_crypt_and_tag(&gcm_ctx, MBEDTLS_GCM_ENCRYPT,
                                    length,
                                    iv, iv_len,
                                    aad, aad_len,
                                    input, output,
                                    tag_len, tag);
    mbedtls_gcm_free(&gcm_ctx);

    if (ret != 0) {
        ESP_LOGE(TAG, "mbedtls_gcm_crypt_and_tag failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

    return ESP_OK;
}

esp_err_t vault_crypto_aes_gcm_decrypt(const uint8_t *key,
                                       const uint8_t *iv, size_t iv_len,
                                       const uint8_t *aad, size_t aad_len,
                                       const uint8_t *input, size_t length,
                                       const uint8_t *tag, size_t tag_len,
                                       uint8_t *output) {
    if (!key || !iv || !tag || (length > 0 && (!input || !output))) {
        return ESP_ERR_INVALID_ARG;
    }

    uint8_t empty = 0;
    if (length == 0) input = output = &empty;

    mbedtls_gcm_context gcm_ctx;
    mbedtls_gcm_init(&gcm_ctx);

    int ret = mbedtls_gcm_setkey(&gcm_ctx, MBEDTLS_CIPHER_ID_AES, key, 256);
    if (ret != 0) {
        ESP_LOGE(TAG, "mbedtls_gcm_setkey failed: -0x%04x", -ret);
        mbedtls_gcm_free(&gcm_ctx);
        return ESP_FAIL;
    }

    ret = mbedtls_gcm_auth_decrypt(&gcm_ctx,
                                   length,
                                   iv, iv_len,
                                   aad, aad_len,
                                   tag, tag_len,
                                   input, output);
    mbedtls_gcm_free(&gcm_ctx);

    if (ret == MBEDTLS_ERR_GCM_AUTH_FAILED) {
        return ESP_ERR_INVALID_STATE; // Tag mismatch (corrupted data or wrong key)
    } else if (ret != 0) {
        ESP_LOGE(TAG, "mbedtls_gcm_auth_decrypt failed: -0x%04x", -ret);
        return ESP_FAIL;
    }

    return ESP_OK;
}
