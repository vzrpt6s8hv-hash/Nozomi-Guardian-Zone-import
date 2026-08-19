"""
Tkinter GUI for the Nozomi Guardian Zone Import Tool.

This module intentionally imports tkinter only inside launch_gui() so that
nozomi_zone_import_tool.core and the CLI can be used (and unit tested) in
headless environments without Tk installed.
"""

import os

import pandas as pd

from .core import (
    EDITABLE_FIELD_KEYS,
    FIELD_KEYS,
    FIELD_LABELS,
    apply_mapping,
    auto_map_asset_columns,
    auto_map_columns,
    generate_config_text,
    load_table_file,
    parse_config_text,
    suggest_zones_from_assets,
)


def launch_gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, simpledialog

    class MappingDialog(tk.Toplevel):
        """Let the user review/adjust the automatic column -> field mapping."""

        def __init__(self, master, columns, mapping):
            super().__init__(master)
            self.title("Map columns to Guardian zone fields")
            self.geometry("560x620")
            self.result = None
            self.columns = [""] + list(columns)
            self.vars = {}

            info = tk.Label(
                self,
                text="Columns were auto-mapped where possible (shown below). Any field\n"
                     "marked '<-- select manually' could not be auto-detected - pick its\n"
                     "matching column from the dropdown yourself. Zone Name and Networks\n"
                     "are required; every other field can be left blank.",
                justify="left", anchor="w"
            )
            info.pack(fill="x", padx=10, pady=(10, 4))

            canvas_frame = ttk.Frame(self)
            canvas_frame.pack(fill="both", expand=True, padx=10, pady=4)
            canvas = tk.Canvas(canvas_frame, borderwidth=0)
            scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
            inner = ttk.Frame(canvas)
            inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=inner, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            self.combos = {}
            for i, key in enumerate(FIELD_KEYS + ["output_mode"]):
                label_text = FIELD_LABELS.get(key, "Output Mode override (full/compact, optional)")
                required = key in ("zone_name", "networks")
                auto_found = bool(mapping.get(key, ""))
                lbl = tk.Label(inner, text=label_text + (" *" if required else ""),
                                anchor="w",
                                fg=("black" if auto_found else ("#b30000" if required else "#b36b00")))
                lbl.grid(row=i, column=0, sticky="w", padx=4, pady=3)
                var = tk.StringVar(value=mapping.get(key, ""))
                combo = ttk.Combobox(inner, textvariable=var, values=self.columns,
                                      width=32, state="readonly")
                combo.grid(row=i, column=1, sticky="w", padx=4, pady=3)
                self.vars[key] = var
                self.combos[key] = (combo, lbl, label_text, required)
                note = tk.Label(
                    inner,
                    text=("" if auto_found else "<-- select manually (not auto-detected)"),
                    fg="#b30000" if required else "#b36b00", anchor="w"
                )
                note.grid(row=i, column=2, sticky="w", padx=4, pady=3)
                self.combos[key] = self.combos[key] + (note,)

                def on_change(_evt=None, k=key, n=note, l=lbl, req=required):
                    if self.vars[k].get():
                        n.config(text="")
                        l.config(fg="black")
                    else:
                        n.config(text="<-- select manually (not auto-detected)")
                        l.config(fg="#b30000" if req else "#b36b00")
                combo.bind("<<ComboboxSelected>>", on_change)

            btns = ttk.Frame(self)
            btns.pack(fill="x", padx=10, pady=10)
            ttk.Button(btns, text="Apply", command=self.on_apply).pack(side="right")
            ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=6)

        def on_apply(self):
            mapping = {k: v.get() for k, v in self.vars.items()}
            if not mapping.get("zone_name") or not mapping.get("networks"):
                messagebox.showerror(
                    "Mapping incomplete",
                    "Please map both 'Zone Name' and 'Networks / CIDR' before continuing."
                )
                return
            self.result = mapping
            self.destroy()

    class AssetMappingDialog(tk.Toplevel):
        """Map columns of a raw asset export (IP / VLAN / Segment / Label)
        before deriving suggested zones from it."""

        def __init__(self, master, columns, mapping):
            super().__init__(master)
            self.title("Map asset export columns")
            self.geometry("520x340")
            self.result = None
            self.columns = [""] + list(columns)
            self.vars = {}

            info = tk.Label(
                self,
                text="Map the columns from your asset export. Provide either a\n"
                     "Segment/Subnet column, or an IP Address column (Guardian\n"
                     "IP ranges will be summarized into CIDR blocks automatically).\n"
                     "A VLAN column is optional but recommended - it drives whether\n"
                     "each suggested zone gets 'assigned_vlan_id' (unique network)\n"
                     "or 'matching_vlan_id' (network reused across VLANs/segments).",
                justify="left", anchor="w"
            )
            info.pack(fill="x", padx=10, pady=(10, 8))

            grid = ttk.Frame(self)
            grid.pack(fill="x", padx=10)
            labels = {
                "ip": "IP Address column",
                "vlan": "VLAN column (optional)",
                "segment": "Segment / Subnet / Site column",
                "label": "Asset Label / Hostname (optional, unused in zone name)",
            }
            for i, key in enumerate(["ip", "vlan", "segment", "label"]):
                tk.Label(grid, text=labels[key], anchor="w").grid(
                    row=i, column=0, sticky="w", padx=4, pady=4)
                var = tk.StringVar(value=mapping.get(key, ""))
                combo = ttk.Combobox(grid, textvariable=var, values=self.columns,
                                      width=32, state="readonly")
                combo.grid(row=i, column=1, sticky="w", padx=4, pady=4)
                self.vars[key] = var

            btns = ttk.Frame(self)
            btns.pack(fill="x", padx=10, pady=14)
            ttk.Button(btns, text="Suggest Zones", command=self.on_apply).pack(side="right")
            ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=6)

        def on_apply(self):
            mapping = {k: v.get() for k, v in self.vars.items()}
            if not mapping.get("ip") and not mapping.get("segment"):
                messagebox.showerror(
                    "Mapping incomplete",
                    "Please map at least an IP Address column or a Segment/Subnet column."
                )
                return
            self.result = mapping
            self.destroy()

    class BulkEditDialog(tk.Toplevel):
        """Set one field to a single value across the selected/all rows."""

        def __init__(self, master, selected_count, total_count):
            super().__init__(master)
            self.title("Bulk edit field")
            self.resizable(False, False)
            self.result = None

            ttk.Label(self, text="Field:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
            self.field_var = tk.StringVar(value=FIELD_KEYS[2])
            field_choices = [k for k in FIELD_KEYS if k not in ("zone_name",)] + ["output_mode"]
            combo = ttk.Combobox(self, textvariable=self.field_var, state="readonly",
                                  values=field_choices, width=36,
                                  postcommand=None)
            combo["values"] = [FIELD_LABELS.get(k, k) + f"  [{k}]" for k in field_choices]
            self._field_keys = field_choices
            combo.current(0)
            combo.grid(row=0, column=1, padx=8, pady=6)
            self._combo = combo

            ttk.Label(self, text="New value:").grid(row=1, column=0, sticky="w", padx=8, pady=6)
            self.value_var = tk.StringVar()
            entry = ttk.Entry(self, textvariable=self.value_var, width=30)
            entry.grid(row=1, column=1, padx=8, pady=6)
            entry.focus_set()

            self.scope_var = tk.StringVar(
                value="selected" if selected_count else "all")
            scope_frame = ttk.Frame(self)
            scope_frame.grid(row=2, column=0, columnspan=2, sticky="w", padx=8, pady=4)
            ttk.Radiobutton(scope_frame, text=f"Selected rows ({selected_count})",
                             variable=self.scope_var, value="selected",
                             state=("normal" if selected_count else "disabled")).pack(anchor="w")
            ttk.Radiobutton(scope_frame, text=f"All rows ({total_count})",
                             variable=self.scope_var, value="all").pack(anchor="w")

            self.only_if_empty = tk.BooleanVar(value=False)
            ttk.Checkbutton(self, text="Only fill rows where this field is currently empty",
                             variable=self.only_if_empty).grid(
                row=3, column=0, columnspan=2, sticky="w", padx=8, pady=4)

            btns = ttk.Frame(self)
            btns.grid(row=4, column=0, columnspan=2, pady=10)
            ttk.Button(btns, text="Apply", command=self.on_apply).pack(side="left", padx=6)
            ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=6)

        def on_apply(self):
            idx = self._combo.current()
            key = self._field_keys[idx]
            self.result = {
                "key": key,
                "value": self.value_var.get(),
                "scope": self.scope_var.get(),
                "only_if_empty": self.only_if_empty.get(),
            }
            self.destroy()

    class App(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Nozomi Guardian Zone Import Tool")
            self.geometry("1180x640")
            self.rows = []  # list[dict] - source of truth
            self.default_mode = tk.StringVar(value="full")
            self._build_menu()
            self._build_toolbar()
            self._build_table()
            self._build_statusbar()

        # ---- UI construction -------------------------------------------------
        def _build_menu(self):
            menubar = tk.Menu(self)

            filemenu = tk.Menu(menubar, tearoff=0)
            filemenu.add_command(label="Import CSV / Excel / Word File...",
                                  command=self.on_import_file)
            filemenu.add_command(label="Open Existing Guardian Config (.cfg)...",
                                  command=self.on_open_cfg)
            filemenu.add_command(label="Suggest Zones from Asset Export...",
                                  command=self.on_suggest_from_assets)
            filemenu.add_separator()
            filemenu.add_command(label="Export Guardian Zone Config...",
                                  command=self.on_export)
            filemenu.add_command(label="Save Mapped Data as CSV Template...",
                                  command=self.on_save_template)
            filemenu.add_separator()
            filemenu.add_command(label="Quit", command=self.destroy)
            menubar.add_cascade(label="File", menu=filemenu)

            editmenu = tk.Menu(menubar, tearoff=0)
            editmenu.add_command(label="Add Row", command=self.on_add_row)
            editmenu.add_command(label="Delete Selected Row(s)", command=self.on_delete_rows)
            editmenu.add_separator()
            editmenu.add_command(label="Bulk Edit Field...", command=self.on_bulk_edit)
            menubar.add_cascade(label="Edit", menu=editmenu)

            helpmenu = tk.Menu(menubar, tearoff=0)
            helpmenu.add_command(label="About", command=self.on_about)
            menubar.add_cascade(label="Help", menu=helpmenu)

            self.config(menu=menubar)

        def _build_toolbar(self):
            bar = ttk.Frame(self)
            bar.pack(fill="x", padx=8, pady=6)

            ttk.Button(bar, text="Import File...", command=self.on_import_file).pack(side="left")
            ttk.Button(bar, text="Open Existing .cfg...", command=self.on_open_cfg).pack(
                side="left", padx=(6, 0))
            ttk.Button(bar, text="Suggest Zones from Asset Export...",
                       command=self.on_suggest_from_assets).pack(side="left", padx=(6, 0))
            ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=10)

            ttk.Button(bar, text="Add Row", command=self.on_add_row).pack(side="left")
            ttk.Button(bar, text="Delete Selected", command=self.on_delete_rows).pack(
                side="left", padx=(6, 0))
            ttk.Button(bar, text="Bulk Edit Field...", command=self.on_bulk_edit).pack(
                side="left", padx=(6, 0))
            ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=10)

            ttk.Label(bar, text="Default output mode:").pack(side="left")
            ttk.Combobox(bar, textvariable=self.default_mode, state="readonly",
                         values=["full", "compact"], width=10).pack(side="left", padx=(4, 0))
            ttk.Label(
                bar,
                text="  (full = write every field, blank if unset; compact = only "
                     "write fields that have a value; a row's 'output_mode' column overrides this)"
            ).pack(side="left")

            ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=10)
            ttk.Button(bar, text="Preview Output", command=self.on_preview).pack(side="left")
            ttk.Button(bar, text="Export .cfg...", command=self.on_export).pack(
                side="left", padx=(6, 0))

        def _build_table(self):
            frame = ttk.Frame(self)
            frame.pack(fill="both", expand=True, padx=8, pady=4)

            columns = EDITABLE_FIELD_KEYS
            self.tree = ttk.Treeview(frame, columns=columns, show="headings",
                                      selectmode="extended")
            for key in columns:
                heading = FIELD_LABELS.get(key, "Output Mode")
                width = 160 if key in ("zone_name", "networks", "security_profile") else 110
                self.tree.heading(key, text=heading)
                self.tree.column(key, width=width, anchor="w", stretch=False)

            vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
            hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
            self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

            self.tree.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)

            self.tree.bind("<Double-1>", self.on_cell_double_click)
            self._edit_widget = None

        def _build_statusbar(self):
            self.status = tk.StringVar(value="No data loaded. Use File > Import to begin.")
            bar = ttk.Label(self, textvariable=self.status, anchor="w",
                             relief="sunken")
            bar.pack(fill="x", side="bottom")

        # ---- Data <-> Treeview sync -------------------------------------------
        def refresh_table(self):
            self.tree.delete(*self.tree.get_children())
            for i, row in enumerate(self.rows):
                values = [row.get(k, "") for k in EDITABLE_FIELD_KEYS]
                self.tree.insert("", "end", iid=str(i), values=values)
            self.status.set(f"{len(self.rows)} zone(s) loaded.")

        def selected_indices(self):
            return sorted(int(iid) for iid in self.tree.selection())

        # ---- File menu actions -------------------------------------------------
        def on_import_file(self):
            path = filedialog.askopenfilename(
                title="Select a CSV, Excel or Word file",
                filetypes=[
                    ("Supported files", "*.csv *.xlsx *.xlsm *.xls *.docx *.tsv *.txt"),
                    ("CSV files", "*.csv"),
                    ("Excel files", "*.xlsx *.xlsm *.xls"),
                    ("Word documents", "*.docx"),
                    ("All files", "*.*"),
                ]
            )
            if not path:
                return
            try:
                df = load_table_file(path)
                if df.empty or len(df.columns) == 0:
                    messagebox.showerror("Empty file", "No data / columns were found in that file.")
                    return
                mapping = auto_map_columns(list(df.columns))
                dialog = MappingDialog(self, list(df.columns), mapping)
                self.wait_window(dialog)
                if not dialog.result:
                    return
                new_rows = apply_mapping(df, dialog.result)
                self.rows = new_rows
                self.refresh_table()
                self.status.set(f"Imported {len(self.rows)} zone(s) from {os.path.basename(path)}.")
            except Exception as e:
                messagebox.showerror("Import failed", str(e))

        def on_open_cfg(self):
            path = filedialog.askopenfilename(
                title="Open existing Guardian zone config",
                filetypes=[("Config / text files", "*.cfg *.txt"), ("All files", "*.*")]
            )
            if not path:
                return
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
                rows = parse_config_text(text)
                if not rows:
                    messagebox.showerror("No zones found",
                                          "No 'vi zones add ...' commands were found in this file.")
                    return
                self.rows = rows
                self.refresh_table()
                self.status.set(f"Loaded {len(self.rows)} zone(s) from {os.path.basename(path)}.")
            except Exception as e:
                messagebox.showerror("Open failed", str(e))

        def on_suggest_from_assets(self):
            path = filedialog.askopenfilename(
                title="Select a Guardian asset export (CSV / Excel)",
                filetypes=[
                    ("Supported files", "*.csv *.xlsx *.xlsm *.xls *.tsv *.txt"),
                    ("CSV files", "*.csv"),
                    ("Excel files", "*.xlsx *.xlsm *.xls"),
                    ("All files", "*.*"),
                ]
            )
            if not path:
                return
            try:
                df = load_table_file(path)
                if df.empty or len(df.columns) == 0:
                    messagebox.showerror("Empty file", "No data / columns were found in that file.")
                    return
                mapping = auto_map_asset_columns(list(df.columns))
                dialog = AssetMappingDialog(self, list(df.columns), mapping)
                self.wait_window(dialog)
                if not dialog.result:
                    return
                new_rows, warnings = suggest_zones_from_assets(df, dialog.result)
                if not new_rows:
                    messagebox.showinfo("No zones suggested",
                                         "No zones could be derived from that asset export.")
                    return

                if self.rows:
                    choice = messagebox.askyesnocancel(
                        "Add suggested zones",
                        f"{len(new_rows)} candidate zone(s) were derived from the asset "
                        f"export.\n\nYes = append them to the {len(self.rows)} zone(s) "
                        f"already loaded.\nNo = replace the current zones with just these "
                        f"suggestions.\nCancel = discard the suggestions."
                    )
                    if choice is None:
                        return
                    if choice:
                        self.rows.extend(new_rows)
                    else:
                        self.rows = new_rows
                else:
                    self.rows = new_rows

                self.refresh_table()
                self.status.set(
                    f"Suggested {len(new_rows)} zone(s) from {os.path.basename(path)}. "
                    f"Review networks, names and VLAN fields (highlighted in the summary) before exporting."
                )

                if warnings:
                    win = tk.Toplevel(self)
                    win.title("Zone suggestions - review notes")
                    win.geometry("640x360")
                    tk.Label(
                        win,
                        text="These zones were suggested automatically. Please review them "
                             "(especially networks and VLAN fields) before exporting:",
                        justify="left", anchor="w", wraplength=620
                    ).pack(fill="x", padx=10, pady=(10, 4))
                    txt = tk.Text(win, wrap="word")
                    txt.pack(fill="both", expand=True, padx=10, pady=6)
                    txt.insert("1.0", "\n".join(f"- {w}" for w in warnings))
                    txt.configure(state="disabled")
                    ttk.Button(win, text="OK", command=win.destroy).pack(pady=(0, 10))
            except Exception as e:
                messagebox.showerror("Suggestion failed", str(e))

        def on_save_template(self):
            if not self.rows:
                messagebox.showinfo("Nothing to save", "There is no data loaded yet.")
                return
            path = filedialog.asksaveasfilename(
                title="Save mapped data as CSV",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")]
            )
            if not path:
                return
            df = pd.DataFrame(self.rows, columns=EDITABLE_FIELD_KEYS)
            df.to_csv(path, index=False)
            self.status.set(f"Saved template CSV to {path}")

        def build_output_text(self):
            return generate_config_text(self.rows, default_mode=self.default_mode.get())

        def on_preview(self):
            if not self.rows:
                messagebox.showinfo("Nothing to preview", "There is no data loaded yet.")
                return
            text = self.build_output_text()
            win = tk.Toplevel(self)
            win.title("Preview - Guardian zone config output")
            win.geometry("760x600")
            txt = tk.Text(win, wrap="none", font=("Courier New", 10))
            txt.pack(fill="both", expand=True)
            txt.insert("1.0", text)
            txt.configure(state="normal")
            btns = ttk.Frame(win)
            btns.pack(fill="x")
            ttk.Button(btns, text="Save As...", command=lambda: self._save_text(text)).pack(
                side="right", padx=8, pady=6)

        def _save_text(self, text):
            path = filedialog.asksaveasfilename(
                title="Export Guardian zone config",
                defaultextension=".cfg",
                filetypes=[("Guardian config", "*.cfg"), ("Text files", "*.txt")]
            )
            if not path:
                return
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            self.status.set(f"Exported config to {path}")

        def on_export(self):
            if not self.rows:
                messagebox.showinfo("Nothing to export", "There is no data loaded yet.")
                return
            missing = [r.get("zone_name", "(unnamed)") for r in self.rows if not r.get("networks")]
            if missing:
                if not messagebox.askyesno(
                    "Some zones have no networks",
                    "These zones have no networks/CIDR value:\n" + ", ".join(missing) +
                    "\n\nExport anyway?"
                ):
                    return
            self._save_text(self.build_output_text())

        # ---- Edit menu actions -------------------------------------------------
        def on_add_row(self):
            self.rows.append({k: "" for k in EDITABLE_FIELD_KEYS})
            self.refresh_table()
            children = self.tree.get_children()
            if children:
                self.tree.selection_set(children[-1])
                self.tree.see(children[-1])

        def on_delete_rows(self):
            idxs = self.selected_indices()
            if not idxs:
                messagebox.showinfo("No selection", "Select one or more rows first.")
                return
            if not messagebox.askyesno("Confirm delete", f"Delete {len(idxs)} row(s)?"):
                return
            for i in sorted(idxs, reverse=True):
                del self.rows[i]
            self.refresh_table()

        def on_bulk_edit(self):
            if not self.rows:
                messagebox.showinfo("Nothing to edit", "There is no data loaded yet.")
                return
            idxs = self.selected_indices()
            dialog = BulkEditDialog(self, selected_count=len(idxs), total_count=len(self.rows))
            self.wait_window(dialog)
            if not dialog.result:
                return
            key = dialog.result["key"]
            value = dialog.result["value"]
            scope = dialog.result["scope"]
            only_if_empty = dialog.result["only_if_empty"]
            targets = idxs if scope == "selected" else range(len(self.rows))
            changed = 0
            for i in targets:
                if only_if_empty and self.rows[i].get(key, ""):
                    continue
                self.rows[i][key] = value
                changed += 1
            self.refresh_table()
            self.status.set(f"Bulk edit: set '{FIELD_LABELS.get(key, key)}' = "
                             f"'{value}' on {changed} row(s).")

        # ---- Inline cell editing ------------------------------------------------
        def on_cell_double_click(self, event):
            region = self.tree.identify("region", event.x, event.y)
            if region != "cell":
                return
            row_id = self.tree.identify_row(event.y)
            col_id = self.tree.identify_column(event.x)
            if not row_id or not col_id:
                return
            col_index = int(col_id.replace("#", "")) - 1
            key = EDITABLE_FIELD_KEYS[col_index]
            x, y, w, h = self.tree.bbox(row_id, col_id)
            value = self.rows[int(row_id)].get(key, "")

            if self._edit_widget is not None:
                self._edit_widget.destroy()

            var = tk.StringVar(value=value)
            entry = ttk.Entry(self.tree, textvariable=var)
            entry.place(x=x, y=y, width=w, height=h)
            entry.focus_set()
            entry.select_range(0, "end")
            self._edit_widget = entry

            def commit(_event=None):
                self.rows[int(row_id)][key] = var.get()
                entry.destroy()
                self._edit_widget = None
                self.refresh_table()
                children = self.tree.get_children()
                if row_id in children:
                    self.tree.selection_set(row_id)

            def cancel(_event=None):
                entry.destroy()
                self._edit_widget = None

            entry.bind("<Return>", commit)
            entry.bind("<KP_Enter>", commit)
            entry.bind("<Escape>", cancel)
            entry.bind("<FocusOut>", commit)

        def on_about(self):
            from tkinter import messagebox as mb
            mb.showinfo(
                "About",
                "Nozomi Guardian Zone Import Tool\n\n"
                "Imports zone data from CSV / Excel / Word files (or an existing\n"
                "Guardian zone config), maps columns to Guardian zone fields, and\n"
                "exports 'vi zones ...' CLI commands compatible with Guardian's\n"
                "zone configuration import format.\n\n"
                "Double-click a cell to edit it. Select multiple rows and use\n"
                "'Bulk Edit Field...' to change one field across many zones at once."
            )

    app = App()
    app.mainloop()


