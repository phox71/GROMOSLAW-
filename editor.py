import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import os
import time
import math
import copy
from PIL import Image, ImageTk
from shapely.geometry import Polygon
from shapely.ops import unary_union
from engine_data import Hotpoint, WalkableArea, GamifikatorProject

class GamifikatorEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("GAMIFIKATOR 2026 - v1.2 [ULTIMATE STABLE]")
        self.root.geometry("1600x950")
        self.root.configure(bg="#121212")
        
        self.project = None
        self.current_room_id = None
        self.mode = "Select"
        
        # State & Undo
        self.undo_stack = []
        self.temp_points = []
        self.selected_object = None 
        self.drag_data = {"x": 0, "y": 0, "obj": None, "mode": None}
        self.view_scale = 1.0
        
        # Assets refs
        self.bg_image_ref = None
        self.player_image_ref = None
        self.icons_ui = {}
        self.player_placeholder_raw = None
        self.log_history = []
        
        self.load_ui_assets()
        self.setup_ui()
        self.setup_canvas_events()
        self.log("Gamifikator v1.2 gotowy. Wszystkie systemy przywrócone.")

    def save_undo(self):
        if not self.project: return
        # Snapshot of the current rooms state
        snapshot = copy.deepcopy(self.project.rooms)
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > 10: self.undo_stack.pop(0)

    def undo(self, event=None):
        if len(self.undo_stack) > 0:
            self.project.rooms = self.undo_stack.pop()
            self.refresh_obj_tree()
            self.refresh_canvas()
            self.log("Cofnięto zmianę (Undo).")

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.log_history.append(entry)
        if hasattr(self, 'log_text'):
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, entry + "\n")
            self.log_text.see(tk.END); self.log_text.config(state=tk.DISABLED)

    def load_ui_assets(self):
        paths = {"Select": r"C:\Users\rafal\Downloads\choose.png", "Walkable": r"C:\Users\rafal\Downloads\square.png", 
                 "Hotpoint": r"C:\Users\rafal\Downloads\double-tap.png", "Edit": r"C:\Users\rafal\Downloads\edit.png",
                 "Player": r"C:\Users\rafal\Downloads\walk.png"}
        for name, path in paths.items():
            if os.path.exists(path):
                img = Image.open(path).convert("RGBA")
                if name == "Player": self.player_placeholder_raw = self.tint_image(img, "#ffffff")
                else:
                    ui_img = img.resize((24, 24), Image.Resampling.LANCZOS)
                    self.icons_ui[f"{name}_dark"] = ImageTk.PhotoImage(self.tint_image(ui_img, "#555555"))
                    self.icons_ui[f"{name}_light"] = ImageTk.PhotoImage(self.tint_image(ui_img, "#ffffff"))
                    self.icons_ui[f"{name}_small"] = ImageTk.PhotoImage(self.tint_image(img.resize((16, 16)), "#ffffff"))

    def tint_image(self, image, color):
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        source = image.split(); R, G, B, A = 0, 1, 2, 3
        return Image.merge("RGBA", (source[R].point(lambda i: r), source[G].point(lambda i: g), source[B].point(lambda i: b), source[A]))

    def setup_ui(self):
        # Toolbar
        self.toolbar = tk.Frame(self.root, bg="#1e1e1e", height=50); self.toolbar.pack(side=tk.TOP, fill=tk.X)
        btn_s = {"bg": "#1e1e1e", "fg": "#eee", "relief": tk.FLAT, "font": ("Segoe UI", 9)}
        tk.Button(self.toolbar, text="PROJECT", command=self.new_project_dialog, **btn_s).pack(side=tk.LEFT, padx=10)
        tk.Button(self.toolbar, text="OPEN", command=self.open_project, **btn_s).pack(side=tk.LEFT, padx=10)
        tk.Button(self.toolbar, text="SAVE", command=self.save_project, **btn_s).pack(side=tk.LEFT, padx=10)
        
        # Main Split
        self.main_pane = tk.PanedWindow(self.root, orient=tk.VERTICAL, bg="#121212", sashwidth=4)
        self.main_pane.pack(fill=tk.BOTH, expand=True)
        self.workspace_frame = tk.Frame(self.main_pane, bg="#121212"); self.main_pane.add(self.workspace_frame, stretch="always")

        # Toolbox (Left)
        self.tool_frame = tk.Frame(self.workspace_frame, bg="#1e1e1e", width=80); self.tool_frame.pack(side=tk.LEFT, fill=tk.Y, padx=1)
        self.tool_btns = {}
        for m in ["Select", "Walkable", "Hotpoint"]:
            btn = tk.Button(self.tool_frame, image=self.icons_ui.get(f"{m}_dark"), bg="#1e1e1e", relief=tk.FLAT, command=lambda mode=m: self.set_mode(mode))
            btn.pack(pady=(15, 0), padx=10); tk.Label(self.tool_frame, text=m.upper(), bg="#1e1e1e", fg="#555", font=("Segoe UI", 7, "bold")).pack()
            self.tool_btns[m] = btn

        # Sidebar (Right)
        self.sidebar = tk.Frame(self.workspace_frame, bg="#1e1e1e", width=350); self.sidebar.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Label(self.sidebar, text="AVATAR", bg="#2d2d2d", fg="#aaa", font=("Segoe UI", 8, "bold"), pady=5).pack(fill=tk.X)
        tk.Button(self.sidebar, text="CONFIGURE AVATAR", command=self.open_player_settings, bg="#007acc", fg="white", relief=tk.FLAT).pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(self.sidebar, text="SCENES", bg="#2d2d2d", fg="#aaa", font=("Segoe UI", 8, "bold"), pady=5).pack(fill=tk.X, pady=(10,0))
        self.room_listbox = tk.Listbox(self.sidebar, bg="#121212", fg="#ddd", borderwidth=0, height=5); self.room_listbox.pack(fill=tk.X, padx=10, pady=5); self.room_listbox.bind("<<ListboxSelect>>", self.on_room_selected)
        tk.Button(self.sidebar, text="+ NEW SCENE", command=self.add_room, bg="#333", fg="white", relief=tk.FLAT).pack(fill=tk.X, padx=10)

        tk.Label(self.sidebar, text="OBJECTS", bg="#2d2d2d", fg="#aaa", font=("Segoe UI", 8, "bold"), pady=5).pack(fill=tk.X, pady=(15, 0))
        self.obj_tree = ttk.Treeview(self.sidebar, show="tree", height=10); self.obj_tree.pack(fill=tk.X, padx=10, pady=5); self.obj_tree.bind("<<TreeviewSelect>>", self.on_obj_tree_select)
        
        tk.Label(self.sidebar, text="PROPERTIES", bg="#2d2d2d", fg="#aaa", font=("Segoe UI", 8, "bold"), pady=5).pack(fill=tk.X, pady=(15, 0))
        self.prop_container = tk.Frame(self.sidebar, bg="#1e1e1e"); self.prop_container.pack(fill=tk.BOTH, expand=True, padx=10)
        self.setup_properties_ui()

        # Canvas Area
        self.cv_area = tk.Frame(self.workspace_frame, bg="#121212"); self.cv_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.warning_bar = tk.Label(self.cv_area, text="", bg="#8b0000", fg="white", font=("Segoe UI", 9, "bold")); self.warning_bar.pack(fill=tk.X)
        self.canvas = tk.Canvas(self.cv_area, bg="#000", highlightthickness=0); self.canvas.pack(expand=True)

        # Console Panel
        self.con_frame = tk.Frame(self.main_pane, bg="#1e1e1e", height=120); self.main_pane.add(self.con_frame, stretch="never")
        log_h = tk.Frame(self.con_frame, bg="#2d2d2d"); log_h.pack(fill=tk.X)
        tk.Label(log_h, text="CONSOLE LOGS", bg="#2d2d2d", fg="#888", font=("Segoe UI", 7, "bold")).pack(side=tk.LEFT, padx=10)
        self.log_text = tk.Text(self.con_frame, bg="#000", fg="#00ff00", font=("Consolas", 9), state=tk.DISABLED, borderwidth=0); self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_properties_ui(self):
        self.room_props_f = tk.Frame(self.prop_container, bg="#1e1e1e")
        tk.Button(self.room_props_f, text="SET BACKGROUND PNG", command=self.select_background, bg="#007acc", fg="white", relief=tk.FLAT).pack(fill=tk.X, pady=5)
        
        self.wa_props_f = tk.Frame(self.prop_container, bg="#1e1e1e")
        self.scale_min = tk.Scale(self.wa_props_f, from_=10, to=200, orient=tk.HORIZONTAL, label="MIN Y %", bg="#1e1e1e", fg="white"); self.scale_min.pack(fill=tk.X)
        self.scale_max = tk.Scale(self.wa_props_f, from_=10, to=200, orient=tk.HORIZONTAL, label="MAX Y %", bg="#1e1e1e", fg="white"); self.scale_max.pack(fill=tk.X)
        tk.Button(self.wa_props_f, text="SAVE SCALING", command=self.save_wa_params, bg="#007acc", fg="white", relief=tk.FLAT).pack(fill=tk.X, pady=10)

        self.hp_props_f = tk.Frame(self.prop_container, bg="#1e1e1e")
        tk.Button(self.hp_props_f, text="EDIT SETTINGS ⚙", command=lambda: self.open_hp_settings(None), bg="#333", fg="white", relief=tk.FLAT, pady=10).pack(fill=tk.X)

    def open_player_settings(self):
        d = tk.Toplevel(self.root); d.title("Avatar Config"); d.geometry("600x750"); d.configure(bg="#1e1e1e"); d.grab_set()
        def row(k):
            f = tk.Frame(d, bg="#252526", pady=5); f.pack(fill=tk.X, padx=20, pady=2)
            tk.Label(f, text=k.upper(), width=10, bg="#252526", fg="white").pack(side=tk.LEFT)
            v = tk.StringVar(value=self.project.player["animations"].get(k, {}).get("path", ""))
            tk.Entry(f, textvariable=v, bg="#121212", fg="white").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            tk.Button(f, text="...", command=lambda: v.set(filedialog.askopenfilename() or v.get())).pack(side=tk.LEFT)
            fv = tk.BooleanVar(value=self.project.player["animations"].get(k, {}).get("flip", False))
            tk.Checkbutton(f, text="FLIP", variable=fv, bg="#252526", fg="white", selectcolor="#000").pack(side=tk.LEFT, padx=5); return v, fv
        rows = {k: row(k) for k in ["idle", "walk_r", "walk_u", "walk_d"]}
        tk.Label(d, text="SCALE %").pack(); sc_s = tk.Scale(d, from_=10, to=200, orient=tk.HORIZONTAL); sc_s.set(self.project.player.get("scale", 100)); sc_s.pack(fill=tk.X, padx=30)
        tk.Label(d, text="SPEED").pack(); sp_s = tk.Scale(d, from_=1, to=30, orient=tk.HORIZONTAL); sp_s.set(self.project.player.get("walk_speed", 5)); sp_s.pack(fill=tk.X, padx=30)
        def save():
            self.save_undo()
            for k, (v, fv) in rows.items(): self.project.player["animations"][k] = {"path": v.get(), "flip": fv.get()}
            self.project.player["scale"], self.project.player["walk_speed"] = sc_s.get(), sp_s.get()
            if self.current_room_id and "player_pos" not in self.project.rooms[self.current_room_id]: self.project.rooms[self.current_room_id]["player_pos"] = [500, 500]
            self.refresh_canvas(); d.destroy()
        tk.Button(d, text="SAVE", command=save, bg="#007acc", fg="white", pady=15).pack(fill=tk.X, padx=30, pady=20)

    def on_canvas_down(self, event):
        if not self.current_room_id: return
        x, y = int(event.x / self.view_scale), int(event.y / self.view_scale); room = self.project.rooms[self.current_room_id]
        if self.mode == "Select":
            if "player_pos" in room:
                px, py = room["player_pos"]; s = self.project.player.get("scale", 100)/100.0
                if px-50*s <= x <= px+50*s and py-120*s <= y <= py:
                    self.drag_data = {"mode": "move_player", "obj": room, "off_x": x-px, "off_y": y-py}; self.selected_object = {"type": "player"}; return
            for i, hp in enumerate(reversed(room["hotpoints"])):
                real_idx = len(room["hotpoints"]) - 1 - i
                if hp.x+hp.w-15 <= x <= hp.x+hp.w+10 and hp.y+hp.h-15 <= y <= hp.y+hp.h+10:
                    self.drag_data = {"mode": "resize", "obj": hp, "start_w": hp.w, "start_h": hp.h, "start_x": x, "start_y": y}
                    self.selected_object = {"type": "hp", "idx": real_idx}; self.show_props("hp"); return
                if hp.x <= x <= hp.x+hp.w and hp.y <= y <= hp.y+hp.h:
                    self.drag_data = {"mode": "move", "obj": hp, "off_x": x - hp.x, "off_y": y - hp.y}
                    self.selected_object = {"type": "hp", "idx": real_idx}; self.show_props("hp"); self.refresh_canvas(); return
            for i, wa in enumerate(room["walkable"]):
                if min(wa.points[0::2]) <= x <= max(wa.points[0::2]) and min(wa.points[1::2]) <= y <= max(wa.points[1::2]):
                    self.selected_object = {"type": "wa", "idx": i}; self.show_props("wa"); self.refresh_canvas(); return
            self.selected_object = None; self.show_props("room"); self.refresh_canvas()
        elif self.mode == "Hotpoint":
            self.save_undo()
            new_hp = Hotpoint(id=f"hotpoint_{len(room['hotpoints'])+1}", x=x, y=y, w=10, h=10)
            room["hotpoints"].append(new_hp); self.selected_object = {"type": "hp", "idx": len(room["hotpoints"])-1}
            self.drag_data = {"mode": "resize", "obj": new_hp, "start_w": 0, "start_h": 0, "start_x": x, "start_y": y}
            self.refresh_canvas(); self.refresh_obj_tree()
        elif self.mode == "Walkable":
            if self.temp_points and math.sqrt((x-self.temp_points[0])**2 + (y-self.temp_points[1])**2) < 15: self.finish_polygon(); return
            self.temp_points.extend([x, y]); self.refresh_canvas()

    def on_canvas_drag(self, event):
        if not self.drag_data["obj"]: return
        x, y = int(event.x / self.view_scale), int(event.y / self.view_scale); o = self.drag_data["obj"]
        if self.drag_data["mode"] == "move_player": o["player_pos"] = [x - self.drag_data["off_x"], y - self.drag_data["off_y"]]
        elif self.drag_data["mode"] == "move": o.x, o.y = x - self.drag_data["off_x"], y - self.drag_data["off_y"]
        elif self.drag_data["mode"] == "resize": o.w, o.h = max(10, self.drag_data["start_w"] + (x - self.drag_data["start_x"])), max(10, self.drag_data["start_h"] + (y - self.drag_data["start_y"]))
        self.refresh_canvas()

    def finish_polygon(self):
        if len(self.temp_points) >= 6:
            self.save_undo()
            new_pts = self.temp_points[:]; room = self.project.rooms[self.current_room_id]
            try:
                new_poly = Polygon([(new_pts[i], new_pts[i+1]) for i in range(0, len(new_pts), 2)])
                existing = [Polygon([(wa.points[j], wa.points[j+1]) for j in range(0, len(wa.points), 2)]) for wa in room["walkable"]]
                merged = unary_union([new_poly] + existing)
                room["walkable"] = []
                if merged.geom_type == 'Polygon': self.add_shapely_poly(merged)
                elif merged.geom_type == 'MultiPolygon': 
                    for p in merged.geoms: self.add_shapely_poly(p)
            except: room["walkable"].append(WalkableArea(id=f"wa_{int(time.time())}", points=new_pts))
            self.temp_points = []; self.refresh_canvas(); self.refresh_obj_tree()

    def add_shapely_poly(self, poly):
        pts = []; [pts.extend([int(x), int(y)]) for x, y in poly.exterior.coords]
        self.project.rooms[self.current_room_id]["walkable"].append(WalkableArea(id=f"wa_{int(time.time())}", points=pts))

    def refresh_canvas(self):
        self.canvas.delete("all")
        if not self.current_room_id: return
        room = self.project.rooms[self.current_room_id]
        if room["background"] and os.path.exists(room["background"]):
            img = Image.open(room["background"]); w, h = map(int, self.project.resolution.split('x'))
            self.bg_image_ref = ImageTk.PhotoImage(img.resize((int(w*self.view_scale), int(h*self.view_scale)))); self.canvas.create_image(0, 0, image=self.bg_image_ref, anchor="nw")
        for i, wa in enumerate(room["walkable"]):
            is_sel = (self.selected_object and self.selected_object["type"] == "wa" and self.selected_object["idx"] == i)
            self.canvas.create_polygon([p*self.view_scale for p in wa.points], outline="#00ff00", fill="#00ff00" if is_sel else "", stipple="gray25", width=3)
        if self.temp_points:
            s_t = [p*self.view_scale for p in self.temp_points]
            if len(s_t)>=4: self.canvas.create_line(s_t, fill="white", width=2)
            self.canvas.create_oval(s_t[0]-5, s_t[1]-5, s_t[0]+5, s_t[1]+5, fill="red")
        if "player_pos" in room:
            px, py = room["player_pos"]; is_sel = (self.selected_object and self.selected_object["type"] == "player")
            p_img = self.player_placeholder_raw; idle = self.project.player["animations"].get("idle", {}).get("path", "")
            if idle and os.path.exists(idle): p_img = Image.open(idle).convert("RGBA")
            if p_img:
                scale = self.project.player.get("scale", 100) / 100.0
                p_img = p_img.resize((int(100*scale), int(100*scale)), Image.Resampling.LANCZOS)
                self.player_image_ref = ImageTk.PhotoImage(p_img); self.canvas.create_image(px*self.view_scale, py*self.view_scale, image=self.player_image_ref, anchor="s")
                if is_sel: self.canvas.create_rectangle((px-50*scale)*self.view_scale, (py-100*scale)*self.view_scale, (px+50*scale)*self.view_scale, py*self.view_scale, outline="#007acc", width=2)
        for i, hp in enumerate(room["hotpoints"]):
            is_sel = (self.selected_object and self.selected_object["type"] == "hp" and self.selected_object["idx"] == i)
            x1, y1, x2, y2 = hp.x*self.view_scale, hp.y*self.view_scale, (hp.x+hp.w)*self.view_scale, (hp.y+hp.h)*self.view_scale
            self.canvas.create_rectangle(x1, y1, x2, y2, outline="#007acc" if is_sel else "white", width=3 if is_sel else 1)
            if is_sel: self.canvas.create_rectangle(x2-15, y2-15, x2, y2, fill="white"); self.canvas.create_text(x2-10, y1+10, text="⚙", fill="white", font=("Arial", 14, "bold"))

    def open_hp_settings(self, hp=None):
        if not hp and self.selected_object and self.selected_object["type"] == "hp":
            hp = self.project.rooms[self.current_room_id]["hotpoints"][self.selected_object["idx"]]
        if not hp: return
        d = tk.Toplevel(self.root); d.title(f"Hotpoint: {hp.id}"); d.geometry("500x850"); d.grab_set(); d.configure(bg="#1e1e1e")
        def lbl(t): tk.Label(d, text=t, bg="#1e1e1e", fg="#C4A35A", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20, pady=(10,0))
        lbl("ACTION TYPE")
        act_v = tk.StringVar(value=hp.action); tk.OptionMenu(d, act_v, "comment", "pick_up", "talk_to", "lock", "move_to").pack(fill=tk.X, padx=20)
        lbl("ITEM REQUIRED")
        item_v = tk.StringVar(value=hp.item_req); tk.OptionMenu(d, item_v, "(none)", *self.project.items.keys()).pack(fill=tk.X, padx=20)
        lbl("FLOW")
        f_chk = tk.Frame(d, bg="#252526"); f_chk.pack(fill=tk.X, padx=20, pady=5)
        chk_vars = {}
        for k, t in [("p_com", "Player Comment"), ("h_com", "Hotpoint Comment"), ("unlock", "Unlock LOCK"), ("swap", "Swap PNG"), ("move", "Change Room")]:
            v = tk.BooleanVar(value=hp.flow.get(k, False)); tk.Checkbutton(f_chk, text=t, variable=v, bg="#252526", fg="#ccc").pack(anchor="w"); chk_vars[k]=v
        lbl("COMMENTS (+ Add Line)")
        com_f = tk.Frame(d, bg="#121212"); com_f.pack(fill=tk.BOTH, expand=True, padx=20)
        def add_com(t=""): 
            r = tk.Frame(com_f, bg="#121212"); r.pack(fill=tk.X, pady=1); e = tk.Entry(r, bg="#1e1e1e", fg="white"); e.insert(0, t); e.pack(side=tk.LEFT, fill=tk.X, expand=True)
            tk.Button(r, text="X", command=r.destroy).pack(side=tk.RIGHT)
        tk.Button(d, text="+ ADD COMMENT", command=add_com).pack()
        for c in hp.comments: add_com(c)
        def save():
            self.save_undo()
            hp.action, hp.item_req = act_v.get(), item_v.get()
            hp.flow = {k: v.get() for k, v in chk_vars.items()}
            hp.comments = [w.winfo_children()[0].get() for w in com_f.winfo_children()]
            self.refresh_canvas(); d.destroy()
        tk.Button(d, text="SAVE ALL", command=save, bg="#007acc", fg="white", pady=15).pack(fill=tk.X, padx=20, pady=20)

    def set_mode(self, mode):
        self.mode = mode; self.temp_points = []; self.refresh_canvas()
        for m, btn in self.tool_btns.items(): btn.config(image=self.icons_ui.get(f"{m}_light") if m == mode else self.icons_ui.get(f"{m}_dark"))
    def on_room_selected(self, e):
        sel = self.room_listbox.curselection()
        if sel: self.current_room_id = list(self.project.rooms.keys())[sel[0]]; self.refresh_obj_tree(); self.refresh_canvas()
    def add_room(self):
        n = simpledialog.askstring("Name", "Scene Name:")
        if n: rid = f"room_{int(time.time())}"; self.project.rooms[rid] = {"name": n, "background": "", "hotpoints": [], "walkable": [], "player_pos": [960, 540]}; self.refresh_room_list()
    def refresh_room_list(self):
        self.room_listbox.delete(0, tk.END); [self.room_listbox.insert(tk.END, r["name"]) for r in self.project.rooms.values()]
    def refresh_obj_tree(self):
        self.obj_tree.delete(*self.obj_tree.get_children())
        if not self.current_room_id: return
        room = self.project.rooms[self.current_room_id]
        if "player_pos" in room: self.obj_tree.insert("", "end", iid="player", text="PLAYER AVATAR")
        for i, wa in enumerate(room["walkable"]): self.obj_tree.insert("", "end", iid=f"wa_{i}", text=f"Area {i+1}")
        for i, hp in enumerate(room["hotpoints"]): self.obj_tree.insert("", "end", iid=f"hp_{i}", text=hp.id, image=self.icons_ui.get("Edit_small"))
    def on_obj_tree_select(self, e):
        sel = self.obj_tree.selection()
        if sel: sid = sel[0]; self.selected_object = {"type": "player" if sid == "player" else ("wa" if sid.startswith("wa_") else "hp"), "idx": 0 if sid == "player" else int(sid[3:])}; self.refresh_canvas()
    def new_project_dialog(self):
        d = tk.Toplevel(self.root); d.title("NEW PROJECT"); d.geometry("350x250"); d.grab_set()
        tk.Label(d, text="NAME:").pack(); ne = tk.Entry(d); ne.insert(0, "NewAdventure"); ne.pack()
        tk.Label(d, text="RES:").pack(); rv = tk.StringVar(value="1920x1080"); tk.OptionMenu(d, rv, "1280x720", "1920x1080").pack()
        def confirm(): self.project = GamifikatorProject(ne.get(), rv.get()); self.init_workspace(); d.destroy()
        tk.Button(d, text="CREATE", command=confirm, bg="#007acc", fg="white").pack(pady=20)
    def init_workspace(self):
        if not self.project: return
        w, h = map(int, self.project.resolution.split('x')); self.view_scale = min(1100/w, 750/h); self.canvas.config(width=int(w*self.view_scale), height=int(h*self.view_scale)); self.refresh_room_list(); self.refresh_canvas()
    def save_project(self):
        if self.project: p = filedialog.asksaveasfilename(defaultextension=".phx"); open(p, 'w').write(self.project.to_json())
    def open_project(self):
        p = filedialog.askopenfilename(filetypes=[("PHX", "*.phx")])
        if p: self.project = GamifikatorProject.from_json(open(p, 'r').read()); self.init_workspace()
    def setup_canvas_events(self):
        self.canvas.bind("<Button-1>", self.on_canvas_down); self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, 'drag_data', {"x":0,"y":0,"obj":None,"mode":None}))
        self.root.bind("<Control-z>", self.undo); self.root.bind("<Delete>", self.delete_selected)
    def delete_selected(self, e):
        if self.selected_object and self.current_room_id:
            self.save_undo(); room = self.project.rooms[self.current_room_id]
            if self.selected_object["type"] == "hp": del room["hotpoints"][self.selected_object["idx"]]
            elif self.selected_object["type"] == "wa": del room["walkable"][self.selected_object["idx"]]
            elif self.selected_object["type"] == "player": del room["player_pos"]
            self.selected_object = None; self.refresh_obj_tree(); self.refresh_canvas()
    def select_background(self):
        p = filedialog.askopenfilename()
        if p and self.current_room_id: self.project.rooms[self.current_room_id]["background"] = p; self.refresh_canvas()
    def save_wa_params(self): pass
    def show_props(self, ptype):
        for f in [self.room_props_f, self.wa_props_f, self.hp_props_f]: f.pack_forget()
        if ptype == "room": self.room_props_f.pack(fill=tk.X)
        elif ptype == "wa": self.wa_props_f.pack(fill=tk.X)
        elif ptype == "hp": self.hp_props_f.pack(fill=tk.X)

if __name__ == "__main__":
    root = tk.Tk(); app = GamifikatorEditor(root); root.mainloop()
