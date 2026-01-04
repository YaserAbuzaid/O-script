# O-script — an OOP language with time-travel objects (and VS Code support)

O-script is a tiny object-oriented scripting language where **every object is versioned**.

Each time you assign to a field (`this.x = ...`), that object records a reversible patch. You can then:

- `obj.undo();`       rewind the last field change on that object
- `obj.redo();`       re-apply the most recently undone change
- `obj.history();`    view a list of past field edits
- `obj.checkpoint("name");` create a named snapshot
- `obj.rollback("name");`   restore the object to that snapshot (undoable as one step)

It’s like **Git/time travel for objects**.

---

## Requirements

- Python 3.10+ recommended (3.8+ often works)
- VS Code (optional, but included setup makes it easy)

---

## Run a .os file

From the `o-script` folder:

```bash
python oscript.py examples/wow.os
```

Windows shortcut:

```bat
oscript.bat examples\wow.os
```

macOS/Linux shortcut:

```bash
./oscript.sh examples/wow.os
```

---

## Start a REPL

```bash
python oscript.py --repl
```

---

## VS Code: make `test.os` and run it

1) Open the **o-script** folder in VS Code.

2) Install the local syntax highlighting extension:

- Go to `vscode-extension/oscript-language/` and follow its `README.md` (copy into your VS Code extensions folder).
- Restart VS Code.

3) Create a new file like `test.os`.

4) Run it:

- Press **Ctrl+Shift+B** (or Cmd+Shift+B on Mac)
- Choose: **O-script: Run current .os file**

Extra tasks:
- **O-script: Run current .os file (trace -> trace.json)**
- **O-script: Open O-script Debugger (trace viewer)**

---

## Trace debugger (visual timeline)

Generate a trace:

```bash
python oscript.py examples/wow.os --trace trace.json
```

Open the GUI trace viewer:

```bash
python tools/os_debugger.py
```

---

## Language quick reference

### Statements / keywords
`class`, `fun`, `var`, `if`, `else`, `while`, `return`, `print`, `and`, `or`, `true`, `false`, `nil`, `this`, `new`

### Built-in functions
- `clock()` → seconds since epoch (float)
- `str(x)` → string form
- `type(x)` → type name
- `len(x)` → length of a string/list/dict
- `input([prompt])` → read a line from stdin
- `assert(cond[, msg])` → runtime assertion

### Object time travel methods
- `obj.undo()`
- `obj.redo()`
- `obj.history()`
- `obj.checkpoint("name")`
- `obj.rollback("name")`
- `obj.checkpoints()` → list checkpoint names
- `obj.id()` → stable object id (useful in traces)

---

## Examples

- `examples/wow.os` — maker portfolio demo script
- `examples/counter.os` — small OOP example
- `examples/checkpoint.os` — checkpoints + rollback
- `examples/test.os` — starter template (copy/modify)
- `examples/test2.os` — study tracker (copy/modify)
- `examples/test3.os` — not finished yet