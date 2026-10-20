#include <assert.h>
#include <stdio.h>
#include "vault_crypto.c"
void esp_fill_random(void *p, size_t n) { memset(p,0x55,n); }
int main(void) {
 uint8_t key[32]={0},iv[12]={0},aad[4]={0},tag[16];
 assert(vault_crypto_aes_gcm_encrypt(key,iv,12,aad,4,NULL,0,NULL,tag,16)==ESP_OK);
 assert(vault_crypto_aes_gcm_decrypt(key,iv,12,aad,4,NULL,0,tag,16,NULL)==ESP_OK);
 tag[0]^=1;
 assert(vault_crypto_aes_gcm_decrypt(key,iv,12,aad,4,NULL,0,tag,16,NULL)==ESP_ERR_INVALID_STATE);
 assert(vault_crypto_aes_gcm_encrypt(key,iv,12,aad,4,NULL,1,NULL,tag,16)==ESP_ERR_INVALID_ARG);
 uint8_t input[1]={7},out[1]={0};
 assert(vault_crypto_aes_gcm_encrypt(key,iv,12,aad,4,input,1,out,tag,16)==ESP_OK && out[0]==7);
 puts("Crypto buffer contract checks passed (ESP-IDF empty-message requirement)");
}
