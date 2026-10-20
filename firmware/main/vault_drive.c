#include "vault_drive.h"
#include "vault_storage.h"
#include "vault_crypto.h"
#include "esp_vfs_fat.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <errno.h>

#define ROOT VAULT_DIR "/usb-drive.hdr"
#define JOURNAL VAULT_DIR "/usb-drive.txn"
#define SEGMENT_BLOCKS 16384U
#define ROOT_BYTES 8192U
#define BLOCK_BYTES 4096U
#ifdef VAULT_DRIVE_TEST
extern bool vault_drive_test_stop(unsigned stage);
#else
#define vault_drive_test_stop(stage) false
#endif
#ifndef VAULT_DRIVE_MAX_SECTORS
#define VAULT_DRIVE_MAX_SECTORS 0xfffff800U
#endif
/* All persistent structures use the ESP32/little-endian layout, versioned by
 * their magic. Every block, allocation map and root is authenticated separately. */
typedef struct __attribute__((packed)) {
    uint32_t sectors, fat_sectors;
    uint8_t cluster_sectors, reserved[7], created[4096], padding[4080];
} root_plain_t;
typedef struct __attribute__((packed)) {
    uint8_t magic[8], uuid[16], iv[12], tag[16], ciphertext[ROOT_BYTES];
} root_record_t;
typedef struct __attribute__((packed)) {
    uint8_t iv[12], tag[16], ciphertext[BLOCK_BYTES];
} record_t;
typedef struct __attribute__((packed)) {
    uint8_t domain[8], uuid[16];uint32_t segment, block;
} aad_t;
typedef struct __attribute__((packed)) {
    uint8_t magic[8], uuid[16];uint32_t segment, block, new_segment;
    uint8_t iv[12], tag[16];
} journal_header_t;
_Static_assert(sizeof(root_plain_t)==ROOT_BYTES,"Root layout changed");
static struct {
    root_plain_t root;
    root_record_t root_record;
    record_t data_record, map_record;
    uint8_t map[BLOCK_BYTES], plain[BLOCK_BYTES];
} *s;
static uint8_t s_key[32];
static bool s_ready,s_creating,s_cached,s_map_cached;
static uint32_t s_cache_block,s_map_segment;
static bool bit(const uint8_t *p,uint32_t i) { return (p[i/8]>>(i%8))&1; }
static void setbit(uint8_t *p,uint32_t i) { p[i/8]|=1U<<(i%8); }
static void segment_path(char *out,size_t n,uint32_t seg) { snprintf(out,n,VAULT_DIR "/usb-%05lu.enc",(unsigned long)seg); }
static bool exists(const char *path) { struct stat st;return stat(path,&st)==0; }
bool vault_drive_exists(void) { return exists(ROOT)||exists(ROOT ".bak")||exists(JOURNAL); }
bool vault_drive_ready(void) { return s_ready; }
bool vault_drive_creating(void) { return s_creating; }
unsigned vault_drive_progress(void) { return s_ready?100:0; }
uint32_t vault_drive_sector_count(void) { return s && (s_ready||s_creating)?s->root.sectors:0; }
void vault_drive_close(void) {
    s_ready=s_creating=s_cached=s_map_cached=false;
    vault_secure_zero(s_key,sizeof(s_key));
    if(s) { vault_secure_zero(s,sizeof(*s));free(s);s=NULL; }
}
static bool finish(FILE *fp,bool ok) {
    if(fflush(fp)!=0) ok=false;
    if(fsync(fileno(fp))!=0) ok=false;
    if(fclose(fp)!=0) ok=false;
    return ok;
}
static esp_err_t crypt_record(bool encrypt,uint32_t seg,uint32_t block,record_t *r,uint8_t *plain) {
    aad_t aad={.domain={'V','L','T','B','L','K','2',0},.segment=seg,.block=block};
    memcpy(aad.uuid,s->root_record.uuid,16);
    if(encrypt) {
        vault_crypto_random(r->iv,12);
        return vault_crypto_aes_gcm_encrypt(s_key,r->iv,12,(uint8_t*)&aad,sizeof(aad),plain,BLOCK_BYTES,r->ciphertext,r->tag,16);
    }
    return vault_crypto_aes_gcm_decrypt(s_key,r->iv,12,(uint8_t*)&aad,sizeof(aad),r->ciphertext,BLOCK_BYTES,r->tag,16,plain);
}
static esp_err_t crypt_root(bool encrypt) {
    root_record_t *r=&s->root_record;
    if(encrypt) {
        vault_crypto_random(r->iv,12);
        return vault_crypto_aes_gcm_encrypt(s_key,r->iv,12,(uint8_t*)r,24,(uint8_t*)&s->root,ROOT_BYTES,r->ciphertext,r->tag,16);
    }
    return vault_crypto_aes_gcm_decrypt(s_key,r->iv,12,(uint8_t*)r,24,r->ciphertext,ROOT_BYTES,r->tag,16,(uint8_t*)&s->root);
}
static bool valid_root(void) {
    uint32_t sectors=s->root.sectors, fat=s->root.fat_sectors, spc=s->root.cluster_sectors;
    if(memcmp(s->root_record.magic,"VLTDSK2",8) || sectors<131072 || sectors>VAULT_DRIVE_MAX_SECTORS ||
       (sectors&2047) || !spc || spc>128 || (spc&(spc-1)) || !fat || (uint64_t)fat*2+32>=sectors) return false;
    uint64_t clusters=(sectors-32-2*fat)/spc;
    return clusters>=65525 && clusters<0x0ffffff5 && (uint64_t)fat*512>=(clusters+2)*4;
}
static bool save_root(void) {
    FILE *fp=fopen(ROOT ".tmp","wb");if(!fp)return false;
    if(!finish(fp,fwrite(&s->root_record,1,sizeof(s->root_record),fp)==sizeof(s->root_record))) return false;
    unlink(ROOT ".bak");
    if(rename(ROOT,ROOT ".bak")!=0 && errno!=ENOENT) return false;
    if(rename(ROOT ".tmp",ROOT)!=0) { rename(ROOT ".bak",ROOT);return false; }
    unlink(ROOT ".bak");return true;
}
/* An acknowledged write has a durable authenticated redo journal before any
 * primary data/map/root changes. Replay is idempotent; incomplete .tmp files
 * are never replayed. The physical SD FAT itself still needs safe removal. */
