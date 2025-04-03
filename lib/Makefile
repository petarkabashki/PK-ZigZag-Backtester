# Makefile for compiling shared libraries

# Compiler
CC = gcc

# Compiler flags
# -Wall: Enable all warnings
# -Werror: Treat warnings as errors
# -fPIC: Generate Position Independent Code (required for shared libraries)
# -O2: Optimization level 2
CFLAGS = -Wall -Werror -fPIC -O2

# Linker flags
# -shared: Create a shared library
LDFLAGS = -shared

# Math library (needed for zigzag)
LDLIBS = -lm

# Source files
ZIGZAG_SRC = zigzag.c
ENUM_TRADES_SRC = enumerate_trades.c

# Target shared libraries
ZIGZAG_TARGET = zigzag.so
ENUM_TRADES_TARGET = enumerate_trades.so

# Default target: build all libraries
all: $(ZIGZAG_TARGET) $(ENUM_TRADES_TARGET)

# Rule to build zigzag.so
$(ZIGZAG_TARGET): $(ZIGZAG_SRC)
	$(CC) $(CFLAGS) $(LDFLAGS) $^ -o $@ $(LDLIBS)

# Rule to build enumerate_trades.so
# No external libraries needed for enumerate_trades
$(ENUM_TRADES_TARGET): $(ENUM_TRADES_SRC)
	$(CC) $(CFLAGS) $(LDFLAGS) $^ -o $@

# Clean target: remove compiled files
clean:
	rm -f $(ZIGZAG_TARGET) $(ENUM_TRADES_TARGET) *.o

# Phony targets (targets that don't represent files)
.PHONY: all clean