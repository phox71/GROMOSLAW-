import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import os, time, math, copy
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
        if self.tip_window or not self.text: return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT, bg="#ffffe1", fg="black", relief=tk.SOLID, borderwidth=1, font=("Segoe UI", 8))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw: tw.destroy()

class GamifikatorEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("GAMIFIKATOR 2026 - v2.1.3 [STABLE]")
        self.root.geometry("1650x950")
        self.root.configure(bg="#121212")
        
        self.project = None
        self.current_room_id = None
        self.mode = "Select"
        self.is_playing = False
        self.undo_stack = []
        self.temp_points = []
        self.selected_object = None 
        self.drag_data = {"obj": None, "mode": None, "off_x": 0, "off_y": 0, "start_w": 0, "start_h": 0, "start_x": 0, "start_y": 0}
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
        
        self.load_ui_assets()
        self.setup_ui()
        self.setup_canvas_events()
        self.engine_loop()
        self.log("System Gamifikator v2.1.3 gotowy.")

    def log(self, message):
        ts = time.strftime("%H:%M:%S")
        self.log_history.append(f"[{ts}] {message}")
        if hasattr(self, 'log_text'):
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"[{ts}] {message}\n")
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
        source = image.split(); return Image.merge("RGBA", (source[0].point(lambda i: r), source[1].point(lambda i: g), source[2].point(lambda i: b), source[3]))

    def save_undo(self):
        if not self.project: return
        self.undo_stack.append(copy.deepcopy(self.project.rooms))
        if len(self.undo_stack) > 15: self.undo_stack.pop(0)

    def undo(self, event=None):
        if self.undo_stack:
            self.project.rooms = self.undo_stack.pop()
            self.refresh_obj_tree(); self.refresh_canvas(); self.log("Cofnięto zmianę.")

    def setup_ui(self):
        self.toolbar = tk.Frame(self.root, bg="#1e1e1e", height=50); self.toolbar.pack(side=tk.TOP, fill=tk.X)
        btn_s = {"bg": "#1e1e1e", "fg": "#eee", "relief": tk.FLAT, "font": ("Segoe UI", 9)}
        tk.Button(self.toolbar, text="PROJECT", command=self.new_project_dialog, **btn_s).pack(side=tk.LEFT, padx=10)
        tk.Button(self.toolbar, text="OPEN", command=self.open_project, **btn_s).pack(side=tk.LEFT, padx=10)
        tk.Button(self.toolbar, text="SAVE", command=self.save_project, **btn_s).pack(side=tk.LEFT, padx=10)
        self.btn_play = tk.Button(self.toolbar, text="\u25ba PLAY MODE", command=self.toggle_play, bg="#007acc", fg="white", relief=tk.FLAT, font=("Segoe UI", 9, "bold"), padx=25); self.btn_play.pack(side=tk.RIGHT, padx=10, pady=8)

        self.main_pane = tk.PanedWindow(self.root, orient=tk.VERTICAL, bg="#121212", sashwidth=6); self.main_pane.pack(fill=tk.BOTH, expand=True)
        self.workspace_frame = tk.Frame(self.main_pane, bg="#121212"); self.main_pane.add(self.workspace_frame, stretch="always")

        self.tool_frame = tk.Frame(self.workspace_frame, bg="#1e1e1e", width=80); self.tool_frame.pack(side=tk.LEFT, fill=tk.Y, padx=1); self.tool_frame.pack_propagate(False)
        self.tool_btns = {}
        for m in ["Select", "Walkable", "Hotpoint"]:
            btn = tk.Button(self.tool_frame, image=self.icons_ui.get(f"{m}_dark"), bg="#1e1e1e", relief=tk.FLAT, command=lambda mode=m: self.set_mode(mode))
            btn.pack(pady=(15, 0), padx=10); tk.Label(self.tool_frame, text=m.upper(), bg="#1e1e1e", fg="#555", font=("Segoe UI", 7, "bold")).pack(); self.tool_btns[m] = btn

        self.sidebar = tk.Frame(self.workspace_frame, bg="#1e1e1e", width=350); self.sidebar.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Label(self.sidebar, text="AVATAR", bg="#2d2d2d", fg="#aaa", font=("Segoe UI", 8, "bold"), pady=5).pack(fill=tk.X)
        tk.Button(self.sidebar, text="CONFIGURE PLAYER", command=self.open_player_settings, bg="#007acc", fg="white", relief=tk.FLAT).pack(fill=tk.X, padx=10, pady=5)
        tk.Label(self.sidebar, text="SCENES", bg="#2d2d2d", fg="#aaa", font=("Segoe UI", 8, "bold"), pady=5).pack(fill=tk.X, pady=(10,0))
        self.room_listbox = tk.Listbox(self.sidebar, bg="#121212", fg="#ddd", borderwidth=0, height=5); self.room_listbox.pack(fill=tk.X, padx=10, pady=5); self.room_listbox.bind("<<ListboxSelect>>", self.on_room_selected)
        tk.Button(self.sidebar, text="+ NEW SCENE", command=self.add_room, bg="#333", fg="white", relief=tk.FLAT).pack(fill=tk.X, padx=10)
        tk.Label(self.sidebar, text="OBJECTS", bg="#2d2d2d", fg="#aaa", font=("Segoe UI", 8, "bold"), pady=5).pack(fill=tk.X, pady=(15, 0))
        self.obj_tree = ttk.Treeview(self.sidebar, show="tree", height=10); self.obj_tree.pack(fill=tk.X, padx=10, pady=5)
        self.obj_tree.bind("<<TreeviewSelect>>", self.on_obj_tree_select); self.obj_tree.bind("<Button-1>", self.on_obj_tree_click)
        self.prop_container = tk.Frame(self.sidebar, bg="#1e1e1e"); self.prop_container.pack(fill=tk.BOTH, expand=True, padx=10); self.setup_properties_ui()
        self.cv_area = tk.Frame(self.workspace_frame, bg="#121212"); self.cv_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.warning_bar = tk.Label(self.cv_area, text="", bg="#8b0000", fg="white", font=("Segoe UI", 9, "bold")); self.warning_bar.pack(fill=tk.X)
        self.canvas = tk.Canvas(self.cv_area, bg="#000", highlightthickness=0); self.canvas.pack(expand=True)
        self.con_frame = tk.Frame(self.main_pane, bg="#1e1e1e", height=120); self.main_pane.add(self.con_frame, stretch="never")
        log_h = tk.Frame(self.con_frame, bg="#2d2d2d"); log_h.pack(fill=tk.X)
        tk.Label(log_h, text="CONSOLE", bg="#2d2d2d", fg="#888", font=("Segoe UI", 7, "bold")).pack(side=tk.LEFT, padx=10)
        self.log_text = tk.Text(self.con_frame, bg="#000", fg="#00ff00", font=("Consolas", 9), state=tk.DISABLED, borderwidth=0); self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_properties_ui(self):
        self.room_props_f = tk.Frame(self.prop_container, bg="#1e1e1e")
        tk.Button(self.room_props_f, text="SET BACKGROUND PNG", command=self.select_background, bg="#007acc", fg="white", relief=tk.FLAT).pack(fill=tk.X, pady=5)
        self.room_props_f.pack(fill=tk.X)
        self.wa_props_f = tk.Frame(self.prop_container, bg="#1e1e1e")
        self.scale_min = tk.Scale(self.wa_props_f, from_=10, to=200, orient=tk.HORIZONTAL, label="MIN Y %", bg="#1e1e1e", fg="white", highlightthickness=0); self.scale_min.pack(fill=tk.X)
        self.scale_max = tk.Scale(self.wa_props_f, from_=10, to=200, orient=tk.HORIZONTAL, label="MAX Y %", bg="#1e1e1e", fg="white", highlightthickness=0); self.scale_max.pack(fill=tk.X)
        tk.Button(self.wa_props_f, text="SAVE SCALING", command=self.save_wa_params, bg="#007acc", fg="white", relief=tk.FLAT).pack(fill=tk.X, pady=10)
        self.hp_props_f = tk.Frame(self.prop_container, bg="#1e1e1e")
        tk.Button(self.hp_props_f, text="EDIT HOTPOINT SETTINGS ⚙", command=lambda: self.open_hp_settings(None), bg="#333", fg="white", relief=tk.FLAT, pady=10).pack(fill=tk.X)

    def engine_loop(self):
        if self.is_playing:
            dx = self.player_target[0] - self.player_runtime_pos[0]; dy = self.player_target[1] - self.player_runtime_pos[1]
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > 5:
                s = self.project.player["walk_speed"]; self.player_runtime_pos[0] += (dx/dist)*s; self.player_runtime_pos[1] += (dy/dist)*s
            self.active_dialogs = [d for d in self.active_dialogs if d["end"] > time.time()]
        self.refresh_canvas(); self.root.after(30, self.engine_loop)

    def toggle_play(self):
        if not self.current_room_id: return
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.btn_play.config(text="STOP [ESC]", bg="#8b0000")
            self.tool_frame.pack_forget(); self.sidebar.pack_forget(); self.con_frame.pack_forget()
            r = self.project.rooms[self.current_room_id]; self.player_runtime_pos = list(r.get("player_pos", [960, 540])); self.player_target = list(self.player_runtime_pos); self.swapped_hotpoints.clear(); self.active_dialogs.clear()
        else:
            self.btn_play.config(text="\u25ba PLAY MODE", bg="#007acc")
            self.tool_frame.pack(side=tk.LEFT, fill=tk.Y, padx=1); self.sidebar.pack(side=tk.RIGHT, fill=tk.Y); self.main_pane.add(self.con_frame, stretch="never")
        self.refresh_canvas()

    def handle_runtime_click(self, x, y):
        room = self.project.rooms[self.current_room_id]
        for hp in reversed(room["hotpoints"]):
            if hp.x <= x <= hp.x+hp.w and hp.y <= y <= hp.y+hp.h:
                if hp.flow.get("swap"): self.swapped_hotpoints.add(hp.id)
                self.execute_comments_runtime(hp); return
        tp = Point(x, y); polys = [Polygon([(p.points[i], p.points[i+1]) for i in range(0, len(p.points), 2)]) for p in room["walkable"]]
        if not polys: self.player_target = [x, y]; return
        cb = unary_union(polys)
        if cb.contains(tp): self.player_target = [x, y]
        else: n = nearest_points(cb, tp)[0]; self.player_target = [int(n.x), int(n.y)]

    def execute_comments_runtime(self, hp):
        if not hp.comments: return
        self.active_dialogs.clear(); d_acc = 0
        for c in hp.comments:
            def show(txt=c["text"], own=c["owner"], h=hp, dur=c.get("duration", 2.0)):
                self.active_dialogs.append({"text": txt, "owner": own, "hp_id": h.id, "end": time.time() + dur})
            self.root.after(int(d_acc * 1000), show)
            d_acc += c.get("duration", 2.0) + c.get("pause", 0.5)

    def open_hp_settings(self, hp=None):
        if not hp and self.selected_object and self.selected_object["type"] == "hp": hp = self.project.rooms[self.current_room_id]["hotpoints"][self.selected_object["idx"]]
        if not hp: return
        d = tk.Toplevel(self.root); d.title(f"Settings: {hp.id}"); d.geometry("650x950"); d.grab_set(); d.configure(bg="#1e1e1e")
        def lbl(t, tip=""): 
            f = tk.Frame(d, bg="#1e1e1e"); f.pack(anchor="w", padx=20, pady=(15,0))
            tk.Label(f, text=t, bg="#1e1e1e", fg="#C4A35A", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
            if tip: q = tk.Label(f, text=" (?) ", bg="#333", fg="#aaa", font=("Arial", 8)); q.pack(side=tk.LEFT, padx=5); ToolTip(q, tip)
        lbl("NAME / POS"); f_top = tk.Frame(d, bg="#1e1e1e"); f_top.pack(fill=tk.X, padx=20)
        ne = tk.Entry(f_top, width=15); ne.insert(0, hp.id); ne.pack(side=tk.LEFT); xe = tk.Entry(f_top, width=5); xe.insert(0, str(hp.x)); xe.pack(side=tk.LEFT, padx=5); ye = tk.Entry(f_top, width=5); ye.insert(0, str(hp.y)); ye.pack(side=tk.LEFT)
        lbl("GRAPHICS"); f_g = tk.Frame(d, bg="#1e1e1e"); f_g.pack(fill=tk.X, padx=20); b_v = tk.StringVar(value=hp.image_path); tk.Entry(f_g, textvariable=b_v).pack(side=tk.LEFT, fill=tk.X, expand=True); tk.Button(f_g, text="BASE", command=lambda: b_v.set(filedialog.askopenfilename() or b_v.get())).pack(side=tk.LEFT)
        s_v = tk.StringVar(value=hp.swap_image_path); tk.Entry(f_g, textvariable=s_v).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5); tk.Button(f_g, text="SWAP", command=lambda: s_v.set(filedialog.askopenfilename() or s_v.get())).pack(side=tk.LEFT)
        lbl("SCALE / ACTION"); sc_v = tk.Scale(d, from_=10, to=200, orient=tk.HORIZONTAL, bg="#1e1e1e", fg="white"); sc_v.set(hp.scale_png); sc_v.pack(fill=tk.X, padx=20); act_v = tk.StringVar(value=hp.action); tk.OptionMenu(d, act_v, "comment", "pick_up", "talk_to", "lock", "move_to").pack(fill=tk.X, padx=20)
        lbl("FLOW"); f_chk = tk.Frame(d, bg="#252526"); f_chk.pack(fill=tk.X, padx=20, pady=5); chk_vars = {k: tk.BooleanVar(value=v) for k, v in hp.flow.items()}
        for k, t in [("p_com", "Player Comment"), ("h_com", "Hotpoint Comment"), ("unlock", "Unlock LOCK"), ("swap", "Swap PNG"), ("move", "Change Room")]: tk.Checkbutton(f_chk, text=t, variable=chk_vars[k], bg="#252526", fg="#ccc").pack(anchor="w")
        lbl("COMMENTS [P/H] | TEXT | DUR | PAUSE"); com_f = tk.Frame(d, bg="#121212"); com_f.pack(fill=tk.BOTH, expand=True, padx=20)
        def add_com(t="", o="p", dur=2.0, ps=0.5): 
            r = tk.Frame(com_f, bg="#121212"); r.pack(fill=tk.X, pady=1); ow = tk.StringVar(value=o); tk.Button(r, textvariable=ow, width=2, bg="#333", command=lambda v=ow: v.set("h" if v.get()=="p" else "p")).pack(side=tk.LEFT)
            e = tk.Entry(r, bg="#1e1e1e", fg="white"); e.insert(0, t); e.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2); de = tk.Entry(r, width=3, bg="#1e1e1e", fg="#00ff00"); de.insert(0, str(dur)); de.pack(side=tk.LEFT); pe = tk.Entry(r, width=3, bg="#1e1e1e", fg="#ffff00"); pe.insert(0, str(ps)); pe.pack(side=tk.LEFT, padx=2); tk.Button(r, text="X", command=r.destroy, bg="#555").pack(side=tk.RIGHT)
        tk.Button(d, text="+ ADD LINE", command=add_com).pack()
        for c in hp.comments: add_com(c["text"], c["owner"], c.get("duration", 2.0), c.get("pause", 0.5))
        def save():
            self.save_undo(); hp.id, hp.x, hp.y, hp.scale_png, hp.action = ne.get(), int(xe.get()), int(ye.get()), sc_v.get(), act_v.get(); hp.image_path, hp.swap_image_path = b_v.get(), s_v.get()
            hp.flow = {k: v.get() for k, v in chk_vars.items()}; hp.comments = [{"text": w.winfo_children()[1].get(), "owner": w.winfo_children()[0].cget("text"), "duration": float(w.winfo_children()[2].get()), "pause": float(w.winfo_children()[3].get())} for w in com_f.winfo_children()]
            self.refresh_canvas(); d.destroy()
        tk.Button(d, text="SAVE", command=save, bg="#007acc", fg="white", pady=15).pack(fill=tk.X, padx=20, pady=20)

    def on_canvas_down(self, event):
        x, y = int(event.x / self.view_scale), int(event.y / self.view_scale)
        if self.is_playing: self.handle_runtime_click(x, y); return
        room = self.project.rooms.get(self.current_room_id) if self.current_room_id else None
        if not room: return
        # RESIZE CHECK (Handle even in HP mode)
        for i, hp in enumerate(reversed(room["hotpoints"])):
            if hp.x+hp.w-15 <= x <= hp.x+hp.w+15 and hp.y+hp.h-15 <= y <= hp.y+hp.h+15:
                self.drag_data = {"mode": "resize", "obj": hp, "start_w": hp.w, "start_h": hp.h, "start_x": x, "start_y": y}
                self.selected_object = {"type": "hp", "idx": len(room["hotpoints"])-1-i}; self.refresh_canvas(); return
        if self.mode == "Select":
            if "player_pos" in room:
                px, py = room["player_pos"]; s = self.project.player.get("scale", 100)/100.0
                if px-50*s <= x <= px+50*s and py-120*s <= y <= py: self.drag_data = {"mode": "move_player", "obj": room, "off_x": x-px, "off_y": y-py}; self.selected_object = {"type": "player"}; return
            for i, hp in enumerate(reversed(room["hotpoints"])):
                if hp.x <= x <= hp.x+hp.w and hp.y <= y <= hp.y+hp.h: self.drag_data = {"mode": "move", "obj": hp, "off_x": x-hp.x, "off_y": y-hp.y}; self.selected_object = {"type": "hp", "idx": len(room["hotpoints"])-1-i}; self.refresh_canvas(); return
            for i, wa in enumerate(room["walkable"]):
                if min(wa.points[0::2]) <= x <= max(wa.points[0::2]) and min(wa.points[1::2]) <= y <= max(wa.points[1::2]): self.selected_object = {"type": "wa", "idx": i}; self.refresh_canvas(); return
            self.selected_object = None; self.refresh_canvas()
        elif self.mode == "Hotpoint":
            self.save_undo(); new_hp = Hotpoint(id=f"hp_{len(room['hotpoints'])+1}", x=x, y=y, w=50, h=50); room["hotpoints"].append(new_hp)
            self.drag_data = {"mode": "resize", "obj": new_hp, "start_w": 0, "start_h": 0, "start_x": x, "start_y": y}
            self.selected_object = {"type": "hp", "idx": len(room["hotpoints"])-1}; self.refresh_obj_tree()
        elif self.mode == "Walkable":
            if self.temp_points and math.sqrt((x-self.temp_points[0])**2 + (y-self.temp_points[1])**2) < 25: self.finish_polygon(); return
            self.temp_points.extend([x, y]); self.refresh_canvas()

    def on_canvas_up(self, e): self.drag_data = {"obj":None,"mode":None,"off_x":0,"off_y":0,"start_w":0,"start_h":0,"start_x":0,"start_y":0}
    def on_canvas_drag(self, event):
        if not self.drag_data["obj"]: return
        x, y = int(event.x / self.view_scale), int(event.y / self.view_scale); o = self.drag_data["obj"]
        if self.drag_data["mode"] == "move_player": o["player_pos"] = [x - self.drag_data["off_x"], y - self.drag_data["off_y"]]
        elif self.drag_data["mode"] == "move": o.x, o.y = x - self.drag_data["off_x"], y - self.drag_data["off_y"]
        elif self.drag_data["mode"] == "resize": o.w, o.h = max(10, self.drag_data["start_w"] + (x - self.drag_data["start_x"])), max(10, self.drag_data["start_h"] + (y - self.drag_data["start_y"]))
        self.refresh_canvas()

    def finish_polygon(self):
        if len(self.temp_points) >= 6:
            self.save_undo(); room = self.project.rooms[self.current_room_id]
            try:
                new_poly = Polygon([(self.temp_points[i], self.temp_points[i+1]) for i in range(0, len(self.temp_points), 2)])
                merged = unary_union([new_poly] + [Polygon([(wa.points[j], wa.points[j+1]) for j in range(0, len(wa.points), 2)]) for wa in room["walkable"]])
                room["walkable"] = []
                if merged.geom_type == 'Polygon': self.add_shapely_poly(merged)
                elif merged.geom_type == 'MultiPolygon': [self.add_shapely_poly(p) for p in merged.geoms]
            except: room["walkable"].append(WalkableArea(id=f"wa_{int(time.time())}", points=self.temp_points[:]))
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
            is_sel = (not self.is_playing and self.selected_object and self.selected_object["type"] == "wa" and self.selected_object["idx"] == i)
            self.canvas.create_polygon([p*self.view_scale for p in wa.points], outline="#00ff00", fill="#00ff00" if is_sel else "", stipple="gray25", width=3)
        for i, hp in enumerate(room["hotpoints"]):
            act_p = hp.swap_image_path if (self.is_playing and hp.id in self.swapped_hotpoints and hp.swap_image_path) else hp.image_path
            if act_p and os.path.exists(act_p):
                h_img = Image.open(act_p).convert("RGBA"); sc = (hp.scale_png/100.0)*self.view_scale; h_img = h_img.resize((int(h_img.width*sc), int(h_img.height*sc)), Image.Resampling.LANCZOS); ref = ImageTk.PhotoImage(h_img); self.hp_images_refs[f"{hp.id}_{act_p}"] = ref; self.canvas.create_image(hp.x*self.view_scale, hp.y*self.view_scale, image=ref, anchor="nw")
            if not self.is_playing:
                is_sel = (self.selected_object and self.selected_object["type"] == "hp" and self.selected_object["idx"] == i)
                x1, y1, x2, y2 = hp.x*self.view_scale, hp.y*self.view_scale, (hp.x+hp.w)*self.view_scale, (hp.y+hp.h)*self.view_scale
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="#007acc" if is_sel else "white", width=2 if is_sel else 1)
                if is_sel: self.canvas.create_rectangle(x2-15, y2-15, x2, y2, fill="white")
        px, py = (self.player_runtime_pos if self.is_playing else room.get("player_pos", [960, 540]))
        self.draw_player(px, py, (not self.is_playing and self.selected_object and self.selected_object["type"] == "player"))
        if self.is_playing:
            for d in self.active_dialogs:
                tx, ty = (px, py-130) if d["owner"] == "p" else (self.get_hp_center(d["hp_id"]))
                self.canvas.create_text(tx*self.view_scale, ty*self.view_scale, text=d["text"], fill="white", font=("Segoe UI", 12, "bold"), justify="center", width=300)
        if self.temp_points:
            st = [p*self.view_scale for p in self.temp_points]; self.canvas.create_line(st, fill="white", width=2) if len(st)>=4 else None; self.canvas.create_oval(st[0]-5, st[1]-5, st[0]+5, st[1]+5, fill="red")

    def get_hp_center(self, hp_id):
        r = self.project.rooms[self.current_room_id]
        for hp in r["hotpoints"]:
            if hp.id == hp_id: return (hp.x + hp.w//2, hp.y - 20)
        return (500, 500)

    def draw_player(self, px, py, is_sel):
        scale = (self.project.player.get("scale", 100) / 100.0)*self.view_scale
        p_img = self.player_placeholder_raw; idle = self.project.player["animations"].get("idle", {}).get("path", "")
        if idle and os.path.exists(idle): p_img = Image.open(idle).convert("RGBA")
        if p_img:
            p_img = p_img.resize((int(100*scale), int(100*scale)), Image.Resampling.LANCZOS); self.player_image_ref = ImageTk.PhotoImage(p_img); self.canvas.create_image(px*self.view_scale, py*self.view_scale, image=self.player_image_ref, anchor="s")
            if is_sel: self.canvas.create_rectangle((px-50*scale/self.view_scale)*self.view_scale, (py-100*scale/self.view_scale)*self.view_scale, (px+50*scale/self.view_scale)*self.view_scale, py*self.view_scale, outline="#007acc", width=2)

    def open_player_settings(self):
        d = tk.Toplevel(self.root); d.title("Avatar"); d.geometry("450x500"); d.grab_set()
        def row(k):
            f = tk.Frame(d); f.pack(fill=tk.X, padx=10, pady=2); tk.Label(f, text=k).pack(side=tk.LEFT)
            v = tk.StringVar(value=self.project.player["animations"][k]["path"]); tk.Entry(f, textvariable=v).pack(side=tk.LEFT, fill=tk.X, expand=True)
            tk.Button(f, text="...", command=lambda: v.set(filedialog.askopenfilename() or v.get())).pack(side=tk.RIGHT); return v
        rvs = {k: row(k) for k in ["idle", "walk_r", "walk_u", "walk_d"]}
        tk.Label(d, text="SPEED").pack(); sp = tk.Scale(d, from_=1, to=30, orient=tk.HORIZONTAL); sp.set(self.project.player["walk_speed"]); sp.pack(fill=tk.X)
        def save(): [self.project.player["animations"][k].update({"path": v.get()}) for k, v in rvs.items()]; self.project.player["walk_speed"]=sp.get(); self.refresh_canvas(); d.destroy()
        tk.Button(d, text="SAVE", command=save, bg="#007acc", fg="white", pady=10).pack(pady=20)

    def set_mode(self, mode):
        self.mode = mode; self.temp_points = []; self.refresh_canvas()
        for m, btn in self.tool_btns.items(): btn.config(image=self.icons_ui.get(f"{m}_light") if m == mode else self.icons_ui.get(f"{m}_dark"))
    def on_room_selected(self, e): sel = self.room_listbox.curselection(); self.current_room_id = list(self.project.rooms.keys())[sel[0]] if sel else None; self.refresh_obj_tree(); self.refresh_canvas()
    def add_room(self): 
        n = simpledialog.askstring("N", "Scene Name:")
        if not n: return
        rid = f"r_{int(time.time())}"; self.project.rooms[rid] = {"name":n, "background":"", "hotpoints":[], "walkable":[], "player_pos":[960,540]}
        self.refresh_room_list()
        idx = len(self.project.rooms) - 1
        self.room_listbox.select_set(idx); self.on_room_selected(None)

    def refresh_room_list(self): self.room_listbox.delete(0, tk.END); [self.room_listbox.insert(tk.END, r["name"]) for r in self.project.rooms.values()]
    def refresh_obj_tree(self):
        self.obj_tree.delete(*self.obj_tree.get_children())
        if self.current_room_id:
            r = self.project.rooms[self.current_room_id]; [self.obj_tree.insert("", "end", iid=f"wa_{i}", text=f"Area {i+1}") for i, wa in enumerate(r["walkable"])]
            [self.obj_tree.insert("", "end", iid=f"hp_{i}", text=hp.id, image=self.icons_ui.get("Edit_small")) for i, hp in enumerate(r["hotpoints"])]
    def on_obj_tree_select(self, e):
        sel = self.obj_tree.selection()
        if sel: sid = sel[0]; self.selected_object = {"type": "wa" if sid.startswith("wa_") else "hp", "idx": int(sid[3:])} if not sid=="player" else {"type":"player"}; self.refresh_canvas()
    def on_obj_tree_click(self, event):
        reg = self.obj_tree.identify("region", event.x, event.y)
        if reg == "image":
            sid = self.obj_tree.identify_row(event.y)
            if sid.startswith("hp_"): self.open_hp_settings(self.project.rooms[self.current_room_id]["hotpoints"][int(sid[3:])])

    def new_project_dialog(self): 
        d = tk.Toplevel(self.root); d.title("NEW PROJECT"); d.geometry("400x300"); d.grab_set()
        tk.Label(d, text="Project Name:").pack(pady=5)
        ne = tk.Entry(d); ne.insert(0, "Game1"); ne.pack()
        tk.Label(d, text="Resolution:").pack(pady=5)
        res_v = tk.StringVar(value="1920x1080")
        tk.OptionMenu(d, res_v, "1920x1080", "1280x720").pack()
        def create():
            self.project = GamifikatorProject(ne.get(), res_v.get())
            self.init_workspace(); d.destroy()
        tk.Button(d, text="CREATE", command=create, bg="#007acc", fg="white").pack(pady=20)

    def init_workspace(self): 
        if not self.project: return
        w, h = map(int, self.project.resolution.split('x')); self.view_scale = min(1100/w, 750/h); self.canvas.config(width=int(w*self.view_scale), height=int(h*self.view_scale)); self.refresh_room_list(); self.refresh_canvas()
    def save_project(self):
        if self.project: p = filedialog.asksaveasfilename(defaultextension=".phx"); open(p, 'w', encoding='utf-8').write(self.project.to_json()) if p else None
    def open_project(self):
        p = filedialog.askopenfilename(filetypes=[("PHX", "*.phx")]); self.project = GamifikatorProject.from_json(open(p, 'r', encoding='utf-8').read()) if p else None; self.init_workspace()
    def select_background(self): 
        if not self.current_room_id: return
        p = filedialog.askopenfilename()
        if p: self.project.rooms[self.current_room_id]["background"] = p; self.refresh_canvas()
    def save_wa_params(self): pass
    def setup_canvas_events(self):
        self.canvas.bind("<Button-1>", self.on_canvas_down); self.canvas.bind("<B1-Motion>", self.on_canvas_drag); self.canvas.bind("<ButtonRelease-1>", self.on_canvas_up); self.root.bind("<Control-z>", self.undo); self.root.bind("<Escape>", lambda e: self.toggle_play() if self.is_playing else None)

if __name__ == "__main__":
    root = tk.Tk(); app = GamifikatorEditor(root); root.mainloop()
