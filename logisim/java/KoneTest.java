import com.cburch.logisim.circuit.Circuit;
import com.cburch.logisim.circuit.CircuitState;
import com.cburch.logisim.comp.Component;
import com.cburch.logisim.file.Loader;
import com.cburch.logisim.file.LogisimFile;
import com.cburch.logisim.instance.StdAttr;
import com.cburch.logisim.proj.Project;
import com.cburch.logisim.std.memory.MemContents;

import java.io.File;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;

/**
 * Runs kasm binaries on logisim/kone.circ in Logisim Evolution's own simulator,
 * with no display, and checks what the circuit's TTY ends up showing. The
 * program is written into the "prog" ROM before each case, so one .circ file
 * serves them all.
 */
public class KoneTest {

    /** cycles is a timeout: a case stops as soon as the display says expect. */
    record Case(String program, int cycles, String keys, String expect) {}

    static final Case[] CASES = {
        new Case("bin/display.bin", 4000, "", " !\"#$%&"),
        new Case("bin/hello.bin", 20000, "", "Hello, World!"),
        new Case("bin/keyboard.bin", 10000, "Hi!", "Hi!"),
        new Case("bin/test_klib_mem.bin", 300000, "", "ALL PASS"),
    };

    /** Loader prompts reach the user through a Swing dialog, which is fatal here. */
    static class QuietLoader extends Loader {
        final List<String> errors = new ArrayList<>();

        QuietLoader() {
            super(null);
        }

        @Override
        public void showError(String description) {
            errors.add(description);
        }

        /**
         * Logisim leaves a .circ.autosave behind when the file is open in its
         * GUI and asks what to do with it. Answer "discard": the tests want the
         * generated file, and the answer costs nothing because the build writes
         * that file from source anyway.
         */
        @Override
        public int showOptions(String content, String title, String[] options,
                               int fallback) {
            System.out.println("[ NOTE ] ignoring a stale autosave file");
            return options.length - 1;
        }
    }

    static int passed = 0;
    static int failed = 0;
    static Circuit circuit;
    static Project project;

    public static void main(String[] args) throws Exception {
        final var loader = new QuietLoader();
        final var file = LogisimFile.load(new File(args[0]), loader);
        check("loads", loader.errors.isEmpty(), String.join("; ", loader.errors));
        project = new Project(file);
        circuit = file.getMainCircuit();

        for (final Case c : CASES) {
            final var name = new File(c.program()).getName().replace(".bin", "");
            try {
                final var shown = run(c);
                check(name, shown.contains(c.expect()),
                      "display shows \"" + shown.replace("\n", " / ") + "\"");
            } catch (Exception e) {
                check(name, false, e.toString());
            }
        }
        System.out.printf("%n%d/%d passed%n", passed, passed + failed);
        System.exit(failed == 0 ? 0 : 1);
    }

    /** Boots one program from reset and returns what the display ends up showing. */
    static String run(Case c) throws Exception {
        final var state = CircuitState.createRootState(project, circuit,
                                                       Thread.currentThread());
        state.getPropagator().propagate();   // no block has state before this
        Component tty = null;
        Component keyboard = null;
        CircuitState ttyState = null;
        CircuitState keyboardState = null;
        for (final var found : walk(state)) {
            final var comp = (Component) found[0];
            final var owner = (CircuitState) found[1];
            final var name = comp.getFactory().getName();
            final var label = comp.getAttributeSet().getValue(StdAttr.LABEL);
            if ("ROM".equals(name) && "prog".equals(label)) {
                load(contents(owner, comp), Files.readAllBytes(new File(c.program()).toPath()));
            } else if ("TTY".equals(name)) {
                tty = comp;
                ttyState = owner;
            } else if ("Keyboard".equals(name)) {
                keyboard = comp;
                keyboardState = owner;
            }
            owner.markComponentAsDirty(comp);
        }
        state.getPropagator().propagate();

        var shown = "";
        for (var i = 0; i < c.cycles(); i++) {
            if (i == 200 && !c.keys().isEmpty()) type(keyboardState, keyboard, c.keys());
            state.getPropagator().toggleClocks();
            state.getPropagator().propagate();
            state.getPropagator().toggleClocks();
            state.getPropagator().propagate();
            if (i % 250 == 0) {
                shown = screen(ttyState, tty);
                if (shown.contains(c.expect())) return shown;
            }
        }
        return screen(ttyState, tty);
    }

    /** Every component of the circuit and of its blocks, with the state it lives in. */
    static List<Object[]> walk(CircuitState state) {
        final var found = new ArrayList<Object[]>();
        for (final Component comp : state.getCircuit().getNonWires()) {
            found.add(new Object[] {comp, state});
        }
        for (final CircuitState sub : state.getSubstates()) found.addAll(walk(sub));
        return found;
    }

    static MemContents contents(CircuitState state, Component memory) throws Exception {
        final var data = state.getInstanceState(memory).getData();
        final var getter = data.getClass().getMethod("getContents");
        getter.setAccessible(true);
        return (MemContents) getter.invoke(data);
    }

    static void load(MemContents rom, byte[] program) {
        for (var i = 0; i < program.length; i++) rom.set(i, program[i] & 0xff);
    }

    static void type(CircuitState state, Component keyboard, String keys) throws Exception {
        final var data = state.getInstanceState(keyboard).getData();
        final var insert = data.getClass().getMethod("insert", char.class);
        insert.setAccessible(true);
        for (final char ch : keys.toCharArray()) insert.invoke(data, ch);
        state.markComponentAsDirty(keyboard);
        state.getPropagator().propagate();
    }

    static String screen(CircuitState state, Component tty) throws Exception {
        final var data = state.getInstanceState(tty).getData();
        final var rows = data.getClass().getMethod("getNrRows");
        final var row = data.getClass().getMethod("getRowString", int.class);
        rows.setAccessible(true);
        row.setAccessible(true);
        final int n = (Integer) rows.invoke(data);
        final var out = new StringBuilder();
        for (var i = 0; i < n; i++) {
            final var text = (String) row.invoke(data, i);
            if (!text.isBlank()) out.append(text.stripTrailing()).append("\n");
        }
        return out.toString();
    }

    static void check(String name, boolean ok, String detail) {
        if (ok) {
            passed++;
        } else {
            failed++;
        }
        final var color = System.console() != null;
        final var tag = ok ? "[ PASS ]" : "[ FAIL ]";
        System.out.println((color ? (ok ? "\033[38;2;0;200;0m" : "\033[38;2;200;0;0m")
                                    + tag + "\033[0m" : tag)
                           + " " + name + (ok ? "" : ": " + detail));
    }
}
