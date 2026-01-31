CC := gcc
CFLAGS := -std=c2x -Wall -Wextra -Wpedantic -O2
LDFLAGS := 

TARGET := kone

SRCS := kone.c alu_functions.c cpu_functions.c utility.c
OBJS := $(SRCS:.c=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
		$(CC) $(OBJS) $(LDFLAGS) -o $@

$.o: $.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)

.PHONY: all clean