static bool apply_journal(void) {
    journal_header_t h;
    FILE *fp=fopen(JOURNAL,"rb");if(!fp)return false;
    bool ok=fread(&h,1,sizeof(h),fp)==sizeof(h) &&
        fread(&s->data_record,1,sizeof(s->data_record),fp)==sizeof(s->data_record) &&
        fread(&s->map_record,1,sizeof(s->map_record),fp)==sizeof(s->map_record) &&
        fread(&s->root_record,1,sizeof(s->root_record),fp)==sizeof(s->root_record) && fgetc(fp)==EOF;
    if(fclose(fp)!=0)ok=false;
    if(!ok || memcmp(h.magic,"VLTTXN2",8) || h.block>=SEGMENT_BLOCKS || h.new_segment>1 ||
       memcmp(h.uuid,s->root_record.uuid,16)) return false;
    if(vault_crypto_aes_gcm_decrypt(s_key,h.iv,12,(uint8_t*)&h,36,NULL,0,h.tag,16,NULL)!=ESP_OK ||
       crypt_root(false)!=ESP_OK || !valid_root() ||
       (uint64_t)h.segment*SEGMENT_BLOCKS+h.block >= (uint64_t)s->root.sectors/8 ||
       !bit(s->root.created,h.segment) ||
       crypt_record(false,h.segment,UINT32_MAX,&s->map_record,s->map)!=ESP_OK || !bit(s->map,h.block) ||
       crypt_record(false,h.segment,h.block,&s->data_record,s->plain)!=ESP_OK) return false;
    if(h.new_segment) {
        for(uint32_t i=0;i<SEGMENT_BLOCKS;i++) if(i!=h.block && bit(s->map,i))return false;
    }
    char path[160];segment_path(path,sizeof(path),h.segment);
    fp=fopen(path,"r+b");
    if(!fp && h.new_segment) fp=fopen(path,"w+b");
    if(!fp)return false;
    long pos=(long)(h.block+1)*sizeof(record_t);
    ok=fseek(fp,pos,SEEK_SET)==0 && fwrite(&s->data_record,1,sizeof(s->data_record),fp)==sizeof(s->data_record) &&
       fseek(fp,0,SEEK_SET)==0 && fwrite(&s->map_record,1,sizeof(s->map_record),fp)==sizeof(s->map_record);
    if(!finish(fp,ok) || vault_drive_test_stop(2) || !save_root() || vault_drive_test_stop(3))return false;
    /* If deletion fails, stop serving writes until next unlock replays it. */
    if(unlink(JOURNAL)!=0)return false;
    s_cached=s_map_cached=false;return true;
}
static void put16(uint8_t *p,uint16_t v) { p[0]=v;p[1]=v>>8; }
static void put32(uint8_t *p,uint32_t v) { put16(p,v);put16(p+2,v>>16); }
/* Lazy initial FAT32 contents are deterministic. Authenticated allocation maps
 * distinguish these untouched blocks from missing/corrupted written data. */
