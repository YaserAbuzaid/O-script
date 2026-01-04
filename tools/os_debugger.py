
import json
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

def load_trace(path):
    with open(path, "r", encoding="utf-8") as f:
        events = json.load(f)
    # ensure sorted by step
    events = sorted(events, key=lambda e: e.get("step", 0))
    return events

def build_index(events):
    by_obj = {}
    steps = []
    for e in events:
        steps.append(e.get("step", 0))
        obj = e.get("object")
        if obj:
            by_obj.setdefault(obj, []).append(e)
    # sort per object
    for obj in by_obj:
        by_obj[obj] = sorted(by_obj[obj], key=lambda e: e.get("step", 0))
    return by_obj, (min(steps) if steps else 0), (max(steps) if steps else 0)

def last_event_leq(events, step):
    # binary search for rightmost event with step <= step
    lo, hi = 0, len(events)-1
    ans = None
    while lo <= hi:
        mid = (lo + hi)//2
        s = events[mid].get("step", 0)
        if s <= step:
            ans = events[mid]
            lo = mid + 1
        else:
            hi = mid - 1
    return ans

class DebuggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("O-script Trace Debugger")
        self.events = []
        self.by_obj = {}
        self.min_step = 0
        self.max_step = 0

        # top bar
        top = ttk.Frame(root, padding=8)
        top.pack(fill="x")

        self.file_label = ttk.Label(top, text="No trace loaded")
        self.file_label.pack(side="left")

        ttk.Button(top, text="Open trace.json…", command=self.open_file).pack(side="right")

        # main area
        main = ttk.Frame(root, padding=8)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="y")

        right = ttk.Frame(main)
        right.pack(side="right", fill="both", expand=True)

        ttk.Label(left, text="Object").pack(anchor="w")
        self.obj_var = tk.StringVar()
        self.obj_menu = ttk.Combobox(left, textvariable=self.obj_var, state="readonly", width=25)
        self.obj_menu.pack(fill="x")
        self.obj_menu.bind("<<ComboboxSelected>>", lambda _evt: self.refresh())

        ttk.Label(left, text="Events").pack(anchor="w", pady=(10,0))
        self.event_list = tk.Listbox(left, width=45, height=25)
        self.event_list.pack(fill="y", expand=True)
        self.event_list.bind("<<ListboxSelect>>", self.on_select_event)

        # step slider
        slider_frame = ttk.Frame(right)
        slider_frame.pack(fill="x")
        ttk.Label(slider_frame, text="Step").pack(side="left")
        self.step_var = tk.IntVar(value=0)
        self.slider = ttk.Scale(slider_frame, from_=0, to=0, orient="horizontal", command=self.on_slider)
        self.slider.pack(side="left", fill="x", expand=True, padx=8)
        self.step_label = ttk.Label(slider_frame, text="0")
        self.step_label.pack(side="left")

        # details
        ttk.Label(right, text="Event details").pack(anchor="w", pady=(10,0))
        self.details = tk.Text(right, height=10, wrap="word")
        self.details.pack(fill="x")

        ttk.Label(right, text="Object state at step").pack(anchor="w", pady=(10,0))
        self.state = tk.Text(right, height=12, wrap="word")
        self.state.pack(fill="both", expand=True)

    def open_file(self):
        path = filedialog.askopenfilename(title="Open O-script trace", filetypes=[("JSON files","*.json"), ("All files","*.*")])
        if not path:
            return
        try:
            self.events = load_trace(path)
            self.by_obj, self.min_step, self.max_step = build_index(self.events)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load trace:\n{e}")
            return

        self.file_label.config(text=path)
        objs = sorted(self.by_obj.keys())
        self.obj_menu["values"] = objs
        if objs:
            self.obj_var.set(objs[0])
        self.slider.configure(from_=self.min_step, to=self.max_step)
        self.slider.set(self.max_step)
        self.step_var.set(self.max_step)
        self.refresh()

    def on_slider(self, value):
        try:
            step = int(float(value))
        except:
            step = 0
        self.step_var.set(step)
        self.step_label.config(text=str(step))
        self.refresh(update_list_selection=False)

    def on_select_event(self, _evt):
        selection = self.event_list.curselection()
        if not selection:
            return
        idx = selection[0]
        obj = self.obj_var.get()
        if not obj or obj not in self.by_obj:
            return
        events = self.by_obj[obj]
        if idx < 0 or idx >= len(events):
            return
        step = events[idx].get("step", 0)
        self.slider.set(step)
        self.step_var.set(step)
        self.step_label.config(text=str(step))
        self.refresh(update_list_selection=True)

    def refresh(self, update_list_selection=True):
        obj = self.obj_var.get()
        step = self.step_var.get()

        self.event_list.delete(0, "end")
        if obj and obj in self.by_obj:
            for e in self.by_obj[obj]:
                t = e.get("type")
                s = e.get("step")
                field = e.get("field")
                old = e.get("old")
                new = e.get("new")
                if field is None:
                    line = f"{s:>4}  {t}"
                else:
                    line = f"{s:>4}  {t}  {field}: {old} -> {new}"
                self.event_list.insert("end", line)

            if update_list_selection:
                # highlight the last event <= step
                events = self.by_obj[obj]
                le = last_event_leq(events, step)
                if le:
                    idx = events.index(le)
                    self.event_list.selection_clear(0, "end")
                    self.event_list.selection_set(idx)
                    self.event_list.see(idx)

        # details text
        self.details.delete("1.0", "end")
        # global event at step?
        exact = next((e for e in self.events if e.get("step")==step), None)
        if exact:
            self.details.insert("end", json.dumps(exact, indent=2))
        else:
            self.details.insert("end", "(No event exactly at this step. Select an object to see its state.)")

        # state text
        self.state.delete("1.0", "end")
        if obj and obj in self.by_obj:
            le = last_event_leq(self.by_obj[obj], step)
            if le:
                state = le.get("fields_after", {})
                self.state.insert("end", f"{obj} at step {step}\n\n")
                if state:
                    for k in sorted(state.keys()):
                        self.state.insert("end", f"{k} = {state[k]}\n")
                else:
                    self.state.insert("end", "(no fields)\n")
            else:
                self.state.insert("end", f"{obj} has no events at or before step {step}.\n")
        else:
            self.state.insert("end", "Load a trace and select an object.")

if __name__ == "__main__":
    root = tk.Tk()
    app = DebuggerApp(root)
    root.mainloop()
