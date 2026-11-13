#include <assert.h>
#include <string.h>
#include "sweet_novatek.h"

static unsigned downs, ups, last_slot, last_x, last_y;
static void emit(void *ctx, unsigned slot, int down, unsigned x, unsigned y)
{
    (void)ctx;
    assert(slot < 10 && x < 1080 && y < 2400);
    if (down) ++downs; else ++ups;
    last_slot = slot; last_x = x; last_y = y;
}
int main(void)
{
    uint8_t data[65] = {0};
    struct nvt_frame frame = {0}, previous = {0}, snapshot;
    /* Slot 10, last pixel: x=1079 (0x437), y=2399 (0x95f).
     * Upper pressure byte is indexed by record, not contact ID. */
    data[0] = 0x51; data[1] = 0x43; data[2] = 0x95; data[3] = 0x7f;
    data[5] = 0x23; data[62] = 1;
    assert(nvt_decode(data, 65, 1080, 2400, &frame) == NVT_OK);
    assert(frame.contact[9].pressure == 0x123 && frame.contact[9].width == 1);
    nvt_deliver(&previous, &frame, emit, 0);
    assert(downs == 1 && ups == 0 && last_slot == 9 && last_x == 1079 && last_y == 2399);
    snapshot = frame;
    /* Truncated transfers and duplicates must not manufacture release events. */
    for (size_t n = 0; n < 65; ++n)
        assert(nvt_decode(data, n, 1080, 2400, &frame) == NVT_INVALID);
    memcpy(data + 6, data, 6);
    assert(nvt_decode(data, 65, 1080, 2400, &frame) == NVT_INVALID);
    assert(memcmp(&frame, &snapshot, sizeof(frame)) == 0);
    memset(data, 0, sizeof(data));
    data[0] = 9; data[1] = 0x43; data[3] = 0x80; /* x=1080 */
    assert(nvt_decode(data, 65, 1080, 2400, &frame) == NVT_INVALID);
    memset(data, 0x77, 6);
    assert(nvt_decode(data, 65, 1080, 2400, &frame) == NVT_RECOVERY);
    memset(data, 0xfd, 6); data[1] = 0xfe;
    assert(nvt_decode(data, 65, 1080, 2400, &frame) == NVT_RECOVERY);
    assert(memcmp(&frame, &snapshot, sizeof(frame)) == 0);
    memset(data, 0, sizeof(data));
    assert(nvt_decode(data, 65, 1080, 2400, &frame) == NVT_OK);
    nvt_deliver(&previous, &frame, emit, 0);
    assert(ups == 1 && last_slot == 9 && last_x == 1079 && last_y == 2399);
    nvt_deliver(&previous, &frame, emit, 0);
    assert(ups == 1);
    /* Ten independent contacts, then movement followed by release. */
    for (unsigned i = 0; i < 10; ++i) data[6*i] = (uint8_t)(((i+1)<<3)|2);
    assert(nvt_decode(data, 65, 1080, 2400, &frame) == NVT_OK);
    nvt_deliver(&previous, &frame, emit, 0);
    assert(downs == 11);
    memset(data, 0xff, sizeof(data));
    assert(nvt_decode(data, 65, 1080, 2400, &frame) == NVT_OK);
    nvt_deliver(&previous, &frame, emit, 0);
    assert(ups == 11);
    return 0;
}
