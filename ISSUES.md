# Issues

Open points, kept short; the design limits that are not going to change are in
[README.md](README.md) instead.

- [ ] __The SRAM sits on the main bus.__ On the memory board the 62256's data
  pins are its data in and data out merged, and data in is `BUS`, which the
  datapath's mux drives at all times; the RAM is output-enabled whenever it is
  not being written. The two fight on every cycle that is not a memory write.
  Logisim has no conflict there, because data in and data out are separate nets
  and a mux picks the ROM or the RAM. The fix is a 74245 between `BUS` and the
  RAM's data pins, enabled from the write strobe. Putting one into `memory()`
  breaks the write path in simulation, and neither tying `DIR` high with a rail
  nor with a constant, nor holding the transceiver enabled, changes that.
  **Do not have the memory board assembled until this is settled**; the other
  five are not affected.

- [ ] __No connectors for the display and the keyboard.__ Their lines reach the
  backplane, but no board carries a socket, so the Arduino bridge is wired to
  the stack connector by hand as `logisim/README.md` describes.

- [ ] __No bill of materials export.__ `PARTS.md` is the list to order from;
  `kicad-cli sch export bom` would give a machine readable one and there is no
  target for it.

- [ ] __The boards have never been built.__ DRC says manufacturable, not
  working. The reset RC and the 1 MHz clock in particular are reasoned about
  rather than measured: Logisim cannot simulate the one, and nothing adds up
  the propagation delays for the other. J6 exists so the clock can be slowed
  down.

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