static void initial_block(uint32_t block,uint8_t *p) {
    memset(p,0,BLOCK_BYTES);
    uint32_t fat=s->root.fat_sectors,data_start=32+2*fat;
    for(unsigned i=0;i<8;i++) {
        uint32_t sector=block*8+i;uint8_t *b=p+i*512;
        if(sector==0 || sector==6) {
            b[0]=0xeb;b[1]=0x58;b[2]=0x90;memcpy(b+3,"MSDOS5.0",8);
            put16(b+11,512);b[13]=s->root.cluster_sectors;put16(b+14,32);b[16]=2;b[21]=0xf8;
            put16(b+24,63);put16(b+26,255);put32(b+32,s->root.sectors);put32(b+36,fat);
            put32(b+44,2);put16(b+48,1);put16(b+50,6);b[64]=0x80;b[66]=0x29;
            memcpy(b+67,s->root_record.uuid,4);memcpy(b+71,"ESP32 VAULT",11);memcpy(b+82,"FAT32   ",8);
            b[510]=0x55;b[511]=0xaa;
        } else if(sector==1 || sector==7) {
            put32(b,0x41615252);put32(b+484,0x61417272);
            put32(b+488,(s->root.sectors-data_start)/s->root.cluster_sectors-1);
            put32(b+492,3);put32(b+508,0xaa550000);
        } else if(sector==32 || sector==32+fat) {
            put32(b,0x0ffffff8);put32(b+4,UINT32_MAX);put32(b+8,0x0fffffff);
        } else if(sector==data_start) { memcpy(b,"ESP32 VAULT",11);b[11]=8; }
    }
}
esp_err_t vault_drive_open(const uint8_t key[32],bool create) {
    if(!key || s || (create && vault_drive_exists())) return ESP_ERR_INVALID_STATE;
    s=calloc(1,sizeof(*s));if(!s)return ESP_ERR_NO_MEM;memcpy(s_key,key,32);
    if(create) {
        uint64_t total,free_bytes;
        if(esp_vfs_fat_info(VAULT_MOUNT_POINT,&total,&free_bytes)!=ESP_OK)goto fail;
        /* 2% reserve covers per-segment maps, filesystem cluster rounding,
         * journal/root backups and room for the legacy file area. */
        uint64_t sectors=free_bytes/100*98/sizeof(record_t)*8;
        if(sectors>VAULT_DRIVE_MAX_SECTORS)sectors=VAULT_DRIVE_MAX_SECTORS;
        sectors &= ~(uint64_t)2047;
        if(sectors<131072)goto fail;
        s->root.sectors=sectors;
        uint32_t spc=sectors>=134217728?64:sectors>=1048576?8:1;
        s->root.cluster_sectors=spc;
        uint64_t numerator=4*(sectors-32+2*spc),denominator=512*spc+8;
        s->root.fat_sectors=(numerator+denominator-1)/denominator;
        memcpy(s->root_record.magic,"VLTDSK2",8);vault_crypto_random(s->root_record.uuid,16);
        if(!valid_root())goto fail;
        s_creating=true;return ESP_OK;
    }
    if(exists(JOURNAL) && !apply_journal())goto fail;
    if(!exists(ROOT))rename(ROOT ".bak",ROOT);
    FILE *fp=fopen(ROOT,"rb");if(!fp)goto fail;
    bool ok=fread(&s->root_record,1,sizeof(s->root_record),fp)==sizeof(s->root_record) && fgetc(fp)==EOF;
    if(fclose(fp)!=0)ok=false;
    if(!ok || crypt_root(false)!=ESP_OK || !valid_root())goto fail;
    s_ready=true;return ESP_OK;
fail:
    vault_drive_close();return ESP_FAIL;
}
esp_err_t vault_drive_create_step(void) {
    if(!s_creating || !s)return ESP_ERR_INVALID_STATE;
    if(crypt_root(true)!=ESP_OK || !save_root()) { vault_drive_close();return ESP_FAIL; }
    s_creating=false;s_ready=true;return ESP_OK;
}
static esp_err_t load_block(uint32_t block) {
    if(s_cached && s_cache_block==block)return ESP_OK;
    s_cached=false;uint32_t seg=block/SEGMENT_BLOCKS,within=block%SEGMENT_BLOCKS;
    char path[160];segment_path(path,sizeof(path),seg);
    if(!s_map_cached || s_map_segment!=seg) {
        s_map_cached=false;
        if(bit(s->root.created,seg)) {
            FILE *fp=fopen(path,"rb");if(!fp)return ESP_FAIL;
            bool ok=fread(&s->map_record,1,sizeof(s->map_record),fp)==sizeof(s->map_record);
            if(fclose(fp)!=0)ok=false;
            if(!ok || crypt_record(false,seg,UINT32_MAX,&s->map_record,s->map)!=ESP_OK)return ESP_FAIL;
        } else memset(s->map,0,sizeof(s->map));
        s_map_segment=seg;s_map_cached=true;
    }
    if(bit(s->map,within)) {
        FILE *fp=fopen(path,"rb");if(!fp)return ESP_FAIL;
        bool ok=fseek(fp,(long)(within+1)*sizeof(record_t),SEEK_SET)==0 &&
            fread(&s->data_record,1,sizeof(s->data_record),fp)==sizeof(s->data_record);
        if(fclose(fp)!=0)ok=false;
        if(!ok || crypt_record(false,seg,within,&s->data_record,s->plain)!=ESP_OK)return ESP_FAIL;
    } else initial_block(block,s->plain);
    s_cache_block=block;s_cached=true;return ESP_OK;
}
static esp_err_t write_block(uint32_t block) {
    uint32_t seg=block/SEGMENT_BLOCKS,within=block%SEGMENT_BLOCKS;
    journal_header_t h={.magic={'V','L','T','T','X','N','2',0},.segment=seg,.block=within,.new_segment=!bit(s->root.created,seg)};
    memcpy(h.uuid,s->root_record.uuid,16);vault_crypto_random(h.iv,12);
    setbit(s->map,within);setbit(s->root.created,seg);
    if(crypt_record(true,seg,within,&s->data_record,s->plain)!=ESP_OK ||
       crypt_record(true,seg,UINT32_MAX,&s->map_record,s->map)!=ESP_OK || crypt_root(true)!=ESP_OK ||
       vault_crypto_aes_gcm_encrypt(s_key,h.iv,12,(uint8_t*)&h,36,NULL,0,NULL,h.tag,16)!=ESP_OK)goto fail;
    FILE *fp=fopen(JOURNAL ".tmp","wb");if(!fp)goto fail;
    bool ok=fwrite(&h,1,sizeof(h),fp)==sizeof(h) &&
        fwrite(&s->data_record,1,sizeof(s->data_record),fp)==sizeof(s->data_record) &&
        fwrite(&s->map_record,1,sizeof(s->map_record),fp)==sizeof(s->map_record) &&
        fwrite(&s->root_record,1,sizeof(s->root_record),fp)==sizeof(s->root_record);
    if(!finish(fp,ok) || rename(JOURNAL ".tmp",JOURNAL)!=0 || vault_drive_test_stop(1) || !apply_journal())goto fail;
    return ESP_OK;
fail:
    vault_drive_close();return ESP_FAIL;
}
static esp_err_t transfer(uint64_t offset,void *data,size_t size,bool write) {
    if(!s_ready || !s)return ESP_ERR_INVALID_STATE;
    uint64_t capacity=(uint64_t)s->root.sectors*512;
    if((size && !data) || offset>capacity || size>capacity-offset)return ESP_ERR_INVALID_ARG;
    uint8_t *p=data;
    while(size) {
        uint32_t block=offset/BLOCK_BYTES;size_t within=offset%BLOCK_BYTES,n=BLOCK_BYTES-within;if(n>size)n=size;
        if(load_block(block)!=ESP_OK) { vault_drive_close();return ESP_FAIL; }
        if(write) {
            memcpy(s->plain+within,p,n);
            if(write_block(block)!=ESP_OK)return ESP_FAIL;
        } else memcpy(p,s->plain+within,n);
        offset+=n;p+=n;size-=n;
    }
    return ESP_OK;
}
esp_err_t vault_drive_read(uint64_t offset,void *data,size_t size) { return transfer(offset,data,size,false); }
esp_err_t vault_drive_write(uint64_t offset,const void *data,size_t size) { return transfer(offset,(void*)data,size,true); }
