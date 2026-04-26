# Issues

- [ ] __Display Stack:__ Finalize implementation of stack for displaying characters
    
    - [ ] Implement an equivalent to ``push`` and ``pop``
        
        - This includes a functionality that deletes the first row and moves content up by one row once ``DP`` (display pointer) reaches the end of the stack

    - [ ] Implement a function that displays the current display stack to the screen

    - [ ] Adjust memory layout
        
        - ``DP`` lies in memory at addresses (MEM_SIZE - DISP_SIZE) to (MEM_SIZE - 1) (constant size)
   
        - ``SP`` lies in memory at addresses SP to (MEM_SIZE - DISP_SIZE - 1) (variable size)
