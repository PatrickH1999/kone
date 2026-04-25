# Issues

- [ ] **Display Stack:** Finalize implementation of stack for displaying characters
    
    - [ ] Implement an equivalent to ``push`` and ``pop``
        
        - This includes a functionality that deletes the first row and moves content up by one row once ``DP`` (display pointer) reaches the end of the stack

    - [ ] Implement a function that displays the current display stack to the screen

    - [ ] Program counter needs to start at ``DISP_SIZE`` as ``DP`` lies in memory at addresses 0 to (DISP_SIZE - 1).
