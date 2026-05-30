#!/bin/sh

# Print content of binary file 1 byte (8 bits) per line (format: 0bXXXXXXXX)
xxd -b -c1 $1 | awk '{print $2}'
