###############################################################################
# Ferqon Scheduling Layer — Native Unit Tests
#
# Usage:
#   make              — build and run all three test suites
#   make ringbuf      — ring buffer only
#   make multicore    — SPSC inter-core queue
#   make singlecore   — UART ISR ring buffer path
#   make clean        — remove build artefacts
###############################################################################

CC      := gcc
CFLAGS  := -std=c11 -O0 -g \
            -Wall -Wextra -Wpedantic \
            -I../../core \
            -I../../core/platform \
            -I../../core/scheduling \
            -I../../drivers/inc \
            -I../../generated

# Unity test framework — PlatformIO caches it here after first `pio test` run;
# fall back to a system-installed unity if not present.
UNITY_SRC := unity/unity.c
UNITY_INC := unity/

CFLAGS  += -I$(UNITY_INC)

BUILDDIR := _build

PLATFORM_SRC := ../../core/platform/ferqon_plt_system.c

.PHONY: all ringbuf multicore singlecore clean

all: ringbuf multicore singlecore

# ── Ring buffer ──────────────────────────────────────────────────────────────
ringbuf: $(BUILDDIR)/test_ringbuf
	@echo "\n=== test_ringbuf ==="
	@./$(BUILDDIR)/test_ringbuf

$(BUILDDIR)/test_ringbuf: test_ringbuf.c $(UNITY_SRC) | $(BUILDDIR)
	$(CC) $(CFLAGS) $^ -o $@

# ── Multicore SPSC queue ─────────────────────────────────────────────────────
MULTICORE_FLAGS := -DFERQON_SCHED_MULTICORE=1 \
                   -DFERQON_SCHED_UART_ISR=0  \
                   -DFERQON_SCHED_QUEUE_DEPTH=8 \
                   -DFERQON_RAM_SIZE_BYTES=264000 \
                   -DFERQON_CORE_COUNT=2 \
                   -Wl,--wrap=FERQON_Drivers_HandleRequest

multicore: $(BUILDDIR)/test_sched_multicore
	@echo "\n=== test_sched_multicore ==="
	@./$(BUILDDIR)/test_sched_multicore

$(BUILDDIR)/test_sched_multicore: test_sched_multicore.c stubs.c \
    ../../core/scheduling/ferqon_sched_multicore.c \
    $(PLATFORM_SRC) \
    $(UNITY_SRC) | $(BUILDDIR)
	$(CC) $(CFLAGS) $(MULTICORE_FLAGS) $^ -o $@

# ── Single-core ISR path ─────────────────────────────────────────────────────
SINGLECORE_FLAGS := -DFERQON_SCHED_MULTICORE=0 \
                    -DFERQON_SCHED_UART_ISR=1 \
                    -DFERQON_ISR_RINGBUF_SIZE=256 \
                    -DFERQON_RAM_SIZE_BYTES=192000 \
                    -DFERQON_CORE_COUNT=1 \
                    -Wl,--wrap=FERQON_Protocol_FrameFeedByte \
                    -Wl,--wrap=FERQON_Drivers_HandleRequest

singlecore: $(BUILDDIR)/test_sched_singlecore
	@echo "\n=== test_sched_singlecore ==="
	@./$(BUILDDIR)/test_sched_singlecore

$(BUILDDIR)/test_sched_singlecore: test_sched_singlecore.c stubs.c \
    ../../core/scheduling/ferqon_sched_singlecore.c \
    $(PLATFORM_SRC) \
    $(UNITY_SRC) | $(BUILDDIR)
	$(CC) $(CFLAGS) $(SINGLECORE_FLAGS) $^ -o $@

$(BUILDDIR):
	mkdir -p $(BUILDDIR)

clean:
	rm -rf $(BUILDDIR)
