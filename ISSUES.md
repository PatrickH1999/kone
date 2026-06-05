# Issues

- [ ] __Display Stack:__ Finalize implementation of stack for displaying characters
    
    - [x] Implement an equivalent to ``push`` and ``pop``
        
        - This includes a functionality that deletes the first row and moves content up by one row once ``DP`` (display pointer) reaches the end of the stack
        
        - This can be implemented as a ring buffer with two registers: ``DRP`` (display row pointer) and ``DCP`` (display column pointer)

        - The stack has the length ((``DISP_NROWS`` + 1) × ``DISP_NCOLS``) (i.e., all display rows plus a display row base)

        - ``DRP`` increments by 1 after each line is written

    - [ ] Implement a function that displays the current display stack to the screen

    - [x] Adjust memory layout
        
        - ``DP`` lies in memory at addresses (MEM_SIZE - DISP_SIZE) to (MEM_SIZE - 1) (constant size)
   
        - ``SP`` lies in memory at addresses SP to (MEM_SIZE - DISP_SIZE - 1) (variable size)

- [x] __Verbocity:__ Implement an indicator that shows both program counter and cycle counter as ```[CC: <cycle_counter>, PC: <program_counter>]```
