#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
typedef unsigned long vm_offset_t;
typedef int DTEntry;
#define kSuccess 0
#define TOUCH_NORTH_PA 0x3900000
#define TOUCH_WEST_PA 0x3500000
static struct { vm_offset_t gpio, gpio_w; bool spi, dead; unsigned sp_clk, sp_mosi, sp_miso, sp_cs; } st;
static uint8_t memory[0x40000];
static uint32_t page;
static bool corrupt;
static void fts_xfer(const uint8_t *tx, uint8_t *rx, unsigned n) {
    if (n == 3 && tx[0] == 255) { page=((uint32_t)tx[1]<<15)|((uint32_t)tx[2]<<7); return; }
    unsigned address=page+(tx[0]&127);
    if (tx[0]&128) {
        assert(address+n-1 <= sizeof(memory));
        memcpy(memory+address,tx+1,n-1);
        if (address==0x3f10d && tx[1]==1) memory[0x22d60]=0xa1;
    } else {
        assert(rx && n>=2 && address+n-2<=sizeof(memory));
        memset(rx,0,n);memcpy(rx+2,memory+address,n-2);
        if (corrupt && address<0x30000) rx[2]^=1;
    }
}
static void touch_wait(unsigned n) { (void)n; }
static void sweet_hid_touch(int a,int b,int c,int d) { (void)a;(void)b;(void)c;(void)d; }
static int SecureDTLookupEntry(void *a,const char *b,DTEntry *c) { (void)a;(void)b;(void)c;return -1; }
static int SecureDTGetProperty(DTEntry a,const char *b,const void **c,unsigned long *d) { (void)a;(void)b;(void)c;(void)d;return -1; }
static vm_offset_t ml_io_map(unsigned a,unsigned b) { (void)b;return a; }
static void touch_gpio_mi(unsigned a,unsigned b,unsigned c,unsigned d,bool e,bool f) { (void)a;(void)b;(void)c;(void)d;(void)e;(void)f; }
static void fts_spi_cfg(void) {}
static void fts_io(unsigned a,bool b) { (void)a;(void)b; }
#include "sweet_novatek_spi.inc"
static void le(uint8_t *b,unsigned v) { for(unsigned i=0;i<4;i++) b[i]=(uint8_t)(v>>(8*i)); }
int main(void) {
    uint8_t fw[128]={0};struct nvt_segment p[32];unsigned count=0;
    le(fw,48);le(fw+4,0);le(fw+8,15);
    le(fw+12,64);le(fw+16,0x20000);le(fw+20,15);
    for(unsigned i=48;i<80;i++) fw[i]=(uint8_t)i;
    assert(nvt_segments(fw,sizeof(fw),p,&count)==0 && count==2);
    assert(nvt_download(fw,sizeof(fw))==0);
    assert(!memcmp(memory,fw+48,16) && !memcmp(memory+0x20000,fw+64,16));
    corrupt=true;assert(nvt_download(fw,sizeof(fw))==EIO);corrupt=false;
    le(fw+8,128);assert(nvt_segments(fw,sizeof(fw),p,&count)==EINVAL);
    le(fw+8,15);le(fw+4,0x3f000);assert(nvt_segments(fw,sizeof(fw),p,&count)==EINVAL);
    le(fw+4,0);fw[40]=0x10;assert(nvt_segments(fw,sizeof(fw),p,&count)==EINVAL);
    nvt_run(); /* no DT input: exits without MMIO */
    return 0;
}
