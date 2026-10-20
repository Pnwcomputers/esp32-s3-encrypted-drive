#pragma once
#include <stddef.h>
#include <string.h>
#define MBEDTLS_CIPHER_ID_AES 1
#define MBEDTLS_GCM_ENCRYPT 1
#define MBEDTLS_ERR_GCM_AUTH_FAILED -18
typedef struct { int unused; } mbedtls_gcm_context;
static inline void mbedtls_gcm_init(mbedtls_gcm_context *c) { (void)c; }
static inline void mbedtls_gcm_free(mbedtls_gcm_context *c) { (void)c; }
static inline int mbedtls_gcm_setkey(mbedtls_gcm_context *c,int id,const unsigned char *k,unsigned bits) { return 0; }
/* Model the ESP-IDF accelerated driver's non-null requirement, including n=0.
 * This adapter tests the wrapper contract, not cryptographic correctness. */
static inline int mbedtls_gcm_crypt_and_tag(mbedtls_gcm_context *c,int mode,size_t n,
 const unsigned char *iv,size_t il,const unsigned char *aad,size_t al,
 const unsigned char *in,unsigned char *out,size_t tl,unsigned char *tag) {
 if (!in || !out) return -20;
 if (n) memcpy(out,in,n);
 memset(tag,0x42,tl); return 0;
}
static inline int mbedtls_gcm_auth_decrypt(mbedtls_gcm_context *c,size_t n,
 const unsigned char *iv,size_t il,const unsigned char *aad,size_t al,
 const unsigned char *tag,size_t tl,const unsigned char *in,unsigned char *out) {
 if (!in || !out) return -20;
 for(size_t i=0;i<tl;i++) if(tag[i]!=0x42) return MBEDTLS_ERR_GCM_AUTH_FAILED;
 if(n) memcpy(out,in,n);
 return 0;
}
