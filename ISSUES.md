# Issues

Open points, kept short; the design limits that are not going to change are in
[README.md](README.md) instead.

- [ ] __Device race:__ cpu, display and keyboard run as three forked processes
  over one `mmap`ed `CPU` struct with no locking. The `R18` handshake is the
  only synchronization, and `display_fetch()` reads `R19` and `R18` without it,
  so a char can in principle be taken twice or missed.

- [ ] __Dropped keystrokes:__ `keyboard_push_cpu()` overwrites `R17` on every
  poll whether or not the program acknowledged the last char, so a key pressed
  while the program is blocked on the display handshake is lost. It shows up in
  `examples/basic.kasm` as a syntax error on a line that looks right on screen.

- [ ] __`basic`: no immediate statements.__ Only `RUN`, `LIST` and `CLEAR` are
  accepted without a line number; `PRINT 2 + 2` at the prompt is a syntax
  error, where a classic BASIC would run it.

- [ ] __`basic`: trailing tokens are ignored.__ Only `LET` reads an operator, so
  `PRINT A * B` prints `A` and says nothing about the `* B` behind it.

- [ ] __`kone -l` at `-v3`__ writes a few hundred MB per second, which is easy
  to point at a small filesystem by accident.
