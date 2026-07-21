# Issues

- [ ] Add tests for kasm.c

- [x] __file not found__: Add a file not found warning to load_bootfile(), otherwise it loads zeros if the file is not found, but without proper notice

- [x] __Verbosity__: Integrate printing of CPU state and display state into the same page -> First print display (if required), then print cpu state below 

- [ ] __kasm Assembler:__ Reimplement in C

- [x] __Unit Tests:__ Write unit tests

- [x] __Display Stack:__ Finalize implementation of stack for displaying characters
    
    - [ ] Discard display stack implementation, implement display and keyboard as 'devices' (each with its own process)
        
        - Symbols are sent/received via two registers (2x1B, one for ASCII-Code (use accumulator!), the other as set-bit (for display, it gets set by sender so display can take ASCII-Code and unset the set-bit)
        - Set-bit: Single register (`0000 0ABC`), with `A`: Clear buffer, `B`: clear last char, `C`: push char to disp. 
