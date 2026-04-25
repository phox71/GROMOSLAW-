# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import os, time, math, copy, random, textwrap
import numpy as np
from PIL import Image, ImageTk
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union, nearest_points
from engine_data import Hotpoint, WalkableArea, GamifikatorProject


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, justify=tk.LEFT, bg="#ffffe1", fg="black",
                 relief=tk.SOLID, borderwidth=1, font=("Segoe UI", 8)).pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


class GamifikatorEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("GAMIFIKATOR 2026 - v2.4.7")
        self.root.geometry("1650x950")
        self.root.configure(bg="#121212")

        self.project = None
        self.current_room_id = None
        self.mode = "Select"
        self.is_playing = False
        self.logs_visible = False
        self.undo_stack = []
        self.temp_points = []
        self.selected_object = None
        self.drag_data = {"obj": None, "mode": None, "off_x": 0, "off_y": 0,
                          "start_w": 0, "start_h": 0, "start_x": 0, "start_y": 0}
        self.view_scale = 1.0
        self.player_runtime_pos = [0, 0]
        self.player_target = [0, 0]
        self.active_dialogs = []
        self.swapped_hotpoints = set()
        self.bg_image_ref = None
        self.player_image_ref = None
        self.hp_images_refs = {}
        self.icons_ui = {}
        self.player_placeholder_raw = None
        self.log_history = []
        self.anim_tick = 0
        self.preview_anim_tick = 0
        self.facing_left = False
        self._lib_thumb_refs = {}
        self._lib_preview_ref = None
        self._anim_refs = {}
        self.game_state = {}
        self.active_dialog = None
        # {did, nid, phase:"npc"|"choices", end_time, choice_rects:[{cid,x1,y1,x2,y2}]}
        self.player_inventory = []
        self.collected_items = set()
        self._placeholder_ref = None

        self.load_ui_assets()
        self.setup_ui()
        self.setup_canvas_events()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.engine_loop()
        self.log("System Gamifikator v2.4.7 zaladowany.")

    def log(self, message):
        ts = time.strftime("%H:%M:%S")
        self.log_history.append(f"[{ts}] {message}")
        if hasattr(self, 'log_text'):
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"[{ts}] {message}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)

    def _toast(self, msg, level="info", duration=3500):
        if not hasattr(self, '_active_toasts'):
            self._active_toasts = []
        self._active_toasts = [f for f in self._active_toasts if f.winfo_exists()]
        bg = {"info": "#1a6fa8", "warn": "#b05c10", "error": "#8b0000"}.get(level, "#333")
        icon = {"info": "ℹ", "warn": "⚠", "error": "✕"}.get(level, "•")
        y_off = -12 - len(self._active_toasts) * 44
        frame = tk.Frame(self.root, bg=bg, padx=12, pady=8, cursor="hand2")
        tk.Label(frame, text=f"{icon}  {msg}", bg=bg, fg="white",
                 font=("Segoe UI", 9), wraplength=340, justify="left").pack()
        frame.place(relx=1.0, rely=1.0, anchor="se", x=-14, y=y_off)
        frame.lift()
        self._active_toasts.append(frame)
        frame.bind("<Button-1>", lambda e: frame.destroy())
        self.root.after(duration, lambda: frame.destroy() if frame.winfo_exists() else None)
        self.log(f"[{level.upper()}] {msg}")

    def load_ui_assets(self):
        paths = {
            "Select":   r"C:\Users\rafal\Downloads\choose.png",
            "Walkable": r"C:\Users\rafal\Downloads\square.png",
            "Hotpoint": r"C:\Users\rafal\Downloads\double-tap.png",
            "Edit":     r"C:\Users\rafal\Downloads\edit.png",
            "Player":   r"C:\Users\rafal\Downloads\walk.png",
        }
        for name, path in paths.items():
            if not os.path.exists(path):
                continue
            img = Image.open(path).convert("RGBA")
            if name == "Player":
                self.player_placeholder_raw = self.tint_image(img, "#ffffff")
            else:
                ui_img = img.resize((24, 24), Image.Resampling.LANCZOS)
                self.icons_ui[f"{name}_dark"]  = ImageTk.PhotoImage(self.tint_image(ui_img, "#555555"))
                self.icons_ui[f"{name}_light"] = ImageTk.PhotoImage(self.tint_image(ui_img, "#ffffff"))
                self.icons_ui[f"{name}_small"] = ImageTk.PhotoImage(self.tint_image(img.resize((16, 16)), "#ffffff"))

    def tint_image(self, image, color):
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        src = image.split()
        return Image.merge("RGBA", (
            src[0].point(lambda i: r),
            src[1].point(lambda i: g),
            src[2].point(lambda i: b),
            src[3],
        ))

    def setup_ui(self):
        self.toolbar = tk.Frame(self.root, bg="#1e1e1e", height=50)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        btn_s = {"bg": "#1e1e1e", "fg": "#eee", "relief": tk.FLAT, "font": ("Segoe UI", 9)}
        tk.Button(self.toolbar, text="PROJECT",     command=self.new_project_dialog, **btn_s).pack(side=tk.LEFT, padx=10)
        tk.Button(self.toolbar, text="OPEN",        command=self.open_project,       **btn_s).pack(side=tk.LEFT, padx=10)
        tk.Button(self.toolbar, text="SAVE",        command=self.save_project,       **btn_s).pack(side=tk.LEFT, padx=10)
        tk.Button(self.toolbar, text="ANIMATORATOR", command=self.open_animatorator,
                  bg="#7B2FBE", fg="white", relief=tk.FLAT, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=10)
        tk.Button(self.toolbar, text="SCRIPTS", command=self.open_scripts,
                  bg="#2ea043", fg="white", relief=tk.FLAT, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=10)
        tk.Button(self.toolbar, text="DIALOGI", command=self.open_dialogs,
                  bg="#e67e22", fg="white", relief=tk.FLAT, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=10)
        self.btn_logs = tk.Button(self.toolbar, text="LOGS", command=self.toggle_logs, **btn_s)
        self.btn_logs.pack(side=tk.LEFT, padx=10)
        self.btn_play = tk.Button(self.toolbar, text="► PLAY MODE", command=self.toggle_play,
                                  bg="#007acc", fg="white", relief=tk.FLAT,
                                  font=("Segoe UI", 9, "bold"), padx=25)
        self.btn_play.pack(side=tk.RIGHT, padx=10, pady=8)

        self.main_pane = tk.PanedWindow(self.root, orient=tk.VERTICAL, bg="#121212", sashwidth=6)
        self.main_pane.pack(fill=tk.BOTH, expand=True)
        self.workspace_frame = tk.Frame(self.main_pane, bg="#121212")
        self.main_pane.add(self.workspace_frame, stretch="always")

        self.tool_frame = tk.Frame(self.workspace_frame, bg="#1e1e1e", width=80)
        self.tool_frame.pack(side=tk.LEFT, fill=tk.Y, padx=1)
        self.tool_frame.pack_propagate(False)
        self.tool_btns = {}
        for m in ["Select", "Walkable", "Hotpoint"]:
            btn = tk.Button(self.tool_frame, image=self.icons_ui.get(f"{m}_dark"),
                            text=m, compound=tk.BOTTOM,
                            bg="#1e1e1e", fg="#555", relief=tk.FLAT,
                            font=("Segoe UI", 7),
                            command=lambda mode=m: self.set_mode(mode))
            btn.pack(pady=(10, 0), padx=5)
            self.tool_btns[m] = btn

        self.sidebar = tk.Frame(self.workspace_frame, bg="#1e1e1e", width=350)
        self.sidebar.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Button(self.sidebar, text="CONFIGURE PLAYER", command=self.open_player_settings,
                  bg="#007acc", fg="white", relief=tk.FLAT).pack(fill=tk.X, padx=10, pady=5)
        tk.Label(self.sidebar, text="SCENY", bg="#1e1e1e", fg="#888",
                 font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=10, pady=(4, 0))
        self.room_listbox = tk.Listbox(self.sidebar, bg="#121212", fg="#ddd",
                                       borderwidth=0, height=5, exportselection=False)
        self.room_listbox.pack(fill=tk.X, padx=10, pady=2)
        self.room_listbox.bind("<<ListboxSelect>>", self.on_room_selected)
        self.room_listbox.bind("<Double-1>", lambda e: self.rename_room())
        scene_row = tk.Frame(self.sidebar, bg="#1e1e1e"); scene_row.pack(fill=tk.X, padx=10)
        tk.Button(scene_row, text="+ SCENA", command=self.add_room,
                  bg="#333", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(scene_row, text="✏", command=self.rename_room,
                  bg="#333", fg="#aaa", relief=tk.FLAT, width=3).pack(side=tk.LEFT, padx=(2, 0))
        tk.Label(self.sidebar, text="OBIEKTY", bg="#1e1e1e", fg="#888",
                 font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=10, pady=(6, 0))
        self.obj_tree = ttk.Treeview(self.sidebar, show="tree", height=10)
        self.obj_tree.pack(fill=tk.X, padx=10, pady=2)
        self.obj_tree.bind("<<TreeviewSelect>>", self.on_obj_tree_select)
        self.obj_tree.bind("<Double-1>",          self.on_obj_tree_double_click)
        self.obj_tree.bind("<Button-3>",          self.on_obj_tree_right_click)
        tk.Button(self.sidebar, text="🗑 DELETE SELECTED", command=self.delete_selected,
                  bg="#8b0000", fg="white", relief=tk.FLAT,
                  font=("Segoe UI", 8, "bold")).pack(fill=tk.X, padx=10, pady=5)
        self.prop_container = tk.Frame(self.sidebar, bg="#1e1e1e")
        self.prop_container.pack(fill=tk.BOTH, expand=True, padx=10)
        self.setup_properties_ui()

        self.cv_area = tk.Frame(self.workspace_frame, bg="#121212")
        self.cv_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(self.cv_area, bg="#000", highlightthickness=0)
        self.canvas.pack(expand=True)

        self.con_frame = tk.Frame(self.main_pane, bg="#1e1e1e", height=100)
        self.log_text = tk.Text(self.con_frame, bg="#000", fg="#00ff00",
                                font=("Consolas", 9), state=tk.DISABLED, borderwidth=0)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_properties_ui(self):
        self.room_props_f = tk.Frame(self.prop_container, bg="#1e1e1e")
        tk.Button(self.room_props_f, text="SET BACKGROUND PNG", command=self.select_background,
                  bg="#007acc", fg="white", relief=tk.FLAT).pack(fill=tk.X, pady=5)
        self.room_props_f.pack(fill=tk.X)
        self.hp_props_f = tk.Frame(self.prop_container, bg="#1e1e1e")
        tk.Button(self.hp_props_f, text="EDIT HOTPOINT SETTINGS ⚙",
                  command=lambda: self.open_hp_settings(None),
                  bg="#333", fg="white", relief=tk.FLAT, pady=10).pack(fill=tk.X)

    # ─────────────────────────────────────────────
    #  HELPERS
    # ─────────────────────────────────────────────

    def _as_hp(self, raw):
        return Hotpoint(**raw) if isinstance(raw, dict) else raw

    def _wa_pts(self, raw):
        return raw['points'] if isinstance(raw, dict) else raw.points

    _EDGE = 9  # px in game coords

    def _hp_edge_at(self, hp, x, y):
        E = self._EDGE
        in_y = hp.y - E <= y <= hp.y + hp.h + E
        in_x = hp.x - E <= x <= hp.x + hp.w + E
        if in_y and hp.x + hp.w - E <= x <= hp.x + hp.w + E:
            return "resize_right"
        if in_y and hp.x - E <= x <= hp.x + E:
            return "resize_left"
        if in_x and hp.y + hp.h - E <= y <= hp.y + hp.h + E:
            return "resize_bottom"
        if in_x and hp.y - E <= y <= hp.y + E:
            return "resize_top"
        return None

    # ─────────────────────────────────────────────
    #  SPRITE LIBRARY
    # ─────────────────────────────────────────────

    def open_sprite_library(self):
        if not self.project:
            self._toast("Najpierw stwórz lub otwórz projekt.", "warn")
            return
        d = tk.Toplevel(self.root)
        d.title("Sprite Library"); d.geometry("960x660"); d.configure(bg="#121212")
        d.transient(self.root)

        top_bar = tk.Frame(d, bg="#1e1e1e"); top_bar.pack(fill=tk.X, padx=6, pady=6)
        tk.Button(top_bar, text="+ ADD SPRITES FROM DISK",
                  command=lambda: self._lib_add_sprites(refresh_grid),
                  bg="#007acc", fg="white", relief=tk.FLAT, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4)

        main_f = tk.Frame(d, bg="#121212"); main_f.pack(fill=tk.BOTH, expand=True)

        left_f = tk.Frame(main_f, bg="#121212"); left_f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        grid_cv = tk.Canvas(left_f, bg="#121212", highlightthickness=0)
        vscr = tk.Scrollbar(left_f, orient="vertical", command=grid_cv.yview)
        grid_cv.configure(yscrollcommand=vscr.set)
        vscr.pack(side=tk.RIGHT, fill=tk.Y); grid_cv.pack(fill=tk.BOTH, expand=True)
        grid_frame = tk.Frame(grid_cv, bg="#121212")
        grid_cv.create_window((0, 0), window=grid_frame, anchor="nw")
        grid_frame.bind("<Configure>", lambda e: grid_cv.configure(scrollregion=grid_cv.bbox("all")))
        grid_cv.bind("<MouseWheel>", lambda e: grid_cv.yview_scroll(int(-1*(e.delta/120)), "units"))

        tk.Frame(main_f, bg="#333", width=2).pack(side=tk.LEFT, fill=tk.Y)

        right_f = tk.Frame(main_f, bg="#1e1e1e", width=290)
        right_f.pack(side=tk.RIGHT, fill=tk.Y, padx=6, pady=6)
        right_f.pack_propagate(False)

        sel = {"sid": None}
        picked = {"color": None}
        eyedropper_on = {"v": False}
        preview_ref = {"img": None}

        def hlbl(t):
            tk.Label(right_f, text=t, bg="#1e1e1e", fg="#C4A35A",
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=8, pady=(8, 0))

        hlbl("NAZWA SPRITE'A")
        name_row = tk.Frame(right_f, bg="#1e1e1e"); name_row.pack(fill=tk.X, padx=8, pady=2)
        name_entry = tk.Entry(name_row, bg="#121212", fg="white", insertbackground="white", relief=tk.FLAT)
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(name_row, text="ZAPISZ", command=lambda: save_name(),
                  bg="#555", fg="white", relief=tk.FLAT, font=("Segoe UI", 7)).pack(side=tk.RIGHT, padx=2)

        preview_cv = tk.Canvas(right_f, width=250, height=210, bg="#2a2a2a",
                               highlightthickness=1, highlightbackground="#444", cursor="crosshair")
        preview_cv.pack(padx=8, pady=6)

        hlbl("USUWANIE TŁA")
        color_row = tk.Frame(right_f, bg="#1e1e1e"); color_row.pack(fill=tk.X, padx=8, pady=2)
        color_swatch = tk.Label(color_row, text="   ", bg="#2a2a2a", relief=tk.SOLID, bd=1, width=3)
        color_swatch.pack(side=tk.LEFT)
        color_lbl = tk.Label(color_row, text="— brak koloru —", bg="#1e1e1e", fg="#888", font=("Segoe UI", 8))
        color_lbl.pack(side=tk.LEFT, padx=6)

        btn_ey = tk.Button(right_f, text="💧 EYEDROPPER  (kliknij podgląd)",
                           command=lambda: toggle_ey(), bg="#333", fg="white", relief=tk.FLAT, anchor="w")
        btn_ey.pack(fill=tk.X, padx=8, pady=2)

        tol_row = tk.Frame(right_f, bg="#1e1e1e"); tol_row.pack(fill=tk.X, padx=8)
        tk.Label(tol_row, text="Tolerancja:", bg="#1e1e1e", fg="#aaa", font=("Segoe UI", 8)).pack(side=tk.LEFT)
        tol_val_lbl = tk.Label(tol_row, text="30", bg="#1e1e1e", fg="white",
                               font=("Segoe UI", 8, "bold"), width=3)
        tol_val_lbl.pack(side=tk.RIGHT)
        tol_v = tk.IntVar(value=30)
        tk.Scale(right_f, variable=tol_v, from_=0, to=100, orient=tk.HORIZONTAL,
                 bg="#1e1e1e", fg="white", showvalue=False,
                 command=lambda v: tol_val_lbl.config(text=v)).pack(fill=tk.X, padx=8)

        tk.Button(right_f, text="REMOVE BG", command=lambda: do_remove_bg(),
                  bg="#C4A35A", fg="black", relief=tk.FLAT, font=("Segoe UI", 9, "bold")).pack(fill=tk.X, padx=8, pady=4)

        hlbl("NARZĘDZIA PNG")
        tk.Button(right_f, text="TRIM  (usuń puste piksele z brzegów)", command=lambda: do_trim(),
                  bg="#333", fg="white", relief=tk.FLAT, anchor="w").pack(fill=tk.X, padx=8, pady=2)
        tk.Button(right_f, text="USUŃ Z BIBLIOTEKI", command=lambda: do_delete(),
                  bg="#8b0000", fg="white", relief=tk.FLAT).pack(fill=tk.X, padx=8, pady=(12, 2))

        def toggle_ey():
            eyedropper_on["v"] = not eyedropper_on["v"]
            if eyedropper_on["v"]:
                btn_ey.config(bg="#007acc", text="💧 EYEDROPPER  [AKTYWNY — kliknij podgląd]")
            else:
                btn_ey.config(bg="#333", text="💧 EYEDROPPER  (kliknij podgląd)")

        def on_preview_click(evt):
            if not eyedropper_on["v"]:
                return
            sid = sel["sid"]
            if not sid or sid not in self.project.sprites:
                return
            path = self.project.sprites[sid]["path"]
            if not path or not os.path.exists(path):
                return
            img = Image.open(path).convert("RGBA")
            pw, ph = 250, 210
            scale = min(pw / img.width, ph / img.height)
            ox = (pw - img.width * scale) / 2
            oy = (ph - img.height * scale) / 2
            ix = int((evt.x - ox) / scale)
            iy = int((evt.y - oy) / scale)
            if 0 <= ix < img.width and 0 <= iy < img.height:
                r, g, b, _ = img.getpixel((ix, iy))
                picked["color"] = (r, g, b)
                hx = f"#{r:02x}{g:02x}{b:02x}"
                color_swatch.config(bg=hx)
                color_lbl.config(text=hx, fg="white")
                self.log(f"Eyedropper: {hx} @ ({ix},{iy})")
            eyedropper_on["v"] = False
            btn_ey.config(bg="#333", text="💧 EYEDROPPER  (kliknij podgląd)")

        preview_cv.bind("<Button-1>", on_preview_click)

        def refresh_detail(sid):
            name_entry.delete(0, tk.END)
            preview_cv.delete("all")
            preview_ref["img"] = None
            if not sid or sid not in self.project.sprites:
                return
            sprite = self.project.sprites[sid]
            name_entry.insert(0, sprite["name"])
            if sprite["path"] and os.path.exists(sprite["path"]):
                try:
                    img = Image.open(sprite["path"]).convert("RGBA")
                    pw, ph = 250, 210
                    scale = min(pw / img.width, ph / img.height)
                    nw, nh = int(img.width * scale), int(img.height * scale)
                    bg = Image.new("RGBA", (pw, ph), (42, 42, 42, 255))
                    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
                    bg.paste(resized, ((pw - nw) // 2, (ph - nh) // 2), resized)
                    preview_ref["img"] = ImageTk.PhotoImage(bg)
                    preview_cv.create_image(0, 0, image=preview_ref["img"], anchor="nw")
                except Exception as e:
                    preview_cv.create_text(125, 105, text=f"Błąd: {e}", fill="red", width=230)

        def select_sprite(sid):
            sel["sid"] = sid
            picked["color"] = None
            color_swatch.config(bg="#2a2a2a")
            color_lbl.config(text="— brak koloru —", fg="#888")
            refresh_detail(sid)

        def save_name():
            if sel["sid"] and sel["sid"] in self.project.sprites:
                self.project.sprites[sel["sid"]]["name"] = name_entry.get()
                refresh_grid()

        def do_trim():
            sid = sel["sid"]
            if not sid:
                self._toast("Wybierz sprite z listy.", "warn")
                return
            self._sprite_trim(self.project.sprites[sid]["path"])
            refresh_detail(sid)
            refresh_grid()

        def do_remove_bg():
            sid = sel["sid"]
            if not sid:
                self._toast("Wybierz sprite z listy.", "warn")
                return
            if not picked["color"]:
                self._toast("Użyj eyedroppera, żeby pobrać kolor tła.", "warn")
                return
            path = self.project.sprites[sid]["path"]
            if messagebox.askyesno("Uwaga", f"Operacja nadpisze plik:\n{os.path.basename(path)}\n\nKontynuować?"):
                self._sprite_remove_bg(path, picked["color"], tol_v.get())
                refresh_detail(sid)
                refresh_grid()

        def do_delete():
            sid = sel["sid"]
            if sid and sid in self.project.sprites:
                del self.project.sprites[sid]
                sel["sid"] = None
                refresh_detail(None)
                refresh_grid()

        self._lib_thumb_refs = {}

        def refresh_grid():
            for w in grid_frame.winfo_children():
                w.destroy()
            self._lib_thumb_refs.clear()
            COLS = 4
            for i, (sid, sprite) in enumerate(self.project.sprites.items()):
                col, row_n = i % COLS, i // COLS
                cell = tk.Frame(grid_frame, bg="#1e1e1e", padx=2, pady=2, cursor="hand2")
                cell.grid(row=row_n, column=col, padx=5, pady=5)
                if sprite["path"] and os.path.exists(sprite["path"]):
                    try:
                        img = Image.open(sprite["path"]).convert("RGBA")
                        bg_t = Image.new("RGBA", (84, 84), (40, 40, 40, 255))
                        thumb = img.copy()
                        thumb.thumbnail((80, 80), Image.Resampling.LANCZOS)
                        bg_t.paste(thumb, ((84 - thumb.width) // 2, (84 - thumb.height) // 2), thumb)
                        ref = ImageTk.PhotoImage(bg_t)
                        self._lib_thumb_refs[sid] = ref
                        tk.Button(cell, image=ref, bg="#252526", activebackground="#007acc",
                                  relief=tk.FLAT, bd=0, command=lambda s=sid: select_sprite(s)).pack()
                    except Exception:
                        tk.Label(cell, text="ERR", bg="#500", fg="red", width=8, height=4).pack()
                else:
                    tk.Label(cell, text="?", bg="#333", fg="#888", width=8, height=4).pack()
                tk.Label(cell, text=sprite["name"][:14], bg="#1e1e1e", fg="#ccc",
                         font=("Segoe UI", 7), wraplength=90).pack()
            grid_cv.update_idletasks()
            grid_cv.configure(scrollregion=grid_cv.bbox("all"))

        refresh_grid()

    def _lib_add_sprites(self, callback):
        paths = filedialog.askopenfilenames(
            title="Dodaj sprite'y",
            filetypes=[("PNG images", "*.png"), ("Wszystkie pliki", "*.*")])
        for path in paths:
            base = os.path.splitext(os.path.basename(path))[0]
            sid = f"spr_{base}_{int(time.time()*1000)}"
            self.project.sprites[sid] = {"name": base, "path": path}
            self.log(f"Sprite dodany: {base}")
        if paths and callback:
            callback()

    def _sprite_trim(self, path):
        try:
            img = Image.open(path).convert("RGBA")
            bbox = img.split()[3].getbbox()
            if bbox:
                img.crop(bbox).save(path)
                self.log(f"TRIM OK: {os.path.basename(path)}")
            else:
                self.log(f"TRIM: brak przezroczystych krawędzi w {os.path.basename(path)}")
        except Exception as e:
            self.log(f"TRIM błąd: {e}")

    def _sprite_remove_bg(self, path, color, tolerance):
        try:
            img = Image.open(path).convert("RGBA")
            data = np.array(img)
            r0, g0, b0 = color
            diff = data[:, :, :3].astype(float) - np.array([r0, g0, b0], float)
            dist = np.sqrt((diff ** 2).sum(axis=2))
            data[dist <= (tolerance * 2.55), 3] = 0
            Image.fromarray(data).save(path)
            self.log(f"Remove BG OK: {os.path.basename(path)}, tol={tolerance}")
        except Exception as e:
            self.log(f"Remove BG błąd: {e}")

    # ─────────────────────────────────────────────
    #  ANIMATORATOR
    # ─────────────────────────────────────────────

    def open_animatorator(self):
        if not self.project:
            self._toast("Najpierw stwórz lub otwórz projekt.", "warn")
            return

        d = tk.Toplevel(self.root)
        d.title("ANIMATORATOR — Wykrywanie Klatek Animacji")
        d.geometry("1120x700"); d.configure(bg="#0d0d0d")
        d.transient(self.root)

        st = {"img": None, "path": "", "frames": [], "uniform": [],
              "fw": 0, "fh": 0, "tick": 0, "playing": False, "job": None,
              "pv_scale": 1.0, "pv_ox": 0, "pv_oy": 0, "current_pil": None}
        lib_sel  = {"aid": None}
        self._anim_refs = {}

        def make_checker(w, h, sz=16):
            r = np.arange(h)[:, None]; c = np.arange(w)[None, :]
            v = np.where(((r // sz) + (c // sz)) % 2 == 0, 52, 38).astype(np.uint8)
            return Image.fromarray(np.stack([v, v, v, np.full((h, w), 255, np.uint8)], 2))

        checker_prev = make_checker(360, 300)

        top_f = tk.Frame(d, bg="#1a1a1a"); top_f.pack(fill=tk.X, padx=8, pady=5)
        status_v = tk.StringVar(value="Załaduj plik PNG ze sprite sheet, potem kliknij WYKRYJ KLATKI.")
        tk.Label(top_f, textvariable=status_v, bg="#1a1a1a", fg="#aaa",
                 font=("Segoe UI", 9), anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        mid_f = tk.Frame(d, bg="#0d0d0d"); mid_f.pack(fill=tk.BOTH, expand=True)

        lp = tk.Frame(mid_f, bg="#161616", width=420)
        lp.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6); lp.pack_propagate(False)

        def hlbl(parent, txt):
            tk.Label(parent, text=txt, bg=parent.cget("bg"), fg="#9B59B6",
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=8, pady=(8, 2))

        hlbl(lp, "PODGLĄD ANIMACJI")
        pv_cv = tk.Canvas(lp, width=360, height=300, bg="#262626",
                          highlightthickness=1, highlightbackground="#333")
        pv_cv.pack(padx=8, pady=4)
        pv_img_id = pv_cv.create_image(0, 0, anchor="nw")

        fps_f = tk.Frame(lp, bg="#161616"); fps_f.pack(fill=tk.X, padx=8, pady=(0, 2))
        tk.Label(fps_f, text="FPS:", bg="#161616", fg="#aaa", font=("Segoe UI", 8)).pack(side=tk.LEFT)
        fps_lbl = tk.Label(fps_f, text="8", bg="#161616", fg="white",
                           font=("Segoe UI", 8, "bold"), width=3)
        fps_lbl.pack(side=tk.RIGHT)
        fps_v = tk.IntVar(value=8)
        tk.Scale(fps_f, variable=fps_v, from_=1, to=30, orient=tk.HORIZONTAL,
                 bg="#161616", fg="white", showvalue=False, length=280,
                 command=lambda v: fps_lbl.config(text=v)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        btn_play = tk.Button(lp, text="▶  PLAY PREVIEW", command=lambda: toggle_play(),
                             bg="#007acc", fg="white", relief=tk.FLAT, font=("Segoe UI", 9, "bold"))
        btn_play.pack(fill=tk.X, padx=8, pady=4)

        hlbl(lp, "ZAPISZ DO BIBLIOTEKI ANIMATORATORA")
        sf = tk.Frame(lp, bg="#161616"); sf.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(sf, text="Nazwa:", bg="#161616", fg="#aaa", font=("Segoe UI", 8)).pack(side=tk.LEFT)
        name_e = tk.Entry(sf, bg="#0d0d0d", fg="white", insertbackground="white", relief=tk.FLAT)
        name_e.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        tk.Button(lp, text="💾  ZAPISZ ANIMACJĘ", command=lambda: save_anim(),
                  bg="#7B2FBE", fg="white", relief=tk.FLAT,
                  font=("Segoe UI", 9, "bold")).pack(fill=tk.X, padx=8, pady=6)

        tk.Frame(mid_f, bg="#2a2a2a", width=2).pack(side=tk.LEFT, fill=tk.Y)

        rp = tk.Frame(mid_f, bg="#0d0d0d")
        rp.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)

        def rhlbl(t):
            tk.Label(rp, text=t, bg="#0d0d0d", fg="#9B59B6",
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=4, pady=(6, 2))

        rhlbl("ŹRÓDŁO")
        src_bar = tk.Frame(rp, bg="#0d0d0d"); src_bar.pack(fill=tk.X, padx=4, pady=2)
        tk.Button(src_bar, text="📂  ZAŁADUJ SPRITE SHEET", command=lambda: load_sheet(),
                  bg="#C4A35A", fg="black", relief=tk.FLAT,
                  font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=2)
        tk.Button(src_bar, text="✂  AUTO-TRIM  +  WYKRYJ KLATKI", command=lambda: do_detect(),
                  bg="#333", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=6)

        rhlbl("USUWANIE TŁA  (flood fill od krawędzi — nie nadpisuje pliku)")
        bg_info_row = tk.Frame(rp, bg="#0d0d0d"); bg_info_row.pack(fill=tk.X, padx=4, pady=(0, 2))
        tk.Label(bg_info_row, text="Wykryty kolor tła:", bg="#0d0d0d", fg="#aaa",
                 font=("Segoe UI", 8)).pack(side=tk.LEFT)
        ey_swatch = tk.Label(bg_info_row, text="   ", bg="#262626",
                             relief=tk.SOLID, bd=1, width=3)
        ey_swatch.pack(side=tk.LEFT, padx=6)
        ey_lbl = tk.Label(bg_info_row, text="auto z narożników", bg="#0d0d0d",
                          fg="#666", font=("Segoe UI", 8))
        ey_lbl.pack(side=tk.LEFT)

        tol_row = tk.Frame(rp, bg="#0d0d0d"); tol_row.pack(fill=tk.X, padx=4, pady=1)
        tk.Label(tol_row, text="Tolerancja:", bg="#0d0d0d", fg="#aaa",
                 font=("Segoe UI", 8)).pack(side=tk.LEFT)
        tol_val_lbl = tk.Label(tol_row, text="25", bg="#0d0d0d", fg="white",
                               font=("Segoe UI", 8, "bold"), width=3)
        tol_val_lbl.pack(side=tk.RIGHT)
        tol_v = tk.IntVar(value=25)
        tk.Scale(rp, variable=tol_v, from_=0, to=100, orient=tk.HORIZONTAL,
                 bg="#0d0d0d", fg="white", showvalue=False,
                 command=lambda v: tol_val_lbl.config(text=v)).pack(fill=tk.X, padx=4)
        tk.Button(rp, text="🗑  REMOVE BG  (flood fill od krawędzi, ponownie wykryj klatki)",
                  command=lambda: do_remove_bg_anim(),
                  bg="#8b3a00", fg="white", relief=tk.FLAT,
                  font=("Segoe UI", 8, "bold")).pack(fill=tk.X, padx=4, pady=(2, 6))

        rhlbl("WYKRYTE KLATKI  (identyczne kontenery, wyrównane do dołu — bez drgań)")
        fr_outer = tk.Frame(rp, bg="#0d0d0d", height=170)
        fr_outer.pack(fill=tk.X, padx=4); fr_outer.pack_propagate(False)
        fr_cv = tk.Canvas(fr_outer, bg="#0d0d0d", highlightthickness=0)
        fr_scr = tk.Scrollbar(fr_outer, orient="horizontal", command=fr_cv.xview)
        fr_cv.configure(xscrollcommand=fr_scr.set)
        fr_scr.pack(side=tk.BOTTOM, fill=tk.X); fr_cv.pack(fill=tk.BOTH, expand=True)
        fr_inner = tk.Frame(fr_cv, bg="#0d0d0d")
        fr_cv.create_window((0, 0), window=fr_inner, anchor="nw")
        fr_inner.bind("<Configure>", lambda e: fr_cv.configure(scrollregion=fr_cv.bbox("all")))
        fr_cv.bind("<MouseWheel>", lambda e: fr_cv.xview_scroll(int(-1*(e.delta/120)), "units"))

        rhlbl("BIBLIOTEKA ANIMATORATORA")
        lib_bar2 = tk.Frame(rp, bg="#0d0d0d"); lib_bar2.pack(fill=tk.X, padx=4, pady=(0, 2))
        tk.Button(lib_bar2, text="🗑  USUŃ ZAZNACZONĄ", command=lambda: del_from_lib(),
                  bg="#8b0000", fg="white", relief=tk.FLAT,
                  font=("Segoe UI", 8)).pack(side=tk.LEFT)
        lib_outer = tk.Frame(rp, bg="#0d0d0d", height=140)
        lib_outer.pack(fill=tk.X, padx=4, pady=2); lib_outer.pack_propagate(False)
        lib_cv = tk.Canvas(lib_outer, bg="#121212", highlightthickness=0)
        lib_scr = tk.Scrollbar(lib_outer, orient="horizontal", command=lib_cv.xview)
        lib_cv.configure(xscrollcommand=lib_scr.set)
        lib_scr.pack(side=tk.BOTTOM, fill=tk.X); lib_cv.pack(fill=tk.BOTH, expand=True)
        lib_inner = tk.Frame(lib_cv, bg="#121212")
        lib_cv.create_window((0, 0), window=lib_inner, anchor="nw")
        lib_inner.bind("<Configure>", lambda e: lib_cv.configure(scrollregion=lib_cv.bbox("all")))
        lib_cv.bind("<MouseWheel>", lambda e: lib_cv.xview_scroll(int(-1*(e.delta/120)), "units"))

        def load_sheet():
            p = filedialog.askopenfilename(
                title="Załaduj sprite sheet",
                filetypes=[("PNG images", "*.png"), ("Wszystkie pliki", "*.*")])
            if not p:
                return
            try:
                img = Image.open(p).convert("RGBA")
                st["img"] = img; st["path"] = p
                base = os.path.splitext(os.path.basename(p))[0]
                name_e.delete(0, tk.END); name_e.insert(0, base)
                status_v.set(f"Załadowano: {os.path.basename(p)}  ({img.width}×{img.height}px)")
                do_detect()
            except Exception as ex:
                self._toast(f"Nie można otworzyć pliku: {ex}", "error")

        def do_detect():
            if st["img"] is None:
                self._toast("Najpierw załaduj sprite sheet.", "warn")
                return
            img = st["img"]
            bbox = img.split()[3].getbbox()
            if bbox:
                img = img.crop(bbox); st["img"] = img
            raw = _detect_frames(img)
            if not raw:
                status_v.set("⚠  Nie wykryto klatek — plik musi mieć kanał alfa (PNG z przezroczystością).")
                return
            fw = max(f[2] for f in raw)
            fh = max(f[3] for f in raw)
            st["frames"] = raw; st["fw"] = fw; st["fh"] = fh
            uniform = []
            for (x, y, w, h) in raw:
                crop = img.crop((x, y, x + w, y + h))
                canvas = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
                canvas.paste(crop, ((fw - w) // 2, fh - h), crop)
                uniform.append(canvas)
            st["uniform"] = uniform; st["tick"] = 0
            status_v.set(f"✓  Wykryto {len(raw)} klatek  |  Kontener: {fw}×{fh}px  |  Gotowe do zapisu")
            refresh_frames_grid()
            show_frame(0)

        def _detect_frames(img):
            alpha_arr = np.array(img.split()[3])
            col_sums = alpha_arr.sum(axis=0)
            is_gap = (col_sums == 0)
            W = len(is_gap)
            MIN_GAP = 3
            gap_f = is_gap.copy()
            x = 0
            while x < W:
                if is_gap[x]:
                    rs = x
                    while x < W and is_gap[x]:
                        x += 1
                    if (x - rs) < MIN_GAP:
                        gap_f[rs:x] = False
                else:
                    x += 1
            frames = []; in_f = False; sx = 0
            for x in range(W):
                if not gap_f[x] and not in_f:
                    in_f = True; sx = x
                elif gap_f[x] and in_f:
                    in_f = False; ew = x - sx
                    slab = alpha_arr[:, sx:x]
                    rows = np.where(slab.sum(axis=1) > 0)[0]
                    if len(rows) and ew >= 4:
                        frames.append((sx, int(rows[0]), ew, int(rows[-1]) - int(rows[0]) + 1))
            if in_f:
                ew = W - sx; slab = alpha_arr[:, sx:]
                rows = np.where(slab.sum(axis=1) > 0)[0]
                if len(rows) and ew >= 4:
                    frames.append((sx, int(rows[0]), ew, int(rows[-1]) - int(rows[0]) + 1))
            return frames

        def show_frame(idx):
            uniform = st["uniform"]
            if not uniform:
                return
            idx = idx % len(uniform)
            frame = uniform[idx]
            pw, ph = 360, 300
            scale = min(pw / max(frame.width, 1), ph / max(frame.height, 1))
            scale = min(scale, 4.0)
            nw = max(1, int(frame.width * scale))
            nh = max(1, int(frame.height * scale))
            ox = (pw - nw) // 2; oy = ph - nh - 6
            st["pv_scale"] = scale; st["pv_ox"] = ox; st["pv_oy"] = oy
            st["current_pil"] = frame
            bg = checker_prev.copy()
            interp = Image.Resampling.NEAREST if scale >= 2.0 else Image.Resampling.LANCZOS
            resized = frame.resize((nw, nh), interp)
            bg.paste(resized, (ox, max(0, oy)), resized)
            ref = ImageTk.PhotoImage(bg); self._anim_refs["pv"] = ref
            pv_cv.itemconfig(pv_img_id, image=ref)

        def animate():
            if not st["playing"] or not d.winfo_exists():
                return
            n = len(st["uniform"])
            if not n:
                return
            st["tick"] = (st["tick"] + 1) % n
            show_frame(st["tick"])
            st["job"] = d.after(max(33, int(1000 / fps_v.get())), animate)

        def toggle_play():
            if not st["uniform"]:
                self._toast("Wykryj klatki przed odtworzeniem.", "warn")
                return
            st["playing"] = not st["playing"]
            if st["playing"]:
                btn_play.config(text="⏹  STOP", bg="#8b0000")
                animate()
            else:
                btn_play.config(text="▶  PLAY PREVIEW", bg="#007acc")
                if st["job"]:
                    d.after_cancel(st["job"]); st["job"] = None

        def refresh_frames_grid():
            for w in fr_inner.winfo_children():
                w.destroy()
            checker_t = make_checker(80, 80, 8)
            for i, frame in enumerate(st["uniform"]):
                cell = tk.Frame(fr_inner, bg="#1a1a1a"); cell.pack(side=tk.LEFT, padx=3, pady=3)
                bg_t = checker_t.copy()
                scale = min(72 / max(frame.width, 1), 72 / max(frame.height, 1))
                nw = max(1, int(frame.width * scale))
                nh = max(1, int(frame.height * scale))
                thumb = frame.resize((nw, nh), Image.Resampling.LANCZOS)
                bg_t.paste(thumb, ((80 - nw) // 2, 80 - nh), thumb)
                ref = ImageTk.PhotoImage(bg_t); self._anim_refs[f"t{i}"] = ref
                lbl_img = tk.Label(cell, image=ref, bg="#252526", cursor="hand2")
                lbl_img.pack(); lbl_img.bind("<Button-1>", lambda e, fi=i: show_frame(fi))
                tk.Label(cell, text=f"#{i+1}", bg="#1a1a1a", fg="#555",
                         font=("Segoe UI", 7)).pack()
            fr_cv.update_idletasks(); fr_cv.configure(scrollregion=fr_cv.bbox("all"))

        def save_anim():
            if not st["uniform"]:
                self._toast("Wykryj klatki przed zapisem.", "warn")
                return
            name = name_e.get().strip() or "animacja"
            safe = name.replace(" ", "_")
            fw, fh, n, fps = st["fw"], st["fh"], len(st["uniform"]), fps_v.get()
            sheet = Image.new("RGBA", (fw * n, fh), (0, 0, 0, 0))
            for i, f in enumerate(st["uniform"]):
                sheet.paste(f, (i * fw, 0), f)
            base_dir = os.path.dirname(st["path"]) if st["path"] else os.path.expanduser("~")
            out_path = os.path.join(base_dir, f"{safe}_anim.png")
            sheet.save(out_path)
            if not hasattr(self.project, "animations"):
                self.project.animations = {}
            aid = f"anim_{safe}_{int(time.time())}"
            self.project.animations[aid] = {
                "name": name, "sheet_path": out_path,
                "frames": n, "frame_w": fw, "frame_h": fh, "fps": fps,
            }
            self.log(f"ANIMATORATOR: '{name}' zapisana ({n} klatek, {fw}×{fh}px) → {out_path}")
            refresh_lib()
            self._toast(f"'{name}' zapisana — {n} kl. {fw}×{fh}px → CONFIGURE PLAYER → animations", "info")

        def do_remove_bg_anim():
            if st["img"] is None:
                self._toast("Najpierw załaduj sprite sheet.", "warn"); return
            from collections import deque
            data = np.array(st["img"].convert("RGBA"), dtype=np.uint8)
            h, w = data.shape[:2]
            # auto-detect bg color: median of corner 5×5 patches
            cs = max(1, min(5, h // 6, w // 6))
            samples = np.vstack([
                data[:cs,    :cs,    :3].reshape(-1, 3),
                data[:cs,    w-cs:,  :3].reshape(-1, 3),
                data[h-cs:,  :cs,    :3].reshape(-1, 3),
                data[h-cs:,  w-cs:,  :3].reshape(-1, 3),
            ])
            bg = np.median(samples, axis=0)
            hx = "#{:02x}{:02x}{:02x}".format(int(bg[0]), int(bg[1]), int(bg[2]))
            ey_swatch.config(bg=hx)
            ey_lbl.config(text=hx, fg="white")
            # flood fill from all 4 edges — only spreads through pixels similar to bg
            tol_sq = (tol_v.get() * 2.55) ** 2
            visited = np.zeros((h, w), dtype=bool)
            result  = data.copy()
            q = deque()
            def seed(y, x):
                if not visited[y, x]:
                    visited[y, x] = True
                    q.append((y, x))
            for x in range(w):
                seed(0, x); seed(h - 1, x)
            for y in range(1, h - 1):
                seed(y, 0); seed(y, w - 1)
            while q:
                y, x = q.popleft()
                px = data[y, x, :3].astype(np.float32)
                diff_sq = float(np.dot(px - bg, px - bg))
                if diff_sq <= tol_sq:
                    result[y, x, 3] = 0
                    for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                            visited[ny, nx] = True
                            q.append((ny, nx))
            st["img"] = Image.fromarray(result)
            removed = int((result[:, :, 3] == 0).sum())
            status_v.set(f"Remove BG: usunięto {removed} px flood-fill od krawędzi "
                         f"(tol={tol_v.get()}, kolor tła={hx}). Ponownie wykrywam klatki…")
            do_detect()

        def del_from_lib():
            if not lib_sel["aid"]:
                self._toast("Kliknij animację w bibliotece, żeby ją zaznaczyć.", "warn"); return
            if not hasattr(self.project, "animations"):
                return
            if lib_sel["aid"] in self.project.animations:
                del self.project.animations[lib_sel["aid"]]
                lib_sel["aid"] = None
                refresh_lib()

        def refresh_lib():
            for w in lib_inner.winfo_children():
                w.destroy()
            if not hasattr(self.project, "animations"):
                return
            checker_t = make_checker(84, 84, 10)
            for aid, anim in self.project.animations.items():
                cell = tk.Frame(lib_inner, bg="#1a1a1a", padx=3, pady=3, cursor="hand2")
                cell.pack(side=tk.LEFT, padx=4, pady=4)
                thumb_ref = None
                try:
                    sp = anim.get("sheet_path", "")
                    if sp and os.path.exists(sp):
                        img_s = Image.open(sp).convert("RGBA")
                        fw = max(1, anim.get("frame_w", img_s.width))
                        fh = max(1, anim.get("frame_h", img_s.height))
                        first = img_s.crop((0, 0, fw, fh))
                        bg_t = checker_t.copy()
                        first.thumbnail((78, 78), Image.Resampling.LANCZOS)
                        ox2 = (84 - first.width) // 2
                        oy2 = 84 - first.height - 2
                        bg_t.paste(first, (ox2, max(0, oy2)), first)
                        thumb_ref = ImageTk.PhotoImage(bg_t)
                        self._anim_refs[f"lib_{aid}"] = thumb_ref
                except Exception:
                    pass

                def make_sel(a=aid, c=cell):
                    def sel():
                        lib_sel["aid"] = a
                        for ch in lib_inner.winfo_children():
                            ch.config(bg="#1a1a1a")
                            for w2 in ch.winfo_children():
                                try: w2.config(bg="#1a1a1a")
                                except Exception: pass
                        c.config(bg="#3a1a5a")
                        for w2 in c.winfo_children():
                            try: w2.config(bg="#3a1a5a")
                            except Exception: pass
                    return sel

                if thumb_ref:
                    tk.Button(cell, image=thumb_ref, bg="#252526", activebackground="#7B2FBE",
                              relief=tk.FLAT, bd=0, command=make_sel()).pack()
                else:
                    tk.Button(cell, text="?", bg="#333", fg="#888", width=6, height=4,
                              relief=tk.FLAT, command=make_sel()).pack()
                tk.Label(cell, text=anim["name"][:13], bg="#1a1a1a", fg="#ccc",
                         font=("Segoe UI", 7), wraplength=88).pack()
                tk.Label(cell, text=f"{anim['frames']}kl · {anim['frame_w']}×{anim['frame_h']}",
                         bg="#1a1a1a", fg="#555", font=("Segoe UI", 6)).pack()
            lib_cv.update_idletasks()
            lib_cv.configure(scrollregion=lib_cv.bbox("all"))

        def on_close():
            st["playing"] = False
            if st["job"]:
                try: d.after_cancel(st["job"])
                except Exception: pass
            d.destroy()

        d.protocol("WM_DELETE_WINDOW", on_close)
        refresh_lib()

    # ─────────────────────────────────────────────
    #  SCRIPTS
    # ─────────────────────────────────────────────

    def open_scripts(self):
        if not self.project:
            self._toast("Najpierw stwórz lub otwórz projekt.", "warn")
            return
        if not hasattr(self.project, "scripts"):
            self.project.scripts = {}

        d = tk.Toplevel(self.root)
        d.title("Skrypty")
        d.geometry("920x640")
        d.configure(bg="#121212")
        d.transient(self.root)

        sel_id = {"v": None}

        # ── LEFT: lista skryptów ──────────────────
        left = tk.Frame(d, bg="#1a1a1a", width=280)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        tk.Button(left, text="+ NOWY SKRYPT", command=lambda: new_script(),
                  bg="#2ea043", fg="white", relief=tk.FLAT,
                  font=("Segoe UI", 9, "bold")).pack(fill=tk.X, padx=8, pady=(10, 2))

        PRESETS = {
            "Burza — START": {
                "name": "burza_start", "scope": "room", "trigger": "on_enter",
                "code": 'game_state["rain"] = {"intensity": 1.0, "color": "#7fb8e8", "lightning_prob": 0.03, "seed": 42}\nlog("Burza uruchomiona!")',
            },
            "Burza — STOP": {
                "name": "burza_stop", "scope": "room", "trigger": "manual",
                "code": 'game_state.pop("rain", None)\ngame_state.pop("_lt_tick", None)\nlog("Burza zatrzymana.")',
            },
        }

        def load_preset(key):
            p = PRESETS[key]
            name_e.delete(0, tk.END)
            name_e.insert(0, p["name"])
            code_t.delete("1.0", tk.END)
            code_t.insert("1.0", p["code"])
            set_scope(p["scope"])
            set_trigger(p["trigger"])
            sel_id["v"] = None

        preset_btn = tk.Menubutton(left, text="📋  PRESETS", bg="#7B2FBE", fg="white",
                                   relief=tk.FLAT, font=("Segoe UI", 9, "bold"),
                                   activebackground="#9B59B6", activeforeground="white")
        preset_btn.pack(fill=tk.X, padx=8, pady=(0, 6))
        preset_menu = tk.Menu(preset_btn, tearoff=0, bg="#1a1a1a", fg="white",
                              activebackground="#7B2FBE", activeforeground="white")
        for key in PRESETS:
            preset_menu.add_command(label=f"  {key}", command=lambda k=key: load_preset(k))
        preset_btn["menu"] = preset_menu

        lb = tk.Listbox(left, bg="#121212", fg="#ddd", borderwidth=0,
                        selectbackground="#1f6feb", font=("Segoe UI", 9),
                        exportselection=False, activestyle="none")
        lb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        tk.Frame(d, bg="#2a2a2a", width=2).pack(side=tk.LEFT, fill=tk.Y)

        # ── RIGHT: edytor ────────────────────────
        right = tk.Frame(d, bg="#0d0d0d")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def hlbl(text):
            tk.Label(right, text=text, bg="#0d0d0d", fg="#2ea043",
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(10, 2))

        hlbl("NAZWA")
        name_e = tk.Entry(right, bg="#1a1a1a", fg="white", insertbackground="white",
                          relief=tk.FLAT, font=("Segoe UI", 10))
        name_e.pack(fill=tk.X, padx=12, pady=2, ipady=4)

        hlbl("ZAKRES")
        scope_f = tk.Frame(right, bg="#0d0d0d")
        scope_f.pack(fill=tk.X, padx=12, pady=2)
        scope_v = tk.StringVar(value="room")
        room_badge = tk.Label(scope_f, text="", bg="#0d0d0d", fg="#888", font=("Segoe UI", 8))

        def set_scope(v):
            scope_v.set(v)
            btn_room.config(bg="#1f6feb" if v == "room" else "#252525", fg="white" if v == "room" else "#666")
            btn_glob.config(bg="#1f6feb" if v == "global" else "#252525", fg="white" if v == "global" else "#666")
            if v == "room" and self.current_room_id and self.current_room_id in self.project.rooms:
                room_badge.config(text="→ " + self.project.rooms[self.current_room_id]["name"])
                room_badge.pack(side=tk.LEFT, padx=8)
            else:
                room_badge.pack_forget()

        btn_room = tk.Button(scope_f, text="  ROOM  ", command=lambda: set_scope("room"),
                             bg="#1f6feb", fg="white", relief=tk.FLAT, font=("Segoe UI", 9, "bold"))
        btn_room.pack(side=tk.LEFT, padx=(0, 4))
        btn_glob = tk.Button(scope_f, text=" GLOBAL ", command=lambda: set_scope("global"),
                             bg="#252525", fg="#666", relief=tk.FLAT, font=("Segoe UI", 9, "bold"))
        btn_glob.pack(side=tk.LEFT)

        hlbl("KIEDY DZIAŁA")
        trig_f = tk.Frame(right, bg="#0d0d0d")
        trig_f.pack(fill=tk.X, padx=12, pady=2)
        trig_v = tk.StringVar(value="on_enter")

        def set_trigger(v):
            trig_v.set(v)
            for btn, val in [(btn_enter, "on_enter"), (btn_exit, "on_exit"), (btn_manual, "manual")]:
                btn.config(bg="#1f6feb" if v == val else "#252525",
                           fg="white" if v == val else "#666")

        btn_enter  = tk.Button(trig_f, text=" ON ENTER ", command=lambda: set_trigger("on_enter"),
                               bg="#1f6feb", fg="white", relief=tk.FLAT, font=("Segoe UI", 9, "bold"))
        btn_exit   = tk.Button(trig_f, text=" ON EXIT ",  command=lambda: set_trigger("on_exit"),
                               bg="#252525", fg="#666", relief=tk.FLAT, font=("Segoe UI", 9, "bold"))
        btn_manual = tk.Button(trig_f, text=" MANUAL ",   command=lambda: set_trigger("manual"),
                               bg="#252525", fg="#666", relief=tk.FLAT, font=("Segoe UI", 9, "bold"))
        btn_enter.pack(side=tk.LEFT, padx=(0, 4))
        btn_exit.pack(side=tk.LEFT, padx=(0, 4))
        btn_manual.pack(side=tk.LEFT)

        # ── przyciski akcji — nad edytorem (zawsze widoczne) ──
        btn_row = tk.Frame(right, bg="#0d0d0d")
        btn_row.pack(fill=tk.X, padx=12, pady=(10, 4))
        tk.Button(btn_row, text="▶  TEST RUN", command=lambda: run_test(),
                  bg="#1f6feb", fg="white", relief=tk.FLAT,
                  font=("Segoe UI", 9, "bold"), padx=10).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(btn_row, text="💾  SAVE SCRIPT", command=lambda: save_script(),
                  bg="#2ea043", fg="white", relief=tk.FLAT,
                  font=("Segoe UI", 9, "bold"), padx=10).pack(side=tk.LEFT)
        tk.Button(btn_row, text="USUŃ", command=lambda: delete_script(),
                  bg="#8b0000", fg="white", relief=tk.FLAT, padx=8).pack(side=tk.RIGHT)

        hlbl("KOD PYTHON")
        code_wrap = tk.Frame(right, bg="#0d0d0d")
        code_wrap.pack(fill=tk.BOTH, expand=True, padx=12, pady=(2, 8))
        code_t = tk.Text(code_wrap, bg="#1a1a1a", fg="#e6edf3", insertbackground="white",
                         font=("Consolas", 10), relief=tk.FLAT, wrap=tk.NONE,
                         tabs=("1.5c",))
        sc_y = tk.Scrollbar(code_wrap, command=code_t.yview)
        sc_x = tk.Scrollbar(code_wrap, orient="horizontal", command=code_t.xview)
        code_t.configure(yscrollcommand=sc_y.set, xscrollcommand=sc_x.set)
        sc_y.pack(side=tk.RIGHT, fill=tk.Y)
        sc_x.pack(side=tk.BOTTOM, fill=tk.X)
        code_t.pack(fill=tk.BOTH, expand=True)

        # ── FUNKCJE ──────────────────────────────
        TRIG_LABELS = {"on_enter": "▶ enter", "on_exit": "◀ exit", "manual": "⚙ manual"}

        def refresh_list():
            lb.delete(0, tk.END)
            for sc in self.project.scripts.values():
                tag = "GLOBAL" if sc["scope"] == "global" else "ROOM "
                tl  = TRIG_LABELS.get(sc["trigger"], sc["trigger"])
                lb.insert(tk.END, f"  [{tag}]  {sc['name']}  — {tl}")

        def load_script(sid):
            sel_id["v"] = sid
            sc = self.project.scripts[sid]
            name_e.delete(0, tk.END)
            name_e.insert(0, sc["name"])
            code_t.delete("1.0", tk.END)
            code_t.insert("1.0", sc["code"])
            set_scope(sc["scope"])
            set_trigger(sc["trigger"])

        def on_lb_select(e):
            sel = lb.curselection()
            if not sel:
                return
            keys = list(self.project.scripts.keys())
            if sel[0] < len(keys):
                load_script(keys[sel[0]])

        lb.bind("<<ListboxSelect>>", on_lb_select)

        def new_script():
            sid = f"scr_{int(time.time()*1000)}"
            self.project.scripts[sid] = {
                "name": "nowy_skrypt",
                "code": "# Dostępne zmienne:\n# project  — obiekt GamifikatorProject\n# room_id  — id aktualnego pokoju\n# log(msg) — wypisz do konsoli\n\n",
                "scope": "room",
                "room_id": self.current_room_id or "",
                "trigger": "on_enter",
                "created": time.strftime("%Y-%m-%d %H:%M"),
            }
            refresh_list()
            lb.select_clear(0, tk.END)
            lb.select_set(tk.END)
            load_script(sid)
            name_e.focus_set()
            name_e.select_range(0, tk.END)

        def save_script():
            sid = sel_id["v"]
            if not sid:
                self._toast("Utwórz lub wybierz skrypt z listy.", "warn")
                return
            created = self.project.scripts[sid].get("created", time.strftime("%Y-%m-%d %H:%M"))
            self.project.scripts[sid] = {
                "name":    name_e.get().strip() or "skrypt",
                "code":    code_t.get("1.0", tk.END).rstrip("\n"),
                "scope":   scope_v.get(),
                "room_id": self.current_room_id if scope_v.get() == "room" else "",
                "trigger": trig_v.get(),
                "created": created,
            }
            refresh_list()
            self.log(f"Skrypt '{self.project.scripts[sid]['name']}' zapisany.")

        def delete_script():
            sid = sel_id["v"]
            if sid and messagebox.askyesno("Usuń skrypt", "Na pewno usunąć ten skrypt?"):
                del self.project.scripts[sid]
                sel_id["v"] = None
                name_e.delete(0, tk.END)
                code_t.delete("1.0", tk.END)
                refresh_list()

        def run_test():
            raw = code_t.get("1.0", tk.END)
            try:
                ctx = {"log": self.log, "project": self.project,
                       "room_id": self.current_room_id, "game_state": self.game_state}
                exec(self._safe_compile(raw, "<skrypt>"), ctx)
                self.log("[SCRIPT TEST] OK")
            except Exception as e:
                self.log(f"[SCRIPT TEST] Błąd: {e}")
                self._toast(str(e), "error")

        refresh_list()
        set_scope("room")

    # ─────────────────────────────────────────────
    #  DIALOGI
    # ─────────────────────────────────────────────

    def open_dialogs(self):
        if not self.project:
            self._toast("Najpierw stwórz lub otwórz projekt.", "warn")
            return
        if not hasattr(self.project, "dialogs"):
            self.project.dialogs = {}

        win = tk.Toplevel(self.root)
        win.title("System Dialogów")
        win.geometry("1200x720")
        win.configure(bg="#0d0d0d")
        win.transient(self.root)

        sel     = {"dlg": None, "node": None}
        connect = {"on": False, "src": None}
        drag    = {"nid": None, "ox": 0, "oy": 0}
        btn_ref = {}

        # ── LEFT ─────────────────────────────────
        left = tk.Frame(win, bg="#1a1a1a", width=250)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        tk.Button(left, text="+ NOWY DIALOG", command=lambda: new_dialog(),
                  bg="#e67e22", fg="white", relief=tk.FLAT,
                  font=("Segoe UI", 9, "bold")).pack(fill=tk.X, padx=8, pady=(10, 2))

        dlg_lb = tk.Listbox(left, bg="#0d0d0d", fg="#ddd", borderwidth=0,
                            selectbackground="#e67e22", font=("Segoe UI", 9),
                            exportselection=False, activestyle="none")
        dlg_lb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        tk.Label(left, text="HOTPOINT (kto mówi)", bg="#1a1a1a", fg="#e67e22",
                 font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=8)
        hp_var  = tk.StringVar()
        hp_combo = ttk.Combobox(left, textvariable=hp_var, state="readonly", font=("Segoe UI", 8))
        hp_combo.pack(fill=tk.X, padx=8, pady=(0, 2))

        tk.Label(left, text="TRIGGER ITEM (opcj.)", bg="#1a1a1a", fg="#888",
                 font=("Segoe UI", 7)).pack(anchor="w", padx=8)
        trigger_e = tk.Entry(left, bg="#0d0d0d", fg="#f1c40f", insertbackground="white",
                             relief=tk.FLAT, font=("Segoe UI", 8))
        trigger_e.pack(fill=tk.X, padx=8, pady=(0, 4))

        meta_row = tk.Frame(left, bg="#1a1a1a"); meta_row.pack(fill=tk.X, padx=8, pady=2)
        tk.Button(meta_row, text="ZAPISZ META", command=lambda: save_meta(),
                  bg="#555", fg="white", relief=tk.FLAT,
                  font=("Segoe UI", 8)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        tk.Button(meta_row, text="🗑", command=lambda: delete_dialog(),
                  bg="#8b0000", fg="white", relief=tk.FLAT,
                  font=("Segoe UI", 8)).pack(side=tk.LEFT)
        tk.Button(left, text="📋 EXPORT CSV", command=lambda: export_csv(),
                  bg="#333", fg="white", relief=tk.FLAT,
                  font=("Segoe UI", 8)).pack(fill=tk.X, padx=8, pady=(2, 8))

        tk.Frame(win, bg="#2a2a2a", width=2).pack(side=tk.LEFT, fill=tk.Y)

        # ── CENTER ───────────────────────────────
        center = tk.Frame(win, bg="#0d0d0d")
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ctb = tk.Frame(center, bg="#1a1a1a"); ctb.pack(fill=tk.X)

        def _tb(txt, cmd, bg="#333"):
            return tk.Button(ctb, text=txt, command=cmd, bg=bg, fg="white",
                             relief=tk.FLAT, font=("Segoe UI", 8, "bold"), padx=8, pady=5)

        _tb("+ NPC",              lambda: add_node("npc"),    "#1a3a7a").pack(side=tk.LEFT, padx=2, pady=3)
        _tb("+ CHOICE (player)", lambda: add_node("choice"), "#1a5a2a").pack(side=tk.LEFT, padx=2, pady=3)
        btn_ref["con"] = _tb("🔗 POŁĄCZ", lambda: toggle_connect(), "#444")
        btn_ref["con"].pack(side=tk.LEFT, padx=2, pady=3)
        _tb("⚑ START",     lambda: set_start(),        "#b8860b").pack(side=tk.LEFT, padx=2, pady=3)
        _tb("✂ USUŃ LINK", lambda: remove_link(),      "#555").pack(side=tk.LEFT, padx=2, pady=3)
        _tb("🗑 WĘZEŁ",    lambda: delete_node(),       "#8b0000").pack(side=tk.LEFT, padx=2, pady=3)

        nc = tk.Canvas(center, bg="#141414", highlightthickness=0)
        nc.pack(fill=tk.BOTH, expand=True)

        tk.Frame(win, bg="#2a2a2a", width=2).pack(side=tk.LEFT, fill=tk.Y)

        # ── RIGHT ────────────────────────────────
        right = tk.Frame(win, bg="#1a1a1a", width=240)
        right.pack(side=tk.LEFT, fill=tk.Y)
        right.pack_propagate(False)

        def rh(t):
            tk.Label(right, text=t, bg="#1a1a1a", fg="#e67e22",
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(8, 2))

        rh("TYP WĘZŁA")
        type_f = tk.Frame(right, bg="#1a1a1a"); type_f.pack(fill=tk.X, padx=10, pady=2)
        type_v = tk.StringVar(value="npc")

        def set_type(v):
            type_v.set(v)
            b_npc.config(bg="#1a3a7a" if v == "npc" else "#252525",
                         fg="white" if v == "npc" else "#666")
            b_cho.config(bg="#1a5a2a" if v == "choice" else "#252525",
                         fg="white" if v == "choice" else "#666")

        b_npc = tk.Button(type_f, text=" NPC ",    command=lambda: set_type("npc"),
                          bg="#1a3a7a", fg="white", relief=tk.FLAT, font=("Segoe UI", 8, "bold"))
        b_npc.pack(side=tk.LEFT, padx=(0, 4))
        b_cho = tk.Button(type_f, text=" CHOICE ", command=lambda: set_type("choice"),
                          bg="#252525", fg="#666", relief=tk.FLAT, font=("Segoe UI", 8, "bold"))
        b_cho.pack(side=tk.LEFT)

        rh("MÓWI (speaker)")
        spk_e = tk.Entry(right, bg="#0d0d0d", fg="white", insertbackground="white",
                         relief=tk.FLAT, font=("Segoe UI", 9))
        spk_e.pack(fill=tk.X, padx=10, pady=2, ipady=3)

        rh("TEKST DIALOGU")
        txt_t = tk.Text(right, bg="#0d0d0d", fg="white", insertbackground="white",
                        relief=tk.FLAT, font=("Segoe UI", 9), height=5, wrap=tk.WORD)
        txt_t.pack(fill=tk.X, padx=10, pady=2)

        rh("CZAS WYŚW. (s)")
        dur_e = tk.Entry(right, bg="#0d0d0d", fg="#00ff88", insertbackground="white",
                         relief=tk.FLAT, font=("Segoe UI", 9), width=6)
        dur_e.insert(0, "3.0"); dur_e.pack(anchor="w", padx=10, pady=2, ipady=3)

        rh("🎁 DAJE PRZEDMIOT")
        give_e = tk.Entry(right, bg="#0d0d0d", fg="#f1c40f", insertbackground="white",
                          relief=tk.FLAT, font=("Segoe UI", 9))
        give_e.pack(fill=tk.X, padx=10, pady=2, ipady=3)

        tk.Button(right, text="💾  ZAPISZ WĘZEŁ", command=lambda: save_node(),
                  bg="#e67e22", fg="white", relief=tk.FLAT,
                  font=("Segoe UI", 9, "bold")).pack(fill=tk.X, padx=10, pady=(14, 4))

        # ── STAŁE ────────────────────────────────
        NW = {"npc": 200, "choice": 178}
        NH = {"npc": 78,  "choice": 58}
        COL = {
            "npc":    {"fill": "#0e1f3e", "brd": "#3a7fd4", "txt": "#8fc8f8", "tag": "#3a7fd4"},
            "choice": {"fill": "#0a2414", "brd": "#3aad6a", "txt": "#88f0a8", "tag": "#3aad6a"},
        }

        # ── RYSOWANIE ────────────────────────────
        def redraw():
            nc.delete("all")
            dlg = _dlg()
            if not dlg:
                nc.create_text(450, 260, text="Wybierz lub utwórz dialog",
                               fill="#2a2a2a", font=("Segoe UI", 14))
                return
            nodes = dlg["nodes"]
            start_id = dlg.get("start", "")

            for nid, node in nodes.items():
                nx, ny = node.get("x", 80), node.get("y", 80)
                nw = NW[node["type"]]; nh = NH[node["type"]]
                c = COL[node["type"]]
                if node["type"] == "npc":
                    for cid in node.get("choices", []):
                        if cid in nodes:
                            cn = nodes[cid]
                            cx, cy = cn.get("x", 80), cn.get("y", 80)
                            nc.create_line(nx + nw, ny + nh // 2,
                                           cx, cy + NH["choice"] // 2,
                                           fill=c["brd"], width=2,
                                           arrow=tk.LAST, arrowshape=(10, 13, 4))
                nxt = node.get("next", "")
                if nxt and nxt in nodes:
                    nn = nodes[nxt]
                    tx, ty = nn.get("x", 80), nn.get("y", 80)
                    nc.create_line(nx + nw, ny + nh // 2,
                                   tx, ty + NH[nn["type"]] // 2,
                                   fill="#666", width=2,
                                   arrow=tk.LAST, arrowshape=(10, 13, 4))

            for nid, node in nodes.items():
                nx, ny = node.get("x", 80), node.get("y", 80)
                nw = NW[node["type"]]; nh = NH[node["type"]]
                c = COL[node["type"]]
                is_sel = (nid == sel["node"])
                nc.create_rectangle(nx, ny, nx + nw, ny + nh,
                                    fill=c["fill"],
                                    outline="#fff" if is_sel else c["brd"],
                                    width=3 if is_sel else 1,
                                    tags=f"nd_{nid}")
                if nid == start_id:
                    nc.create_text(nx + 6, ny + 5, text="▶ START", fill="#f1c40f",
                                   font=("Consolas", 7, "bold"), anchor="nw")
                nc.create_text(nx + 8, ny + 16, text=f"[{node.get('speaker','?')}]",
                               fill=c["tag"], font=("Segoe UI", 7, "bold"), anchor="nw")
                raw = node.get("text", "")
                disp = (raw[:37] + "…") if len(raw) > 37 else raw
                nc.create_text(nx + 8, ny + 30, text=disp, fill=c["txt"],
                               font=("Segoe UI", 8), anchor="nw", width=nw - 16)
                give = node.get("give_item", "")
                if give:
                    nc.create_text(nx + 8, ny + nh - 13, text=f"🎁 {give}",
                                   fill="#f1c40f", font=("Segoe UI", 7), anchor="nw")
                nc.create_text(nx + nw - 6, ny + 6,
                               text=f"{node.get('dur',3.0):.1f}s",
                               fill="#555", font=("Segoe UI", 6), anchor="ne")

        # ── KLIKNIĘCIA CANVASA ───────────────────
        def _node_at(ex, ey):
            dlg = _dlg()
            if not dlg: return None
            for nid in reversed(list(dlg["nodes"].keys())):
                n = dlg["nodes"][nid]
                nx, ny = n.get("x", 0), n.get("y", 0)
                if nx <= ex <= nx + NW[n["type"]] and ny <= ey <= ny + NH[n["type"]]:
                    return nid
            return None

        def on_nc_press(event):
            nid = _node_at(event.x, event.y)
            if connect["on"]:
                if nid:
                    if connect["src"] is None:
                        connect["src"] = nid
                        btn_ref["con"].config(text=f"🔗 → {nid[:12]}…", bg="#e67e22")
                    else:
                        _do_connect(connect["src"], nid)
                        connect["src"] = None; connect["on"] = False
                        btn_ref["con"].config(text="🔗 POŁĄCZ", bg="#444")
                        redraw()
                return
            if nid:
                sel["node"] = nid
                drag["nid"] = nid
                drag["ox"] = event.x - _dlg()["nodes"][nid].get("x", 0)
                drag["oy"] = event.y - _dlg()["nodes"][nid].get("y", 0)
                _load_node(nid)
            else:
                sel["node"] = None; drag["nid"] = None
            redraw()

        def on_nc_drag(event):
            if drag["nid"] and _dlg():
                n = _dlg()["nodes"][drag["nid"]]
                n["x"] = max(0, event.x - drag["ox"])
                n["y"] = max(0, event.y - drag["oy"])
                redraw()

        def on_nc_release(event): drag["nid"] = None

        nc.bind("<Button-1>",        on_nc_press)
        nc.bind("<B1-Motion>",       on_nc_drag)
        nc.bind("<ButtonRelease-1>", on_nc_release)

        # ── POŁĄCZENIA ───────────────────────────
        def _do_connect(src_id, dst_id):
            dlg = _dlg()
            if not dlg: return
            src = dlg["nodes"].get(src_id); dst = dlg["nodes"].get(dst_id)
            if not src or not dst: return
            if src["type"] == "npc" and dst["type"] == "choice":
                if dst_id not in src.setdefault("choices", []):
                    src["choices"].append(dst_id)
            else:
                src["next"] = dst_id

        def toggle_connect():
            connect["on"] = not connect["on"]; connect["src"] = None
            if connect["on"]:
                btn_ref["con"].config(text="🔗 [kliknij źródło]", bg="#e67e22")
            else:
                btn_ref["con"].config(text="🔗 POŁĄCZ", bg="#444")

        def remove_link():
            nid = sel["node"]; dlg = _dlg()
            if not nid or not dlg: return
            n = dlg["nodes"][nid]; n["next"] = ""; n["choices"] = []
            for other in dlg["nodes"].values():
                if other.get("next") == nid: other["next"] = ""
                if nid in other.get("choices", []): other["choices"].remove(nid)
            redraw()

        # ── WĘZŁY CRUD ───────────────────────────
        def add_node(ntype):
            dlg = _dlg()
            if not dlg:
                self._toast("Utwórz lub wybierz dialog.", "warn"); return
            nid = f"n{int(time.time()*100) % 999999}"
            xs = [n.get("x", 0) + NW[n["type"]] for n in dlg["nodes"].values()]
            nx = max(xs) + 30 if xs else 60
            ny = 80 + (len(dlg["nodes"]) * 30) % 280
            default_spk = (dlg.get("hotpoint_id") or "NPC") if ntype == "npc" else "Player"
            dlg["nodes"][nid] = {
                "type": ntype, "speaker": default_spk,
                "text": "...", "dur": 3.0 if ntype == "npc" else 0.0,
                "give_item": "", "choices": [], "next": "", "x": nx, "y": ny,
            }
            if not dlg.get("start"): dlg["start"] = nid
            sel["node"] = nid; _load_node(nid); redraw()

        def delete_node():
            nid = sel["node"]; dlg = _dlg()
            if not nid or not dlg or nid not in dlg["nodes"]: return
            for n in dlg["nodes"].values():
                if n.get("next") == nid: n["next"] = ""
                if nid in n.get("choices", []): n["choices"].remove(nid)
            del dlg["nodes"][nid]
            if dlg.get("start") == nid:
                dlg["start"] = next(iter(dlg["nodes"]), "")
            sel["node"] = None; redraw()

        def set_start():
            nid = sel["node"]; dlg = _dlg()
            if nid and dlg: dlg["start"] = nid; redraw()

        # ── PANEL WŁAŚCIWOŚCI ────────────────────
        def _load_node(nid):
            dlg = _dlg()
            if not dlg or nid not in dlg["nodes"]: return
            n = dlg["nodes"][nid]
            set_type(n.get("type", "npc"))
            spk_e.delete(0, tk.END);  spk_e.insert(0, n.get("speaker", ""))
            txt_t.delete("1.0", tk.END); txt_t.insert("1.0", n.get("text", ""))
            dur_e.delete(0, tk.END);  dur_e.insert(0, str(n.get("dur", 3.0)))
            give_e.delete(0, tk.END); give_e.insert(0, n.get("give_item", ""))

        def save_node():
            nid = sel["node"]; dlg = _dlg()
            if not nid or not dlg or nid not in dlg["nodes"]: return
            n = dlg["nodes"][nid]
            n["type"] = type_v.get(); n["speaker"] = spk_e.get().strip()
            n["text"] = txt_t.get("1.0", tk.END).strip(); n["give_item"] = give_e.get().strip()
            try: n["dur"] = float(dur_e.get())
            except: n["dur"] = 3.0
            redraw()

        # ── LISTA DIALOGÓW ───────────────────────
        def _dlg():
            did = sel["dlg"]
            if did and hasattr(self.project, "dialogs") and did in self.project.dialogs:
                return self.project.dialogs[did]
            return None

        def refresh_list():
            dlg_lb.delete(0, tk.END)
            if not hasattr(self.project, "dialogs"): return
            for dlg in self.project.dialogs.values():
                hp = dlg.get("hotpoint_id", "")
                dlg_lb.insert(tk.END, f"  {dlg['name']}  {'→ ' + hp if hp else ''}")

        def _load_dlg(did):
            sel["dlg"] = did; sel["node"] = None
            dlg = self.project.dialogs.get(did, {})
            hp_var.set(dlg.get("hotpoint_id", ""))
            trigger_e.delete(0, tk.END); trigger_e.insert(0, dlg.get("trigger_item", ""))
            redraw()

        def on_lb_sel(e):
            s = dlg_lb.curselection()
            if not s: return
            keys = list(self.project.dialogs.keys())
            if s[0] < len(keys): _load_dlg(keys[s[0]])

        dlg_lb.bind("<<ListboxSelect>>", on_lb_sel)

        def new_dialog():
            did = f"dlg{int(time.time()*100) % 999999}"
            nid = f"n{int(time.time()*100+1) % 999999}"
            self.project.dialogs[did] = {
                "name": f"dialog_{len(self.project.dialogs)+1}",
                "hotpoint_id": "", "trigger_item": "", "start": nid,
                "nodes": {
                    nid: {"type": "npc", "speaker": "NPC",
                          "text": "Witaj podróżniku!", "dur": 3.0,
                          "give_item": "", "choices": [], "next": "",
                          "x": 60, "y": 130}
                }
            }
            refresh_list()
            dlg_lb.select_clear(0, tk.END); dlg_lb.select_set(tk.END)
            _load_dlg(did); _refresh_hp_combo()

        def save_meta():
            did = sel["dlg"]
            if not did or did not in self.project.dialogs: return
            dlg = self.project.dialogs[did]
            new_hp = hp_var.get()
            dlg["hotpoint_id"] = new_hp
            dlg["trigger_item"] = trigger_e.get().strip()
            if new_hp:
                for n in dlg["nodes"].values():
                    if n["type"] == "npc" and n.get("speaker", "") in ("NPC", ""):
                        n["speaker"] = new_hp
            refresh_list()
            redraw()

        def delete_dialog():
            did = sel["dlg"]
            if did and messagebox.askyesno("Usuń", "Usunąć dialog?"):
                del self.project.dialogs[did]
                sel["dlg"] = None; refresh_list(); redraw()

        def _refresh_hp_combo():
            hps = [""]
            if self.current_room_id and self.current_room_id in self.project.rooms:
                for hp in self.project.rooms[self.current_room_id].get("hotpoints", []):
                    hps.append(self._as_hp(hp).id)
            hp_combo["values"] = hps

        def export_csv():
            import csv
            dlg = _dlg()
            if not dlg:
                self._toast("Wybierz dialog.", "warn"); return
            p = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV", "*.csv")])
            if not p: return
            with open(p, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["node_id","type","speaker","text","dur",
                            "give_item","next","choices","is_start"])
                for nid, n in dlg["nodes"].items():
                    w.writerow([nid, n["type"], n.get("speaker",""), n.get("text",""),
                                n.get("dur",3.0), n.get("give_item",""), n.get("next",""),
                                "|".join(n.get("choices",[])),
                                "1" if nid == dlg.get("start") else ""])
            self.log(f"CSV zapisany: {p}")

        _refresh_hp_combo(); refresh_list(); redraw()

    def _safe_compile(self, code, name="<skrypt>"):
        code = textwrap.dedent(code).strip()
        try:
            return compile(code, name, "exec")
        except IndentationError:
            code = "\n".join(line.lstrip() for line in code.splitlines())
            return compile(code, name, "exec")

    def _run_scripts(self, trigger):
        if not self.project or not hasattr(self.project, "scripts"):
            return
        for sc in self.project.scripts.values():
            if sc["trigger"] != trigger:
                continue
            if sc["scope"] == "room" and sc.get("room_id") != self.current_room_id:
                continue
            try:
                ctx = {"log": self.log, "project": self.project,
                       "room_id": self.current_room_id, "game_state": self.game_state}
                exec(self._safe_compile(sc["code"], f"<{sc['name']}>"), ctx)
            except Exception as e:
                self.log(f"[SCRIPT] '{sc['name']}' błąd: {e}")

    # ─────────────────────────────────────────────
    #  ENGINE LOOP
    # ─────────────────────────────────────────────

    def engine_loop(self):
        self.anim_tick += 1
        if self.is_playing:
            self._update_player_position()
            self.active_dialogs = [dg for dg in self.active_dialogs if dg["end"] > time.time()]
        try:
            self.refresh_canvas()
        except Exception as e:
            self.log(f"[RENDER ERR] {e}")
        self.root.after(100, self.engine_loop)

    def _update_player_position(self):
        dx = self.player_target[0] - self.player_runtime_pos[0]
        dy = self.player_target[1] - self.player_runtime_pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        if dist <= 3:
            return
        if dx < -1:
            self.facing_left = True
        elif dx > 1:
            self.facing_left = False
        speed = self.project.player.get("walk_speed", 10)
        self.player_runtime_pos[0] += (dx / dist) * speed
        self.player_runtime_pos[1] += (dy / dist) * speed

    def toggle_play(self):
        if not self.current_room_id:
            return
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.btn_play.config(text="STOP [ESC]", bg="#8b0000")
            self.tool_frame.pack_forget()
            self.sidebar.pack_forget()
            self.con_frame.pack_forget()
            r = self.project.rooms[self.current_room_id]
            self.player_runtime_pos = list(r.get("player_pos", [960, 540]))
            self.player_target = list(self.player_runtime_pos)
            self.swapped_hotpoints.clear()
            self.active_dialogs.clear()
            self.player_inventory.clear()
            self.collected_items.clear()
            self._run_scripts("on_enter")
        else:
            self.game_state.clear()
            self.active_dialog = None
            self.btn_play.config(text="► PLAY MODE", bg="#007acc")
            self.tool_frame.pack(side=tk.LEFT, fill=tk.Y, padx=1)
            self.sidebar.pack(side=tk.RIGHT, fill=tk.Y)
            if self.logs_visible:
                self.main_pane.add(self.con_frame, height=120)
        self.refresh_canvas()

    def toggle_logs(self):
        self.logs_visible = not self.logs_visible
        if self.logs_visible:
            self.main_pane.add(self.con_frame, height=120)
        else:
            self.main_pane.forget(self.con_frame)

    # ─────────────────────────────────────────────
    #  CANVAS EVENTS
    # ─────────────────────────────────────────────

    def handle_runtime_click(self, x, y):
        room = self.project.rooms[self.current_room_id]
        target_x, target_y = x, y
        hit_hp = None
        for hp in reversed(room["hotpoints"]):
            hp_obj = self._as_hp(hp)
            if hp_obj.x <= x <= hp_obj.x + hp_obj.w and hp_obj.y <= y <= hp_obj.y + hp_obj.h:
                hit_hp = hp_obj
                target_x, target_y = hp_obj.x + hp_obj.w // 2, hp_obj.y + hp_obj.h
                break
        try:
            polys = []
            for p in room.get("walkable", []):
                pts = self._wa_pts(p)
                if len(pts) >= 6:
                    polys.append(Polygon([(pts[j], pts[j+1]) for j in range(0, len(pts), 2)]))
            if not polys:
                self.player_target = [target_x, target_y]
            else:
                combined = unary_union(polys)
                tp = Point(target_x, target_y)
                if combined.contains(tp):
                    self.player_target = [target_x, target_y]
                else:
                    nearest = nearest_points(combined, tp)[0]
                    self.player_target = [int(nearest.x), int(nearest.y)]
        except Exception as e:
            self.log(f"[NAV ERR] {e}")
            self.player_target = [target_x, target_y]
        if hit_hp:
            # skip already-collected items
            if hit_hp.id in self.collected_items:
                return
            # check required item
            req = getattr(hit_hp, 'required_item', '')
            if req and req not in self.player_inventory:
                self._show_wrong_item(hit_hp)
                return
            # pick up item
            if getattr(hit_hp, 'is_item', False):
                self.player_inventory.append(hit_hp.id)
                self.collected_items.add(hit_hp.id)
                self.log(f"[ITEM] Podniesiono: {hit_hp.id}")
                return
            if hit_hp.flow.get("swap"):
                self.swapped_hotpoints.add(hit_hp.id)
            # dialog system ma priorytet nad komentarzami
            if hasattr(self.project, "dialogs"):
                for did, dlg in self.project.dialogs.items():
                    if dlg.get("hotpoint_id") == hit_hp.id:
                        start = dlg.get("start", "")
                        if start and start in dlg["nodes"]:
                            sn = dlg["nodes"][start]
                            self.active_dialog = {
                                "did": did, "nid": start, "phase": "npc",
                                "end_time": time.time() + sn.get("dur", 3.0),
                                "choice_rects": [],
                            }
                            return
            self.execute_comments_runtime(hit_hp)

    def execute_comments_runtime(self, hp):
        if not hp.comments:
            return
        self.active_dialogs.clear()
        dur = float(getattr(hp, 'comment_dur', 2.0))
        gap = float(getattr(hp, 'comment_gap', 0.5))
        delay = 0.0
        for c in hp.comments:
            def show(txt=c["text"], own=c["owner"], h=hp, d=dur):
                self.active_dialogs.clear()
                self.active_dialogs.append({"text": txt, "owner": own, "hp_id": h.id, "end": time.time() + d})
            self.root.after(int(delay * 1000), show)
            delay += dur + gap

    def on_canvas_down(self, event):
        if self.is_playing and self.active_dialog:
            phase = self.active_dialog.get("phase")
            if phase == "choices":
                for rect in self.active_dialog.get("choice_rects", []):
                    if rect["x1"] <= event.x <= rect["x2"] and rect["y1"] <= event.y <= rect["y2"]:
                        self._select_dialog_choice(rect["cid"])
                        return
                return  # blokuj kliknięcia podczas wyboru
            elif phase == "npc":
                self.active_dialog["end_time"] = 0  # klik = pomiń czas
                return
        x, y = int(event.x / self.view_scale), int(event.y / self.view_scale)
        if self.is_playing:
            self.handle_runtime_click(x, y)
            return
        room = self.project.rooms.get(self.current_room_id)
        if not room:
            return
        for i, raw in enumerate(reversed(room["hotpoints"])):
            hp = self._as_hp(raw)
            edge = self._hp_edge_at(hp, x, y)
            if edge:
                self.save_undo()
                self.drag_data = {"mode": edge, "obj": hp,
                                  "start_w": hp.w, "start_h": hp.h,
                                  "start_x": x, "start_y": y,
                                  "orig_x": hp.x, "orig_y": hp.y}
                self.selected_object = {"type": "hp", "idx": len(room["hotpoints"])-1-i}
                self.refresh_canvas()
                return
        if self.mode == "Select":
            self._handle_select_click(room, x, y)
        elif self.mode == "Hotpoint":
            self._handle_hotpoint_click(room, x, y)
        elif self.mode == "Walkable":
            self._handle_walkable_click(x, y)

    def _handle_select_click(self, room, x, y):
        if "player_pos" in room:
            px, py = room["player_pos"]
            s = self.project.player.get("scale", 100) / 100.0
            if px-100*s <= x <= px+100*s and py-200*s <= y <= py:
                self.save_undo()
                self.drag_data = {"mode": "move_player", "obj": room, "off_x": x-px, "off_y": y-py}
                self.selected_object = {"type": "player"}
                return
        for i, raw in enumerate(reversed(room["hotpoints"])):
            hp = self._as_hp(raw)
            if hp.x <= x <= hp.x+hp.w and hp.y <= y <= hp.y+hp.h:
                self.save_undo()
                self.drag_data = {"mode": "move", "obj": hp, "off_x": x-hp.x, "off_y": y-hp.y}
                self.selected_object = {"type": "hp", "idx": len(room["hotpoints"])-1-i}
                self.refresh_canvas()
                return
        for i, wa in enumerate(room["walkable"]):
            pts = self._wa_pts(wa)
            if min(pts[0::2]) <= x <= max(pts[0::2]):
                self.selected_object = {"type": "wa", "idx": i}
                self.refresh_canvas()
                return
        self.selected_object = None
        self.refresh_canvas()

    def _handle_hotpoint_click(self, room, x, y):
        new_hp = Hotpoint(id=f"hp_{len(room['hotpoints'])+1}", x=x-50, y=y-50, w=100, h=100)
        room["hotpoints"].append(new_hp)
        self.selected_object = {"type": "hp", "idx": len(room["hotpoints"])-1}
        self.refresh_obj_tree()
        self.refresh_canvas()

    def _handle_walkable_click(self, x, y):
        if self.temp_points and math.sqrt((x-self.temp_points[0])**2 + (y-self.temp_points[1])**2) < 25:
            self.finish_polygon()
            return
        self.temp_points.extend([x, y])
        self.refresh_canvas()

    def on_canvas_right_click(self, event):
        if self.mode == "Walkable":
            self.finish_polygon()
            return
        if not self.current_room_id:
            return
        cx, cy = event.x / self.view_scale, event.y / self.view_scale
        for hp in reversed(self.project.rooms[self.current_room_id]["hotpoints"]):
            hp_obj = self._as_hp(hp)
            if hp_obj.x <= cx <= hp_obj.x+hp_obj.w and hp_obj.y <= cy <= hp_obj.y+hp_obj.h:
                self.open_hp_settings(hp_obj)
                return

    def on_canvas_up(self, e):
        self.drag_data = {"obj": None, "mode": None}

    def on_canvas_drag(self, event):
        if not self.drag_data["obj"]:
            return
        x, y = int(event.x / self.view_scale), int(event.y / self.view_scale)
        o = self.drag_data["obj"]
        mode = self.drag_data["mode"]
        if mode == "move_player":
            o["player_pos"] = [x - self.drag_data["off_x"], y - self.drag_data["off_y"]]
        elif mode == "move":
            o.x = x - self.drag_data["off_x"]
            o.y = y - self.drag_data["off_y"]
        elif mode == "resize_right":
            o.w = max(20, self.drag_data["start_w"] + (x - self.drag_data["start_x"]))
        elif mode == "resize_left":
            delta = x - self.drag_data["start_x"]
            o.x = self.drag_data["orig_x"] + delta
            o.w = max(20, self.drag_data["start_w"] - delta)
        elif mode == "resize_bottom":
            o.h = max(20, self.drag_data["start_h"] + (y - self.drag_data["start_y"]))
        elif mode == "resize_top":
            delta = y - self.drag_data["start_y"]
            o.y = self.drag_data["orig_y"] + delta
            o.h = max(20, self.drag_data["start_h"] - delta)
        self.refresh_canvas()

    def on_canvas_motion(self, event):
        if self.is_playing or not self.current_room_id:
            return
        room = self.project.rooms.get(self.current_room_id)
        if not room:
            return
        x, y = int(event.x / self.view_scale), int(event.y / self.view_scale)
        for raw in room.get("hotpoints", []):
            hp = self._as_hp(raw)
            edge = self._hp_edge_at(hp, x, y)
            if edge in ("resize_left", "resize_right"):
                self.canvas.config(cursor="size_we")
                return
            if edge in ("resize_top", "resize_bottom"):
                self.canvas.config(cursor="size_ns")
                return
        self.canvas.config(cursor="")

    def setup_canvas_events(self):
        self.canvas.bind("<Button-1>",        self.on_canvas_down)
        self.canvas.bind("<B1-Motion>",       self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_up)
        self.canvas.bind("<Motion>",          self.on_canvas_motion)
        self.canvas.bind("<Button-3>",        self.on_canvas_right_click)
        self.root.bind_all("<Delete>", self.delete_selected)
        self.root.bind("<Control-z>", self.undo)
        self.root.bind("<Escape>", lambda e: self.toggle_play() if self.is_playing else None)

    # ─────────────────────────────────────────────
    #  HOTPOINT SETTINGS
    # ─────────────────────────────────────────────

    def open_hp_settings(self, hp=None):
        if not hp and self.selected_object and self.selected_object["type"] == "hp":
            hp = self.project.rooms[self.current_room_id]["hotpoints"][self.selected_object["idx"]]
        if not hp:
            return
        hp = self._as_hp(hp)
        d = tk.Toplevel(self.root)
        d.title(f"Settings: {hp.id}")
        d.geometry("650x950")
        d.grab_set()
        d.configure(bg="#1e1e1e")
        d.transient(self.root)

        def lbl(t):
            tk.Label(d, text=t, bg="#1e1e1e", fg="#C4A35A",
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20, pady=(10, 0))

        f_top = tk.Frame(d, bg="#1e1e1e"); f_top.pack(fill=tk.X, padx=20)
        ne = tk.Entry(f_top, width=15); ne.insert(0, hp.id); ne.pack(side=tk.LEFT)
        xe = tk.Entry(f_top, width=5);  xe.insert(0, str(hp.x)); xe.pack(side=tk.LEFT, padx=5)
        ye = tk.Entry(f_top, width=5);  ye.insert(0, str(hp.y)); ye.pack(side=tk.LEFT)

        lbl("GRAPHICS")
        f_g = tk.Frame(d, bg="#1e1e1e"); f_g.pack(fill=tk.X, padx=20)
        b_v = tk.StringVar(value=hp.image_path)
        tk.Entry(f_g, textvariable=b_v).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(f_g, text="BASE",
                  command=lambda: b_v.set(filedialog.askopenfilename() or b_v.get())).pack(side=tk.LEFT)
        tk.Button(f_g, text="📚",
                  command=lambda: self._pick_from_anim_lib(d, lambda aid: b_v.set(
                      self.project.animations[aid]["sheet_path"])),
                  bg="#7B2FBE", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
        s_v = tk.StringVar(value=hp.swap_image_path)
        tk.Entry(f_g, textvariable=s_v).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(f_g, text="SWAP",
                  command=lambda: s_v.set(filedialog.askopenfilename() or s_v.get())).pack(side=tk.LEFT)
        tk.Button(f_g, text="📚",
                  command=lambda: self._pick_from_anim_lib(d, lambda aid: s_v.set(
                      self.project.animations[aid]["sheet_path"])),
                  bg="#7B2FBE", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=2)

        lbl("OPACITY LIVE %")
        def live_op(v): hp.opacity = int(v); self.refresh_canvas()
        op_v = tk.Scale(d, from_=10, to=100, orient=tk.HORIZONTAL, bg="#1e1e1e", fg="white", command=live_op)
        op_v.set(getattr(hp, 'opacity', 100)); op_v.pack(fill=tk.X, padx=20)

        lbl("SCALE LIVE %")
        def live_hp_sc(v): hp.scale_png = int(v); self.refresh_canvas()
        sc_v = tk.Scale(d, from_=10, to=500, orient=tk.HORIZONTAL, bg="#1e1e1e", fg="white", command=live_hp_sc)
        sc_v.set(hp.scale_png); sc_v.pack(fill=tk.X, padx=20)

        lbl("FLOW")
        f_chk = tk.Frame(d, bg="#252526"); f_chk.pack(fill=tk.X, padx=20, pady=5)
        chk_vars = {k: tk.BooleanVar(value=v) for k, v in hp.flow.items()}
        for k, t in [("p_com", "Player Comment"), ("h_com", "Hotpoint Comment"),
                     ("unlock", "Unlock LOCK"), ("swap", "Swap PNG"), ("move", "Change Room")]:
            tk.Checkbutton(f_chk, text=t, variable=chk_vars[k],
                           bg="#252526", fg="#eee", selectcolor="#121212").pack(anchor="w", padx=5)

        lbl("ITEM")
        item_f = tk.Frame(d, bg="#252526"); item_f.pack(fill=tk.X, padx=20, pady=5)
        is_item_v = tk.BooleanVar(value=getattr(hp, 'is_item', False))
        tk.Checkbutton(item_f, text="Jest przedmiotem (gracz może podnieść)",
                       variable=is_item_v, bg="#252526", fg="#eee",
                       selectcolor="#121212").pack(anchor="w", padx=5)
        req_row = tk.Frame(item_f, bg="#252526"); req_row.pack(fill=tk.X, padx=5, pady=(4, 2))
        tk.Label(req_row, text="Wymagany przedmiot (ID):", bg="#252526", fg="#aaa",
                 font=("Segoe UI", 8)).pack(side=tk.LEFT)
        req_e = tk.Entry(req_row, width=14, bg="#121212", fg="#f1c40f",
                         insertbackground="white", relief=tk.FLAT)
        req_e.insert(0, getattr(hp, 'required_item', ''))
        req_e.pack(side=tk.LEFT, padx=5)

        lbl("TIMING KOMENTARZY")
        t_f = tk.Frame(d, bg="#1e1e1e"); t_f.pack(fill=tk.X, padx=20, pady=4)
        tk.Label(t_f, text="Czas wyśw. (s):", bg="#1e1e1e", fg="#aaa", font=("Segoe UI", 8)).pack(side=tk.LEFT)
        dur_e = tk.Entry(t_f, width=5, bg="#121212", fg="#00ff00", insertbackground="white", relief=tk.FLAT)
        dur_e.insert(0, str(getattr(hp, 'comment_dur', 2.0))); dur_e.pack(side=tk.LEFT, padx=(4, 16))
        tk.Label(t_f, text="Przerwa (s):", bg="#1e1e1e", fg="#aaa", font=("Segoe UI", 8)).pack(side=tk.LEFT)
        gap_e = tk.Entry(t_f, width=5, bg="#121212", fg="#00ff00", insertbackground="white", relief=tk.FLAT)
        gap_e.insert(0, str(getattr(hp, 'comment_gap', 0.5))); gap_e.pack(side=tk.LEFT, padx=4)

        lbl("KOMENTARZE")
        com_f = tk.Frame(d, bg="#121212"); com_f.pack(fill=tk.BOTH, expand=True, padx=20)

        def add_com(t="", o="p"):
            r = tk.Frame(com_f, bg="#121212"); r.pack(fill=tk.X, pady=1)
            ow = tk.StringVar(value=o)
            tk.Button(r, textvariable=ow, width=2, bg="#333",
                      command=lambda v=ow: v.set("h" if v.get() == "p" else "p")).pack(side=tk.LEFT)
            e = tk.Entry(r, bg="#1e1e1e", fg="white")
            e.insert(0, t); e.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            tk.Button(r, text="X", command=r.destroy, bg="#555").pack(side=tk.RIGHT)

        tk.Button(d, text="+ ADD LINE", command=add_com).pack()
        for c in hp.comments:
            add_com(c["text"], c["owner"])

        def save():
            self.save_undo()
            hp.id = ne.get()
            hp.x, hp.y = int(xe.get()), int(ye.get())
            hp.scale_png, hp.opacity = sc_v.get(), op_v.get()
            hp.flow = {k: v.get() for k, v in chk_vars.items()}
            hp.image_path = b_v.get()
            hp.swap_image_path = s_v.get()
            hp.is_item = is_item_v.get()
            hp.required_item = req_e.get().strip()
            try: hp.comment_dur = float(dur_e.get())
            except ValueError: hp.comment_dur = 2.0
            try: hp.comment_gap = float(gap_e.get())
            except ValueError: hp.comment_gap = 0.5
            hp.comments = [
                {"text": w.winfo_children()[1].get(), "owner": w.winfo_children()[0].cget("text")}
                for w in com_f.winfo_children()
                if len(w.winfo_children()) > 1
            ]
            self.refresh_canvas()
            d.destroy()

        tk.Button(d, text="SAVE", command=save, bg="#007acc", fg="white",
                  pady=15).pack(fill=tk.X, padx=20, pady=20)

    # ─────────────────────────────────────────────
    #  PLAYER SETTINGS
    # ─────────────────────────────────────────────

    def open_player_settings(self):
        d = tk.Toplevel(self.root)
        d.title("Avatar Config")
        d.geometry("600x800")
        d.grab_set()
        d.configure(bg="#1e1e1e")
        d.transient(self.root)
        preview_cv = tk.Canvas(d, width=200, height=200, bg="#121212", highlightthickness=0)
        preview_cv.pack(pady=10)
        self.preview_image_ref = None

        def row(k):
            f = tk.Frame(d, bg="#1e1e1e"); f.pack(fill=tk.X, padx=20, pady=2)
            tk.Label(f, text=k.upper(), bg="#1e1e1e", fg="#aaa", width=10).pack(side=tk.LEFT)
            p_v = tk.StringVar(value=self.project.player["animations"][k]["path"])
            f_v = tk.StringVar(value=str(self.project.player["animations"][k]["frames"]))
            tk.Entry(f, textvariable=p_v, bg="#121212", fg="white", bd=0).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            tk.Button(f, text="...",
                      command=lambda: p_v.set(filedialog.askopenfilename() or p_v.get())).pack(side=tk.LEFT)
            def _lib_pick(pv=p_v, fv=f_v):
                def cb(aid):
                    a = self.project.animations[aid]
                    pv.set(a["sheet_path"]); fv.set(str(a["frames"]))
                self._pick_from_anim_lib(d, cb)
            tk.Button(f, text="📚", command=_lib_pick,
                      bg="#7B2FBE", fg="white", relief=tk.FLAT, padx=4).pack(side=tk.LEFT, padx=2)
            tk.Entry(f, textvariable=f_v, width=3, bg="#121212", fg="#00ff00", bd=0).pack(side=tk.LEFT, padx=5)
            return {"path": p_v, "frames": f_v}

        rvs = {k: row(k) for k in ["idle", "walk_r", "walk_u", "walk_d"]}
        sp = tk.Scale(d, from_=1, to=100, orient=tk.HORIZONTAL, label="WALK SPEED",
                      bg="#1e1e1e", fg="white")
        sp.set(self.project.player.get("walk_speed", 10)); sp.pack(fill=tk.X, padx=20)

        def live_p_sc(v): self.project.player["scale"] = int(v); self.refresh_canvas()
        sc = tk.Scale(d, from_=10, to=500, orient=tk.HORIZONTAL, label="PLAYER SCALE %",
                      bg="#1e1e1e", fg="white", command=live_p_sc)
        sc.set(self.project.player.get("scale", 100)); sc.pack(fill=tk.X, padx=20)

        def update_preview():
            if not d.winfo_exists():
                return
            self.preview_anim_tick += 1
            idle_data = rvs["idle"]
            path = idle_data["path"].get()
            frames = max(1, int(idle_data["frames"].get() or 1))
            if path and os.path.exists(path):
                img = Image.open(path).convert("RGBA")
                fw = max(1, img.width // frames)
                fh = img.height
                tick = self.preview_anim_tick % frames
                frame_img = img.crop((tick * fw, 0, (tick + 1) * fw, fh))
                ratio = min(180/fw, 180/fh)
                frame_img = frame_img.resize((max(1, int(fw*ratio)), max(1, int(fh*ratio))),
                                             Image.Resampling.LANCZOS)
                self.preview_image_ref = ImageTk.PhotoImage(frame_img)
                preview_cv.delete("all")
                preview_cv.create_image(100, 100, image=self.preview_image_ref, anchor="center")
            d.after(100, update_preview)

        def save():
            for k, v in rvs.items():
                self.project.player["animations"][k] = {
                    "path": v["path"].get(),
                    "frames": max(1, int(v["frames"].get() or 1)),
                }
            self.project.player["walk_speed"] = sp.get()
            self.project.player["scale"] = sc.get()
            self.refresh_canvas()
            d.destroy()

        tk.Button(d, text="SAVE SETTINGS", command=save, bg="#007acc", fg="white",
                  font=("Segoe UI", 10, "bold"), pady=10).pack(fill=tk.X, padx=20, pady=20)
        update_preview()

    # ─────────────────────────────────────────────
    #  CANVAS RENDERING
    # ─────────────────────────────────────────────

    def draw_player(self, px, py, is_sel):
        scale_val = self.project.player.get("scale", 100) / 100.0
        draw_scale = scale_val * self.view_scale
        anim_data = self.project.player["animations"].get("idle", {"path": "", "frames": 1})
        path = anim_data["path"]
        frames = max(1, anim_data.get("frames", 1))
        if path and os.path.exists(path):
            try:
                img = Image.open(path).convert("RGBA")
                fw, fh = max(1, img.width // frames), max(1, img.height)
                tick = self.anim_tick % frames
                p_img = img.crop((tick * fw, 0, (tick + 1) * fw, fh))
                if self.facing_left:
                    p_img = p_img.transpose(Image.FLIP_LEFT_RIGHT)
                nw, nh = max(1, int(fw * draw_scale)), max(1, int(fh * draw_scale))
                p_img = p_img.resize((nw, nh), Image.Resampling.LANCZOS)
                self.player_image_ref = ImageTk.PhotoImage(p_img)
                self.canvas.create_image(px * self.view_scale, py * self.view_scale,
                                         image=self.player_image_ref, anchor="s")
                self._player_canvas_top = int(py * self.view_scale) - nh
                if is_sel:
                    vs = self.view_scale
                    self.canvas.create_rectangle(
                        (px - (fw*scale_val)/2)*vs, (py - fh*scale_val)*vs,
                        (px + (fw*scale_val)/2)*vs, py*vs,
                        outline="#007acc", width=2)
            except Exception as e:
                self.log(f"[PLAYER IMG ERR] {e}")
                self._draw_player_placeholder(px, py)
        else:
            self._draw_player_placeholder(px, py)

    def _draw_player_placeholder(self, px, py):
        vs = self.view_scale
        if self.player_placeholder_raw:
            scale_val = self.project.player.get("scale", 100) / 100.0
            raw = self.player_placeholder_raw
            rw, rh = raw.size
            target_h = max(1, int(120 * scale_val * vs))
            target_w = max(1, int(rw * target_h / rh))
            img = raw.resize((target_w, target_h), Image.Resampling.LANCZOS)
            self._placeholder_ref = ImageTk.PhotoImage(img)
            self.canvas.create_image(int(px*vs), int(py*vs),
                                      image=self._placeholder_ref, anchor="s")
            self._player_canvas_top = int(py*vs) - target_h
        else:
            self.canvas.create_oval((px-10)*vs, (py-10)*vs,
                                     (px+10)*vs, (py+10)*vs, fill="white")
            self._player_canvas_top = int(py*vs) - 20

    def refresh_canvas(self):
        self.canvas.delete("all")
        if not self.current_room_id:
            return
        room = self.project.rooms[self.current_room_id]
        self._draw_background(room)
        self._draw_walkable_areas(room)
        self._draw_hotpoints(room)
        px, py = self.player_runtime_pos if self.is_playing else room.get("player_pos", [960, 540])
        is_sel = (not self.is_playing
                  and self.selected_object is not None
                  and self.selected_object["type"] == "player")
        self.draw_player(px, py, is_sel)
        if self.is_playing:
            self._draw_effects()
            self._draw_active_dialog()
            self._draw_dialogs(px, py)
            self._draw_inventory()
        if self.temp_points:
            self._draw_temp_polygon()

    def _draw_background(self, room):
        bg = room.get("background")
        if bg and os.path.exists(bg):
            img = Image.open(bg)
            w, h = map(int, self.project.resolution.split('x'))
            self.bg_image_ref = ImageTk.PhotoImage(
                img.resize((int(w * self.view_scale), int(h * self.view_scale))))
            self.canvas.create_image(0, 0, image=self.bg_image_ref, anchor="nw")

    def _draw_walkable_areas(self, room):
        for i, wa in enumerate(room.get("walkable", [])):
            pts = self._wa_pts(wa)
            is_sel = (not self.is_playing
                      and self.selected_object is not None
                      and self.selected_object["type"] == "wa"
                      and self.selected_object["idx"] == i)
            self.canvas.create_polygon(
                [p * self.view_scale for p in pts],
                outline="#00ff00",
                fill="#00ff00" if is_sel else "",
                stipple="gray25" if not is_sel else "",
                width=2)

    def _draw_hotpoints(self, room):
        for i, raw in enumerate(room.get("hotpoints", [])):
            hp = self._as_hp(raw)
            if self.is_playing and hp.id in self.collected_items:
                continue
            act_p = (hp.swap_image_path
                     if (self.is_playing and hp.id in self.swapped_hotpoints and hp.swap_image_path)
                     else hp.image_path)
            if act_p and os.path.exists(act_p):
                h_img = Image.open(act_p).convert("RGBA")
                alpha = h_img.split()[3].point(lambda p: p * (getattr(hp, 'opacity', 100) / 100.0))
                h_img.putalpha(alpha)
                sc = (hp.scale_png / 100.0) * self.view_scale
                h_img = h_img.resize((max(1, int(h_img.width*sc)), max(1, int(h_img.height*sc))),
                                     Image.Resampling.LANCZOS)
                ref = ImageTk.PhotoImage(h_img)
                self.hp_images_refs[f"{hp.id}_{act_p}"] = ref
                self.canvas.create_image(hp.x * self.view_scale, hp.y * self.view_scale,
                                         image=ref, anchor="nw")
            if not self.is_playing:
                is_sel = (self.selected_object is not None
                          and self.selected_object["type"] == "hp"
                          and self.selected_object["idx"] == i)
                vs = self.view_scale
                self.canvas.create_rectangle(
                    hp.x*vs, hp.y*vs, (hp.x+hp.w)*vs, (hp.y+hp.h)*vs,
                    outline="#007acc" if is_sel else "white",
                    width=2 if is_sel else 1)

    def _draw_dialogs(self, px, py):
        if not self.current_room_id:
            return
        w, h = map(int, self.project.resolution.split('x'))
        vs = self.view_scale
        cw, ch = int(w * vs), int(h * vs)
        BOX_W, BOX_H, GAP = 300, 28, 6
        for dg in self.active_dialogs:
            if dg["owner"] == "p":
                cx_px = int(px * vs)
                top_px = getattr(self, '_player_canvas_top', int(py * vs) - 80)
            else:
                gc_x, gc_y = self.get_hp_center(dg["hp_id"])
                cx_px = int(gc_x * vs)
                top_px = int(gc_y * vs)
            box_bottom = top_px - GAP
            box_top = box_bottom - BOX_H
            if box_top < 4:
                box_top = 4
                box_bottom = box_top + BOX_H
            half = BOX_W // 2
            cx_px = max(half + 4, min(cx_px, cw - half - 4))
            self.canvas.create_rectangle(
                cx_px - half, box_top, cx_px + half, box_bottom,
                fill="#111", outline="#444")
            self.canvas.create_text(
                cx_px, (box_top + box_bottom) // 2,
                text=dg["text"], fill="white",
                font=("Segoe UI", 11, "bold"), justify="center", width=BOX_W - 10)

    def _draw_temp_polygon(self):
        st = [p * self.view_scale for p in self.temp_points]
        if len(st) >= 4:
            self.canvas.create_line(st, fill="white", width=2)
        self.canvas.create_oval(st[0]-8, st[1]-8, st[0]+8, st[1]+8, fill="red", outline="white")

    def _draw_effects(self):
        rain = self.game_state.get("rain")
        if not rain:
            return
        w, h = map(int, self.project.resolution.split('x'))
        cw = int(w * self.view_scale)
        ch = int(h * self.view_scale)
        tick = self.anim_tick
        intensity = rain.get("intensity", 1.0)

        # ciemne niebo
        self.canvas.create_rectangle(0, 0, cw, ch,
            fill="#000933", stipple="gray50", outline="")

        # inicjalizacja kropel raz, przy pierwszym renderze
        if "drops" not in rain:
            rng = random.Random(rain.get("seed", 42))
            n = int(160 * intensity)
            rain["drops"] = [
                (rng.randint(-40, w + 40),   # base_x (game coords)
                 rng.uniform(10, 22),          # speed (px/tick)
                 rng.uniform(0, h + 60),       # phase
                 rng.randint(9, 24),           # length
                 rng.uniform(0.18, 0.32))      # angle
                for _ in range(n)
            ]

        color = rain.get("color", "#7fb8e8")
        vs = self.view_scale
        period = h + 60

        for bx, spd, phase, ln, ang in rain["drops"]:
            y = int((tick * spd + phase) % period) - 30
            x = int(bx * vs + y * ang)
            self.canvas.create_line(
                x, int(y * vs),
                x + int(ln * ang * vs), int((y + ln) * vs),
                fill=color, width=1)

        # piorun — flash przez 2 ticki
        lt = self.game_state.get("_lt_tick", -999)
        if tick - lt <= 2:
            stipple = "gray75" if tick - lt == 0 else "gray50"
            self.canvas.create_rectangle(0, 0, cw, ch,
                fill="white", stipple=stipple, outline="")
        elif random.random() < rain.get("lightning_prob", 0.025):
            self.game_state["_lt_tick"] = tick

    def _draw_active_dialog(self):
        if not self.active_dialog:
            return
        did = self.active_dialog["did"]
        nid = self.active_dialog["nid"]
        if not hasattr(self.project, "dialogs") or did not in self.project.dialogs:
            self.active_dialog = None; return
        dlg = self.project.dialogs[did]
        if nid not in dlg["nodes"]:
            self.active_dialog = None; return

        node = dlg["nodes"][nid]
        w, h = map(int, self.project.resolution.split('x'))
        vs = self.view_scale
        cw = int(w * vs)
        ch = int(h * vs)
        phase = self.active_dialog["phase"]

        if phase == "npc":
            speaker = node.get("speaker", "NPC")
            text    = node.get("text", "")
            bw = int(cw * 0.65); bh = 88
            hp_id = dlg.get("hotpoint_id", "")
            if hp_id:
                gc_x, gc_y = self.get_hp_center(hp_id)
                npc_cx = int(gc_x * vs)
                npc_top = int(gc_y * vs)
            else:
                npc_cx = cw // 2
                npc_top = ch
            bx = max(8, min(npc_cx - bw // 2, cw - bw - 8))
            by = max(8, min(npc_top - bh - 12, ch - bh - 8))
            # shadow
            self.canvas.create_rectangle(bx+4, by+4, bx+bw+4, by+bh+4,
                fill="#000", outline="")
            # box
            self.canvas.create_rectangle(bx, by, bx+bw, by+bh,
                fill="#080f1e", outline="#3a7fd4", width=2)
            # speaker badge
            sw = len(speaker) * 7 + 18
            self.canvas.create_rectangle(bx+10, by+7, bx+10+sw, by+25,
                fill="#3a7fd4", outline="")
            self.canvas.create_text(bx+14, by+11, text=speaker,
                fill="white", font=("Segoe UI", 8, "bold"), anchor="nw")
            # text
            self.canvas.create_text(bx+14, by+33, text=text,
                fill="#d0e8ff", font=("Segoe UI", 10), anchor="nw", width=bw-28)
            # progress bar
            dur = node.get("dur", 3.0)
            remaining = max(0.0, self.active_dialog["end_time"] - time.time())
            bar_w = int((1.0 - remaining / max(dur, 0.01)) * (bw - 20))
            self.canvas.create_rectangle(bx+10, by+bh-5, bx+10+bw-20, by+bh-1,
                fill="#0d1c33", outline="")
            self.canvas.create_rectangle(bx+10, by+bh-5, bx+10+bar_w, by+bh-1,
                fill="#3a7fd4", outline="")
            # auto-advance
            if time.time() >= self.active_dialog["end_time"]:
                choices = [cid for cid in node.get("choices", []) if cid in dlg["nodes"]]
                if choices:
                    self.active_dialog["phase"] = "choices"
                    self.active_dialog["choice_rects"] = []
                else:
                    nxt = node.get("next", "")
                    if nxt and nxt in dlg["nodes"]:
                        self._advance_dialog(nxt)
                    else:
                        self.active_dialog = None

        elif phase == "choices":
            choices = [cid for cid in node.get("choices", []) if cid in dlg["nodes"]]
            bw = int(cw * 0.55); bh = 38; gap = 6
            total_h = len(choices) * (bh + gap)
            px_r, py_r = self.player_runtime_pos
            cx_px = int(px_r * vs)
            player_top = getattr(self, '_player_canvas_top', int(py_r * vs) - 80)
            by_base = player_top - total_h - 14
            by_base = max(8, min(by_base, ch - total_h - 8))
            bx = max(8, min(cx_px - bw // 2, cw - bw - 8))
            rects = []
            for i, cid in enumerate(choices):
                cn = dlg["nodes"][cid]
                ry1 = by_base + i * (bh + gap); ry2 = ry1 + bh
                self.canvas.create_rectangle(bx+3, ry1+3, bx+bw+3, ry2+3,
                    fill="#000", outline="")
                self.canvas.create_rectangle(bx, ry1, bx+bw, ry2,
                    fill="#091a0f", outline="#3aad6a", width=2)
                self.canvas.create_text(bx+14, ry1 + bh // 2,
                    text=f"▶  {cn.get('text','...')}",
                    fill="#88f0a8", font=("Segoe UI", 9), anchor="w", width=bw-28)
                rects.append({"cid": cid, "x1": bx, "y1": ry1, "x2": bx+bw, "y2": ry2})
            self.active_dialog["choice_rects"] = rects

    def _advance_dialog(self, nid):
        did = self.active_dialog["did"]
        dlg = self.project.dialogs[did]
        node = dlg["nodes"][nid]
        give = node.get("give_item", "")
        if give:
            self.log(f"[ITEM] Otrzymano: {give}")
        self.active_dialog = {
            "did": did, "nid": nid, "phase": "npc",
            "end_time": time.time() + node.get("dur", 3.0),
            "choice_rects": [],
        }

    def _select_dialog_choice(self, cid):
        if not self.active_dialog: return
        did = self.active_dialog["did"]
        dlg = self.project.dialogs[did]
        cn = dlg["nodes"].get(cid)
        if not cn: return
        give = cn.get("give_item", "")
        if give:
            self.log(f"[ITEM] Otrzymano: {give}")
        nxt = cn.get("next", "")
        if nxt and nxt in dlg["nodes"]:
            self._advance_dialog(nxt)
        else:
            self.active_dialog = None

    def get_hp_center(self, hp_id):
        room = self.project.rooms[self.current_room_id]
        for hp in room["hotpoints"]:
            hp_obj = self._as_hp(hp)
            if hp_obj.id == hp_id:
                return (hp_obj.x + hp_obj.w // 2, hp_obj.y)
        return (0, 0)

    def set_mode(self, mode):
        self.mode = mode
        for m, btn in self.tool_btns.items():
            active = (m == mode)
            btn.config(image=self.icons_ui.get(f"{m}_light" if active else f"{m}_dark"),
                       fg="#ffffff" if active else "#555")

    # ─────────────────────────────────────────────
    #  UNDO
    # ─────────────────────────────────────────────

    def save_undo(self):
        if self.project:
            self.undo_stack.append(copy.deepcopy(self.project.rooms))
        if len(self.undo_stack) > 15:
            self.undo_stack.pop(0)

    def undo(self, event=None):
        if self.undo_stack:
            self.project.rooms = self.undo_stack.pop()
            self.refresh_obj_tree()
            self.refresh_canvas()

    # ─────────────────────────────────────────────
    #  ROOM & OBJECT MANAGEMENT
    # ─────────────────────────────────────────────

    def on_room_selected(self, e):
        sel = self.room_listbox.curselection()
        self.current_room_id = list(self.project.rooms.keys())[sel[0]] if sel else None
        self.refresh_obj_tree()
        self.refresh_canvas()

    def add_room(self):
        n = simpledialog.askstring("Nowa scena", "Nazwa sceny:", initialvalue="new_room")
        if not n:
            return
        rid = f"r_{int(time.time())}"
        self.project.rooms[rid] = {
            "name": n, "background": "",
            "hotpoints": [], "walkable": [], "player_pos": [960, 540],
        }
        self.refresh_room_list()
        self.room_listbox.select_set(tk.END)
        self.on_room_selected(None)

    def refresh_room_list(self):
        self.room_listbox.delete(0, tk.END)
        for r in self.project.rooms.values():
            self.room_listbox.insert(tk.END, r["name"])

    def refresh_obj_tree(self):
        self.obj_tree.delete(*self.obj_tree.get_children())
        if not self.current_room_id:
            return
        r = self.project.rooms[self.current_room_id]
        for i, wa in enumerate(r.get("walkable", [])):
            self.obj_tree.insert("", "end", iid=f"wa_{i}", text=f"Area {i+1}")
        for i, hp in enumerate(r.get("hotpoints", [])):
            self.obj_tree.insert("", "end", iid=f"hp_{i}", text=self._as_hp(hp).id)

    def on_obj_tree_select(self, e):
        sel = self.obj_tree.selection()
        if not sel:
            return
        sid = sel[0]
        self.selected_object = {"type": "wa" if sid.startswith("wa_") else "hp", "idx": int(sid[3:])}
        self.refresh_canvas()

    def on_obj_tree_double_click(self, e):
        sel = self.obj_tree.selection()
        sid = sel[0] if sel else ""
        if sid.startswith("hp_"):
            raw = self.project.rooms[self.current_room_id]["hotpoints"][int(sid[3:])]
            self.open_hp_settings(self._as_hp(raw))

    def on_obj_tree_right_click(self, event):
        iid = self.obj_tree.identify_row(event.y)
        if not iid:
            return
        self.obj_tree.selection_set(iid)
        self.on_obj_tree_select(None)
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="🗑 Delete Object", command=self.delete_selected)
        m.post(event.x_root, event.y_root)

    def delete_selected(self, e=None):
        if not self.selected_object or not self.current_room_id:
            return
        self.save_undo()
        r = self.project.rooms[self.current_room_id]
        t = self.selected_object["type"]
        idx = self.selected_object["idx"]
        if t == "hp":
            del r["hotpoints"][idx]
        elif t == "wa":
            del r["walkable"][idx]
        self.selected_object = None
        self.refresh_obj_tree()
        self.refresh_canvas()

    def finish_polygon(self):
        if len(self.temp_points) < 6:
            return
        room = self.project.rooms[self.current_room_id]
        try:
            new_poly = Polygon([(self.temp_points[i], self.temp_points[i+1])
                                for i in range(0, len(self.temp_points), 2)])
            polys = []
            for p in room["walkable"]:
                pts = self._wa_pts(p)
                polys.append(Polygon([(pts[j], pts[j+1]) for j in range(0, len(pts), 2)]))
            merged = unary_union([new_poly] + polys)
            room["walkable"] = []
            if merged.geom_type == "Polygon":
                self.add_shapely_poly(merged)
            elif merged.geom_type == "MultiPolygon":
                for poly in merged.geoms:
                    self.add_shapely_poly(poly)
        except Exception:
            room["walkable"].append(WalkableArea(id=f"wa_{int(time.time())}", points=self.temp_points[:]))
        self.temp_points = []
        self.refresh_canvas()
        self.refresh_obj_tree()

    def add_shapely_poly(self, poly):
        pts = []
        for x, y in poly.exterior.coords:
            pts.extend([int(x), int(y)])
        self.project.rooms[self.current_room_id]["walkable"].append(
            WalkableArea(id=f"wa_{int(time.time())}", points=pts))

    # ─────────────────────────────────────────────
    #  PROJECT I/O
    # ─────────────────────────────────────────────

    def new_project_dialog(self):
        if self.project and not messagebox.askyesno(
                "Nowy projekt", "Bieżący projekt zostanie zamknięty bez zapisania. Kontynuować?"):
            return
        d = tk.Toplevel(self.root)
        d.title("Nowy projekt")
        d.configure(bg="#1e1e1e")
        d.grab_set()
        d.transient(self.root)
        tk.Label(d, text="Nazwa projektu:", bg="#1e1e1e", fg="white").pack(padx=20, pady=(15, 2))
        ne = tk.Entry(d, bg="#121212", fg="white", insertbackground="white")
        ne.insert(0, "new project"); ne.pack(padx=20)
        ne.select_range(0, tk.END); ne.focus_set()
        tk.Label(d, text="Rozdzielczość:", bg="#1e1e1e", fg="white").pack(padx=20, pady=(10, 2))
        rv = tk.StringVar(value="1920x1080")
        ttk.Combobox(d, textvariable=rv, values=["1920x1080", "1280x720"],
                     state="readonly").pack(padx=20)

        def create():
            self.project = GamifikatorProject(ne.get(), rv.get())
            self.init_workspace()
            d.destroy()

        tk.Button(d, text="UTWÓRZ", command=create,
                  bg="#007acc", fg="white", relief=tk.FLAT,
                  font=("Segoe UI", 10, "bold")).pack(fill=tk.X, padx=20, pady=15)

    def init_workspace(self):
        if not self.project:
            return
        w, h = map(int, self.project.resolution.split("x"))
        self.view_scale = min(1100/w, 750/h)
        self.canvas.config(width=int(w * self.view_scale), height=int(h * self.view_scale))
        self.refresh_room_list()
        self.refresh_canvas()

    def save_project(self):
        if not self.project:
            return
        p = filedialog.asksaveasfilename(defaultextension=".phx",
                                         filetypes=[("PHX Project", "*.phx")])
        if not p:
            return
        with open(p, 'w', encoding='utf-8') as f:
            f.write(self.project.to_json())
        self.log(f"Zapisano: {p}")

    def open_project(self):
        p = filedialog.askopenfilename(filetypes=[("PHX Project", "*.phx")])
        if not p:
            return
        with open(p, 'r', encoding='utf-8') as f:
            self.project = GamifikatorProject.from_json(f.read())
        for r in self.project.rooms.values():
            r["hotpoints"] = [self._as_hp(h) for h in r["hotpoints"]]
            r["walkable"]  = [WalkableArea(**w) if isinstance(w, dict) else w for w in r["walkable"]]
        self.init_workspace()
        self.room_listbox.select_set(0)
        self.on_room_selected(None)
        self.log(f"Otwarto: {p}")

    def select_background(self):
        p = filedialog.askopenfilename()
        if p:
            self.project.rooms[self.current_room_id]["background"] = p
            self.refresh_canvas()

    def rename_room(self):
        if not self.current_room_id:
            return
        room = self.project.rooms[self.current_room_id]
        n = simpledialog.askstring("Zmień nazwę sceny", "Nowa nazwa:",
                                   initialvalue=room["name"])
        if n:
            room["name"] = n
            self.refresh_room_list()

    def _on_close(self):
        if self.project and not messagebox.askyesno(
                "Wyjście", "Projekt nie został zapisany. Wyjść bez zapisywania?"):
            return
        self.root.destroy()

    def _show_wrong_item(self, hp):
        msgs = getattr(self.project, 'wrong_item_msgs', [
            "To nie jest właściwy przedmiot.",
            "Potrzebuję czegoś innego.",
            "Hmm... nie sądzę.",
        ])
        msg = random.choice(msgs) if msgs else "Nie."
        self.active_dialogs.clear()
        self.active_dialogs.append({
            "text": msg, "owner": "p", "hp_id": hp.id,
            "end": time.time() + 2.5,
        })

    def _pick_from_anim_lib(self, parent, callback):
        anims = getattr(self.project, "animations", {})
        if not anims:
            self._toast("Brak animacji w bibliotece ANIMATORATORA.", "warn")
            return
        win = tk.Toplevel(parent)
        win.title("Biblioteka Animatoratora — wybierz")
        win.configure(bg="#0d0d0d")
        win.transient(parent)
        win.grab_set()
        tk.Label(win, text="WYBIERZ ANIMACJĘ", bg="#0d0d0d", fg="#9B59B6",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
        cv = tk.Canvas(win, bg="#121212", highlightthickness=0)
        vsb = tk.Scrollbar(win, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        cv.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        grid_f = tk.Frame(cv, bg="#121212")
        cv.create_window((0, 0), window=grid_f, anchor="nw")
        grid_f.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<MouseWheel>", lambda e: cv.yview_scroll(int(-1*(e.delta/120)), "units"))
        win._refs = {}
        COLS = 4
        for i, (aid, anim) in enumerate(anims.items()):
            col, row_n = i % COLS, i // COLS
            cell = tk.Frame(grid_f, bg="#1a1a1a", padx=4, pady=4, cursor="hand2")
            cell.grid(row=row_n, column=col, padx=5, pady=5)
            thumb_ref = None
            try:
                sp = anim.get("sheet_path", "")
                if sp and os.path.exists(sp):
                    img_p = Image.open(sp).convert("RGBA")
                    fw = max(1, anim.get("frame_w", img_p.width))
                    fh = max(1, anim.get("frame_h", img_p.height))
                    first = img_p.crop((0, 0, fw, fh))
                    bg_t = Image.new("RGBA", (84, 84), (30, 30, 30, 255))
                    first.thumbnail((80, 80), Image.Resampling.LANCZOS)
                    ox2 = (84 - first.width) // 2
                    oy2 = 84 - first.height - 2
                    bg_t.paste(first, (ox2, max(0, oy2)), first)
                    thumb_ref = ImageTk.PhotoImage(bg_t)
                    win._refs[aid] = thumb_ref
            except Exception:
                pass
            def make_cmd(a=aid):
                def cmd():
                    callback(a); win.destroy()
                return cmd
            if thumb_ref:
                tk.Button(cell, image=thumb_ref, bg="#252526", activebackground="#7B2FBE",
                          relief=tk.FLAT, bd=0, command=make_cmd()).pack()
            else:
                tk.Button(cell, text="?", bg="#333", fg="#888", width=6, height=4,
                          relief=tk.FLAT, command=make_cmd()).pack()
            tk.Label(cell, text=anim.get("name", "")[:14], bg="#1a1a1a", fg="#ccc",
                     font=("Segoe UI", 7), wraplength=90).pack()
            tk.Label(cell, text=f"{anim.get('frames','?')} kl · {anim.get('frame_w','?')}×{anim.get('frame_h','?')}",
                     bg="#1a1a1a", fg="#555", font=("Segoe UI", 6)).pack()
        win.update_idletasks()
        cols_used = min(len(anims), COLS)
        w = max(240, cols_used * 102 + 30)
        rows_used = (len(anims) + COLS - 1) // COLS
        h = min(520, rows_used * 115 + 80)
        win.geometry(f"{w}x{h}")

    def _draw_inventory(self):
        if not self.player_inventory:
            return
        vs = self.view_scale
        x0, y0 = 10, 10
        self.canvas.create_rectangle(x0, y0, x0 + 160, y0 + 26,
                                      fill="#0d0d0d", outline="#444")
        self.canvas.create_text(x0 + 6, y0 + 4, text="🎒", font=("Segoe UI", 9),
                                 fill="#f1c40f", anchor="nw")
        items_txt = "  ".join(self.player_inventory[-5:])
        self.canvas.create_text(x0 + 26, y0 + 5, text=items_txt,
                                 fill="#f1c40f", font=("Segoe UI", 8),
                                 anchor="nw", width=128)


if __name__ == "__main__":
    root = tk.Tk()
    app = GamifikatorEditor(root)
    root.mainloop()
