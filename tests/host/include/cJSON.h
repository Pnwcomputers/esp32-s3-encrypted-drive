#pragma once
/* Public cJSON ABI, linked against the host's real libcjson for regression tests. */
typedef struct cJSON { struct cJSON *next, *prev, *child; int type; char *valuestring; int valueint; double valuedouble; char *string; } cJSON;
cJSON *cJSON_Parse(const char *);
void cJSON_Delete(cJSON *);
cJSON *cJSON_GetObjectItemCaseSensitive(const cJSON *, const char *);
int cJSON_IsString(const cJSON *);
int cJSON_IsNumber(const cJSON *);
int cJSON_IsBool(const cJSON *);
int cJSON_IsTrue(const cJSON *);
int cJSON_IsObject(const cJSON *);
cJSON *cJSON_CreateObject(void);
cJSON *cJSON_AddStringToObject(cJSON *, const char *, const char *);
cJSON *cJSON_AddNumberToObject(cJSON *, const char *, double);
cJSON *cJSON_AddBoolToObject(cJSON *, const char *, int);
char *cJSON_PrintUnformatted(const cJSON *);
