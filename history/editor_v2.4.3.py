import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import os, time, math, copy
from PIL import Image, ImageTk
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union, nearest_points
from engine_data import Hotpoint, WalkableArea, GamifikatorProject, Item

class GamifikatorEditor:
    def __init__(self, root):
        self.root = root; self.root.title("GAMIFIKATOR 2026 - v2.4.3 [FINAL STABLE]")
        self.root.geometry("1650x950"); self.root.configure(bg="#121212")
        self.project = None; self.current_room_id = None; self.mode = "Select"
        self.is_playing = False; self.logs_visible = False; self.undo_stack = []
        self.temp_points = []; self.selected_object = None 
        self.drag_data = {"obj": None, "mode": None, "off_x": 0, "off_y": 0, "start_w": 0, "start_h": 0, "start_x": 0, "start_y": 0}
        self.view_scale = 1.0; self.player_runtime_pos = [0, 0]; self.player_target = [0, 0]
        self.active_dialogs = []; self.swapped_hotpoints = set()
        self.bg_image_ref = None; self.player_image_ref = None; self.hp_images_refs = {} 
        self.icons_ui = {}; self.player_placeholder_raw = None; self.log_history = []
        self.anim_tick = 0; self.preview_anim_tick = 0; self.facing_left = False
        self.inventory_open = False; self.active_item_id = None; self.item_icons_refs = {}
        self.load_ui_assets(); self.setup_ui(); self.setup_canvas_events(); self.engine_loop()
        self.log("System Gamifikator v2.4.3: Naprawa...")

    def log(self, message):
        ts = time.strftime("%H:%M:%S"); self.log_history.append(f"[{ts}] {message}")
        if hasattr(self, 'log_text'):
            self.log_text.config(state=tk.NORMAL); self.log_text.insert(tk.END, f"[{ts}] {message}\n")
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

    def setup_ui(self):
        self.toolbar = tk.Frame(self.root, bg="#1e1e1e", height=50); self.toolbar.pack(side=tk.TOP, fill=tk.X)
        btn_s = {"bg": "#1e1e1e", "fg": "#eee", "relief": tk.FLAT, "font": ("Segoe UI", 9)}
        tk.Button(self.toolbar, text="PROJECT", command=self.new_project_dialog, **btn_s).pack(side=tk.LEFT, padx=10)
        tk.Button(self.toolbar, text="OPEN", command=self.open_project, **btn_s).pack(side=tk.LEFT, padx=10)
        tk.Button(self.toolbar, text="SAVE", command=self.save_project, **btn_s).pack(side=tk.LEFT, padx=10)
        tk.Button(self.toolbar, text="ITEMS", command=self.open_items_manager, bg="#C4A35A", fg="black", relief=tk.FLAT, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=10)
        self.btn_logs = tk.Button(self.toolbar, text="LOGS", command=self.toggle_logs, **btn_s); self.btn_logs.pack(side=tk.LEFT, padx=10)
        self.btn_play = tk.Button(self.toolbar, text="\u25ba PLAY MODE", command=self.toggle_play, bg="#007acc", fg="white", relief=tk.FLAT, font=("Segoe UI", 9, "bold"), padx=25); self.btn_play.pack(side=tk.RIGHT, padx=10, pady=8)
        self.main_pane = tk.PanedWindow(self.root, orient=tk.VERTICAL, bg="#121212", sashwidth=6); self.main_pane.pack(fill=tk.BOTH, expand=True)
        self.workspace_frame = tk.Frame(self.main_pane, bg="#121212"); self.main_pane.add(self.workspace_frame, stretch="always")
        self.tool_frame = tk.Frame(self.workspace_frame, bg="#1e1e1e", width=80); self.tool_frame.pack(side=tk.LEFT, fill=tk.Y, padx=1); self.tool_frame.pack_propagate(False)
        self.tool_btns = {}
        for m in ["Select", "Walkable", "Hotpoint"]:
            btn = tk.Button(self.tool_frame, image=self.icons_ui.get(f"{m}_dark"), bg="#1e1e1e", relief=tk.FLAT, command=lambda mode=m: self.set_mode(mode))
            btn.pack(pady=(15, 0), padx=10); self.tool_btns[m] = btn
        self.sidebar = tk.Frame(self.workspace_frame, bg="#1e1e1e", width=350); self.sidebar.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Button(self.sidebar, text="CONFIGURE PLAYER", command=self.open_player_settings, bg="#007acc", fg="white", relief=tk.FLAT).pack(fill=tk.X, padx=10, pady=5)
        self.room_listbox = tk.Listbox(self.sidebar, bg="#121212", fg="#ddd", borderwidth=0, height=5, exportselection=False); self.room_listbox.pack(fill=tk.X, padx=10, pady=5); self.room_listbox.bind("<<ListboxSelect>>", self.on_room_selected)
        tk.Button(self.sidebar, text="+ NEW SCENE", command=self.add_room, bg="#333", fg="white", relief=tk.FLAT).pack(fill=tk.X, padx=10)
        self.obj_tree = ttk.Treeview(self.sidebar, show="tree", height=10); self.obj_tree.pack(fill=tk.X, padx=10, pady=5)
        self.obj_tree.bind("<<TreeviewSelect>>", self.on_obj_tree_select); self.obj_tree.bind("<Double-1>", self.on_obj_tree_double_click); self.obj_tree.bind("<Button-3>", self.on_obj_tree_right_click)
        tk.Button(self.sidebar, text="🗑 DELETE SELECTED", command=self.delete_selected, bg="#8b0000", fg="white", relief=tk.FLAT, font=("Segoe UI", 8, "bold")).pack(fill=tk.X, padx=10, pady=5)
        self.prop_container = tk.Frame(self.sidebar, bg="#1e1e1e"); self.prop_container.pack(fill=tk.BOTH, expand=True, padx=10); self.setup_properties_ui()
        self.cv_area = tk.Frame(self.workspace_frame, bg="#121212"); self.cv_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(self.cv_area, bg="#000", highlightthickness=0); self.canvas.pack(expand=True)
        self.con_frame = tk.Frame(self.main_pane, bg="#1e1e1e", height=100)
        self.log_text = tk.Text(self.con_frame, bg="#000", fg="#00ff00", font=("Consolas", 9), state=tk.DISABLED, borderwidth=0); self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_properties_ui(self):
        self.room_props_f = tk.Frame(self.prop_container, bg="#1e1e1e"); tk.Button(self.room_props_f, text="SET BACKGROUND PNG", command=self.select_background, bg="#007acc", fg="white", relief=tk.FLAT).pack(fill=tk.X, pady=5); self.room_props_f.pack(fill=tk.X)
        self.hp_props_f = tk.Frame(self.prop_container, bg="#1e1e1e"); tk.Button(self.hp_props_f, text="EDIT HOTPOINT SETTINGS ⚙", command=lambda: self.open_hp_settings(None), bg="#333", fg="white", relief=tk.FLAT, pady=10).pack(fill=tk.X)

    def engine_loop(self):
        self.anim_tick += 1
        if self.is_playing:
            if not self.inventory_open:
                dx = self.player_target[0] - self.player_runtime_pos[0]; dy = self.player_target[1] - self.player_runtime_pos[1]
                dist = math.sqrt(dx*dx + dy*dy)
                if dist > 3:
                    if dx < -1: self.facing_left = True
                    elif dx > 1: self.facing_left = False
                    s = self.project.player.get("walk_speed", 10)
                    self.player_runtime_pos[0] += (dx/dist)*s; self.player_runtime_pos[1] += (dy/dist)*s
            self.active_dialogs = [d for d in self.active_dialogs if d["end"] > time.time()]
        self.refresh_canvas(); self.root.after(100, self.engine_loop)

    def toggle_play(self):
        if not self.current_room_id: return
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.btn_play.config(text="STOP [ESC]", bg="#8b0000"); self.tool_frame.pack_forget(); self.sidebar.pack_forget(); self.con_frame.pack_forget()
            r = self.project.rooms[self.current_room_id]; self.player_runtime_pos = list(r.get("player_pos", [960, 540])); self.player_target = list(self.player_runtime_pos)
            self.swapped_hotpoints.clear(); self.active_dialogs.clear(); self.inventory_open = False; self.active_item_id = None
        else:
            self.btn_play.config(text="\u25ba PLAY MODE", bg="#007acc"); self.tool_frame.pack(side=tk.LEFT, fill=tk.Y, padx=1); self.sidebar.pack(side=tk.RIGHT, fill=tk.Y)
            if self.logs_visible: self.main_pane.add(self.con_frame, height=120)
        self.refresh_canvas()

    def toggle_logs(self):
        self.logs_visible = not self.logs_visible
        if self.logs_visible: self.main_pane.add(self.con_frame, height=120)
        else: self.main_pane.forget(self.con_frame)

    def refresh_canvas(self):
        self.canvas.delete("all")
        if not self.current_room_id: return
        room = self.project.rooms[self.current_room_id]
        if room.get("background") and os.path.exists(room["background"]):
            img = Image.open(room["background"]); w, h = map(int, self.project.resolution.split('x'))
            self.bg_image_ref = ImageTk.PhotoImage(img.resize((int(w*self.view_scale), int(h*self.view_scale)))); self.canvas.create_image(0, 0, image=self.bg_image_ref, anchor="nw")
        for i, wa in enumerate(room.get("walkable", [])):
            wa_pts = wa['points'] if isinstance(wa, dict) else wa.points
            is_sel = (not self.is_playing and self.selected_object and self.selected_object["type"] == "wa" and self.selected_object["idx"] == i)
            self.canvas.create_polygon([p*self.view_scale for p in wa_pts], outline="#00ff00", fill="#00ff00" if is_sel else "", stipple="gray25" if not is_sel else "", width=2)
        for i, hp in enumerate(room.get("hotpoints", [])):
            hp_obj = Hotpoint(**hp) if isinstance(hp, dict) else hp
            act_p = hp_obj.swap_image_path if (self.is_playing and hp_obj.id in self.swapped_hotpoints and hp_obj.swap_image_path) else hp_obj.image_path
            if act_p and os.path.exists(act_p):
                h_img = Image.open(act_p).convert("RGBA"); alpha = h_img.split()[3]; alpha = alpha.point(lambda p: p * (getattr(hp_obj, 'opacity', 100) / 100.0)); h_img.putalpha(alpha)
                sc = (hp_obj.scale_png/100.0)*self.view_scale; h_img = h_img.resize((int(h_img.width*sc), int(h_img.height*sc)), Image.Resampling.LANCZOS)
                ref = ImageTk.PhotoImage(h_img); self.hp_images_refs[f"{hp_obj.id}_{act_p}"] = ref; self.canvas.create_image(hp_obj.x*self.view_scale, hp_obj.y*self.view_scale, image=ref, anchor="nw")
            if not self.is_playing:
                is_sel = (self.selected_object and self.selected_object["type"] == "hp" and self.selected_object["idx"] == i)
                x1, y1, x2, y2 = hp_obj.x*self.view_scale, hp_obj.y*self.view_scale, (hp_obj.x+hp_obj.w)*self.view_scale, (hp_obj.y+hp_obj.h)*self.view_scale
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="#007acc" if is_sel else "white", width=2 if is_sel else 1)
                if is_sel: self.canvas.create_rectangle(x2-15, y2-15, x2, y2, fill="white"); self.canvas.create_text(x2-10, y1+20, text="⚙", fill="white", font=("Arial", 32, "bold"))
        px, py = (self.player_runtime_pos if self.is_playing else room.get("player_pos", [960, 540]))
        self.draw_player(px, py, (not self.is_playing and self.selected_object and self.selected_object["type"] == "player"))
        if self.is_playing:
            self.canvas.create_rectangle(1800*self.view_scale, 960*self.view_scale, 1920*self.view_scale, 1080*self.view_scale, fill="#C4A35A", outline="white")
            self.canvas.create_text(1860*self.view_scale, 1020*self.view_scale, text="ITEM", font=("Segoe UI", 14, "bold"))
            if self.inventory_open:
                self.canvas.create_rectangle(200*self.view_scale, 200*self.view_scale, 1720*self.view_scale, 880*self.view_scale, fill="#1e1e1e", stipple="gray75")
                for i, iid in enumerate(self.project.player["inventory"]):
                    item = self.project.items.get(iid)
                    if item:
                        ix, iy = 400 + (i%5)*220, 300 + (i//5)*220
                        if item["icon_path"] and os.path.exists(item["icon_path"]):
                            if iid not in self.item_icons_refs: self.item_icons_refs[iid] = ImageTk.PhotoImage(Image.open(item["icon_path"]).resize((150, 150)))
                            self.canvas.create_image((ix+100)*self.view_scale, (iy+100)*self.view_scale, image=self.item_icons_refs[iid], anchor="center")
            if self.active_item_id:
                mx, my = self.root.winfo_pointerx() - self.root.winfo_rootx(), self.root.winfo_pointery() - self.root.winfo_rooty()
                self.canvas.create_text(mx, my, text=f"USE: {self.project.items[self.active_item_id]['name']}", fill="#C4A35A", font=("Segoe UI", 12, "bold"))
            for d in self.active_dialogs:
                tx, ty = (px, py-130) if d["owner"] == "p" else (self.get_hp_center(d["hp_id"]))
                self.canvas.create_text(tx*self.view_scale, ty*self.view_scale, text=d["text"], fill="white", font=("Segoe UI", 12, "bold"), justify="center", width=300)
        if self.temp_points:
            st = [p*self.view_scale for p in self.temp_points]; self.canvas.create_line(st, fill="white", width=2) if len(st)>=4 else None; self.canvas.create_oval(st[0]-8, st[1]-8, st[0]+8, st[1]+8, fill="red", outline="white")

    def get_hp_center(self, hp_id):
        room = self.project.rooms[self.current_room_id]
        for hp in room["hotpoints"]:
            hp_obj = Hotpoint(**hp) if isinstance(hp, dict) else hp
            if hp_obj.id == hp_id: return (hp_obj.x + hp_obj.w//2, hp_obj.y)
        return (0, 0)

    def set_mode(self, mode):
        self.mode = mode
        for m, btn in self.tool_btns.items(): btn.config(image=self.icons_ui.get(f"{m}_light") if m == mode else self.icons_ui.get(f"{m}_dark"))
        self.log(f"Mode: {mode}")

    def open_items_manager(self):
        d = tk.Toplevel(self.root); d.title("Items Manager"); d.geometry("600x500"); d.grab_set(); d.configure(bg="#1e1e1e")
        f_list = tk.Frame(d, bg="#121212"); f_list.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        def refresh_list():
            for w in f_list.winfo_children(): w.destroy()
            for iid, item in self.project.items.items():
                r = tk.Frame(f_list, bg="#1e1e1e"); r.pack(fill=tk.X, pady=1)
                tk.Label(r, text=f"{iid}: {item['name']}", bg="#1e1e1e", fg="white").pack(side=tk.LEFT, padx=10)
                tk.Button(r, text="X", command=lambda i=iid: [self.project.items.pop(i), refresh_list()], bg="#555").pack(side=tk.RIGHT)
        def add_item():
            iid = simpledialog.askstring("ID", "Unique Item ID:")
            name = simpledialog.askstring("Name", "Display Name:")
            if iid and name: 
                path = filedialog.askopenfilename(title="Select Icon PNG")
                self.project.items[iid] = {"id": iid, "name": name, "icon_path": path}; refresh_list()
        tk.Button(d, text="+ ADD NEW ITEM", command=add_item, bg="#007acc", fg="white").pack(pady=10); refresh_list()

    def handle_runtime_click(self, x, y):
        room = self.project.rooms[self.current_room_id]
        if 1800*self.view_scale <= x*self.view_scale <= 1920*self.view_scale and 960*self.view_scale <= y*self.view_scale <= 1080*self.view_scale:
            self.inventory_open = not self.inventory_open; self.refresh_canvas(); return
        if self.inventory_open:
            for i, iid in enumerate(self.project.player["inventory"]):
                ix, iy = 400 + (i%5)*220, 300 + (i//5)*220
                if ix <= x <= ix+200 and iy <= y <= iy+200:
                    self.active_item_id = iid; self.inventory_open = False; self.refresh_canvas(); return
            self.inventory_open = False; self.refresh_canvas(); return
        target_x, target_y = x, y; hit_hp = None
        for hp in reversed(room["hotpoints"]):
            hp_obj = Hotpoint(**hp) if isinstance(hp, dict) else hp
            if hp_obj.x <= x <= hp_obj.x+hp_obj.w and hp_obj.y <= y <= hp_obj.y+hp_obj.h:
                hit_hp = hp_obj; target_x, target_y = hp_obj.x + hp_obj.w//2, hp_obj.y + hp_obj.h; break
        polys = [Polygon([(p['points'][j], p['points'][j+1]) for j in range(0, len(p['points']), 2)]) if isinstance(p, dict) else Polygon([(p.points[j], p.points[j+1]) for j in range(0, len(p.points), 2)]) for p in room["walkable"]]
        if not polys: self.player_target = [target_x, target_y]
        else:
            cb = unary_union(polys); tp = Point(target_x, target_y)
            if cb.contains(tp): self.player_target = [target_x, target_y]
            else: n = nearest_points(cb, tp)[0]; self.player_target = [int(n.x), int(n.y)]
        if hit_hp:
            if self.active_item_id:
                if getattr(hit_hp, 'require_item_id', "") == self.active_item_id:
                    self.log(f"Used {self.active_item_id}"); self.active_item_id = None
                    if hit_hp.flow.get("swap"): self.swapped_hotpoints.add(hit_hp.id)
                    self.execute_comments_runtime(hit_hp)
                else: self.active_dialogs.append({"text": "To nie zadziała.", "owner": "p", "end": time.time()+2}); self.active_item_id = None; return
            elif hit_hp.action == "pick_up" and getattr(hit_hp, 'give_item_id', ""):
                if hit_hp.give_item_id not in self.project.player["inventory"]: self.project.player["inventory"].append(hit_hp.give_item_id)
            if hit_hp.flow.get("swap") and not getattr(hit_hp, 'require_item_id', ""): self.swapped_hotpoints.add(hit_hp.id)
            self.execute_comments_runtime(hit_hp)

    def execute_comments_runtime(self, hp):
        if not hp.comments: return
        self.active_dialogs.clear(); d_acc = 0
        for c in hp.comments:
            def show(txt=c["text"], own=c["owner"], h=hp, dur=2.0):
                self.active_dialogs.append({"text": txt, "owner": own, "hp_id": h.id, "end": time.time() + dur})
            self.root.after(int(d_acc * 1000), show); d_acc += 2.5

    def open_hp_settings(self, hp=None):
        if not hp and self.selected_object and self.selected_object["type"] == "hp": hp = self.project.rooms[self.current_room_id]["hotpoints"][self.selected_object["idx"]]
        if not hp: return
        d = tk.Toplevel(self.root); d.title(f"Settings: {hp.id}"); d.geometry("650x950"); d.grab_set(); d.configure(bg="#1e1e1e")
        def lbl(t): tk.Label(d, text=t, bg="#1e1e1e", fg="#C4A35A", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20, pady=(10,0))
        f_top = tk.Frame(d, bg="#1e1e1e"); f_top.pack(fill=tk.X, padx=20)
        ne = tk.Entry(f_top, width=15); ne.insert(0, hp.id); ne.pack(side=tk.LEFT); xe = tk.Entry(f_top, width=5); xe.insert(0, str(hp.x)); xe.pack(side=tk.LEFT, padx=5); ye = tk.Entry(f_top, width=5); ye.insert(0, str(hp.y)); ye.pack(side=tk.LEFT)
        lbl("GRAPHICS"); f_g = tk.Frame(d, bg="#1e1e1e"); f_g.pack(fill=tk.X, padx=20); b_v = tk.StringVar(value=hp.image_path); tk.Entry(f_g, textvariable=b_v).pack(side=tk.LEFT, fill=tk.X, expand=True); tk.Button(f_g, text="BASE", command=lambda: b_v.set(filedialog.askopenfilename() or b_v.get())).pack(side=tk.LEFT)
        s_v = tk.StringVar(value=hp.swap_image_path); tk.Entry(f_g, textvariable=s_v).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5); tk.Button(f_g, text="SWAP", command=lambda: s_v.set(filedialog.askopenfilename() or s_v.get())).pack(side=tk.LEFT)
        lbl("INVENTORY LOGIC"); f_inv = tk.Frame(d, bg="#1e1e1e"); f_inv.pack(fill=tk.X, padx=20)
        item_list = [""] + list(self.project.items.keys())
        tk.Label(f_inv, text="GIVE:", bg="#1e1e1e", fg="#aaa").pack(side=tk.LEFT); g_v = tk.StringVar(value=getattr(hp, 'give_item_id', ""))
        ttk.Combobox(f_inv, textvariable=g_v, values=item_list, width=12).pack(side=tk.LEFT, padx=5)
        tk.Label(f_inv, text="REQUIRE:", bg="#1e1e1e", fg="#aaa").pack(side=tk.LEFT); r_v = tk.StringVar(value=getattr(hp, 'require_item_id', ""))
        ttk.Combobox(f_inv, textvariable=r_v, values=item_list, width=12).pack(side=tk.LEFT, padx=5)
        lbl("OPACITY LIVE %"); 
        def live_op(v): hp.opacity = int(v); self.refresh_canvas()
        op_v = tk.Scale(d, from_=10, to=100, orient=tk.HORIZONTAL, bg="#1e1e1e", fg="white", command=live_op); op_v.set(getattr(hp, 'opacity', 100)); op_v.pack(fill=tk.X, padx=20)
        lbl("SCALE LIVE %"); 
        def live_hp_sc(v): hp.scale_png = int(v); self.refresh_canvas()
        sc_v = tk.Scale(d, from_=10, to=500, orient=tk.HORIZONTAL, bg="#1e1e1e", fg="white", command=live_hp_sc); sc_v.set(hp.scale_png); sc_v.pack(fill=tk.X, padx=20)
        lbl("FLOW"); f_chk = tk.Frame(d, bg="#252526"); f_chk.pack(fill=tk.X, padx=20, pady=5); chk_vars = {k: tk.BooleanVar(value=v) for k, v in hp.flow.items()}
        for k, t in [("p_com", "Player Comment"), ("h_com", "Hotpoint Comment"), ("unlock", "Unlock LOCK"), ("swap", "Swap PNG"), ("move", "Change Room")]: tk.Checkbutton(f_chk, text=t, variable=chk_vars[k], bg="#252526", fg="#eee", selectcolor="#121212").pack(anchor="w", padx=5)
        com_f = tk.Frame(d, bg="#121212"); com_f.pack(fill=tk.BOTH, expand=True, padx=20)
        def add_com(t="", o="p"): 
            r = tk.Frame(com_f, bg="#121212"); r.pack(fill=tk.X, pady=1); ow = tk.StringVar(value=o); tk.Button(r, textvariable=ow, width=2, bg="#333", command=lambda v=ow: v.set("h" if v.get()=="p" else "p")).pack(side=tk.LEFT)
            e = tk.Entry(r, bg="#1e1e1e", fg="white"); e.insert(0, t); e.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2); tk.Button(r, text="X", command=r.destroy, bg="#555").pack(side=tk.RIGHT)
        tk.Button(d, text="+ ADD LINE", command=add_com).pack()
        for c in hp.comments: add_com(c["text"], c["owner"])
        def save():
            self.save_undo(); hp.id, hp.x, hp.y, hp.scale_png, hp.opacity = ne.get(), int(xe.get()), int(ye.get()), sc_v.get(), op_v.get()
            hp.give_item_id, hp.require_item_id = g_v.get(), r_v.get()
            hp.flow = {k: v.get() for k, v in chk_vars.items()}; hp.image_path, hp.swap_image_path = b_v.get(), s_v.get()
            hp.comments = [{"text": w.winfo_children()[1].get(), "owner": w.winfo_children()[0].cget("text")} for w in com_f.winfo_children() if len(w.winfo_children())>1]
            self.refresh_canvas(); d.destroy()
        tk.Button(d, text="SAVE", command=save, bg="#007acc", fg="white", pady=15).pack(fill=tk.X, padx=20, pady=20)

    def open_player_settings(self):
        d = tk.Toplevel(self.root); d.title("Avatar Config"); d.geometry("600x800"); d.grab_set(); d.configure(bg="#1e1e1e")
        preview_cv = tk.Canvas(d, width=200, height=200, bg="#121212", highlightthickness=0); preview_cv.pack(pady=10)
        self.preview_image_ref = None
        def row(k):
            f = tk.Frame(d, bg="#1e1e1e"); f.pack(fill=tk.X, padx=20, pady=2)
            tk.Label(f, text=k.upper(), bg="#1e1e1e", fg="#aaa", width=10).pack(side=tk.LEFT)
            p_v = tk.StringVar(value=self.project.player["animations"][k]["path"]); f_v = tk.StringVar(value=str(self.project.player["animations"][k]["frames"]))
            tk.Entry(f, textvariable=p_v, bg="#121212", fg="white", bd=0).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5); tk.Button(f, text="...", command=lambda: p_v.set(filedialog.askopenfilename() or p_v.get())).pack(side=tk.LEFT)
            tk.Entry(f, textvariable=f_v, width=3, bg="#121212", fg="#00ff00", bd=0).pack(side=tk.LEFT, padx=5); return {"path": p_v, "frames": f_v}
        rvs = {k: row(k) for k in ["idle", "walk_r", "walk_u", "walk_d"]}
        sp = tk.Scale(d, from_=1, to=100, orient=tk.HORIZONTAL, label="WALK SPEED", bg="#1e1e1e", fg="white"); sp.set(self.project.player.get("walk_speed", 10)); sp.pack(fill=tk.X, padx=20)
        def live_p_sc(v): self.project.player["scale"] = int(v); self.refresh_canvas()
        sc = tk.Scale(d, from_=10, to=500, orient=tk.HORIZONTAL, label="PLAYER SCALE %", bg="#1e1e1e", fg="white", command=live_p_sc); sc.set(self.project.player.get("scale", 100)); sc.pack(fill=tk.X, padx=20)
        def update_preview():
            if not d.winfo_exists(): return
            self.preview_anim_tick += 1; idle_data = rvs["idle"]; path = idle_data["path"].get(); frames = int(idle_data["frames"].get() or 1)
            if path and os.path.exists(path):
                img = Image.open(path).convert("RGBA"); fw = img.width // frames; fh = img.height
                frame_img = img.crop(((self.preview_anim_tick % frames) * fw, 0, ((self.preview_anim_tick % frames) + 1) * fw, fh))
                ratio = min(180/fw, 180/fh); frame_img = frame_img.resize((int(fw*ratio), int(fh*ratio)), Image.Resampling.LANCZOS)
                self.preview_image_ref = ImageTk.PhotoImage(frame_img); preview_cv.delete("all"); preview_cv.create_image(100, 100, image=self.preview_image_ref, anchor="center")
            d.after(100, update_preview)
        def save():
            for k, v in rvs.items(): self.project.player["animations"][k] = {"path": v["path"].get(), "frames": int(v["frames"].get() or 1)}
            self.project.player["walk_speed"], self.project.player["scale"] = sp.get(), sc.get(); self.refresh_canvas(); d.destroy()
        tk.Button(d, text="SAVE SETTINGS", command=save, bg="#007acc", fg="white", font=("Segoe UI", 10, "bold"), pady=10).pack(fill=tk.X, padx=20, pady=20); update_preview()

    def draw_player(self, px, py, is_sel):
        scale_val = self.project.player.get("scale", 100) / 100.0; draw_scale = scale_val * self.view_scale
        anim_data = self.project.player["animations"].get("idle", {"path": "", "frames": 1})
        path, frames = anim_data["path"], anim_data.get("frames", 1)
        if path and os.path.exists(path):
            img = Image.open(path).convert("RGBA"); fw, fh = img.width // frames, img.height
            p_img = img.crop(((self.anim_tick % frames) * fw, 0, ((self.anim_tick % frames) + 1) * fw, fh))
            if self.facing_left: p_img = p_img.transpose(Image.FLIP_LEFT_RIGHT)
            p_img = p_img.resize((int(fw*draw_scale), int(fh*draw_scale)), Image.Resampling.LANCZOS); self.player_image_ref = ImageTk.PhotoImage(p_img); self.canvas.create_image(px*self.view_scale, py*self.view_scale, image=self.player_image_ref, anchor="s")
            if is_sel: self.canvas.create_rectangle((px-(fw*scale_val)/2)*self.view_scale, (py-(fh*scale_val))*self.view_scale, (px+(fw*scale_val)/2)*self.view_scale, py*self.view_scale, outline="#007acc", width=2)
        else: self.canvas.create_oval((px-10)*self.view_scale, (py-10)*self.view_scale, (px+10)*self.view_scale, (py+10)*self.view_scale, fill="white")

    def on_canvas_down(self, event):
        x, y = int(event.x / self.view_scale), int(event.y / self.view_scale)
        if self.is_playing: self.handle_runtime_click(x, y); return
        room = self.project.rooms.get(self.current_room_id)
        if not room: return
        for i, hp in enumerate(reversed(room["hotpoints"])):
            hp_obj = Hotpoint(**hp) if isinstance(hp, dict) else hp
            if hp_obj.x+hp_obj.w-15 <= x <= hp_obj.x+hp_obj.w+15 and hp_obj.y+hp_obj.h-15 <= y <= hp_obj.y+hp_obj.h+15:
                self.drag_data = {"mode": "resize", "obj": hp_obj, "start_w": hp_obj.w, "start_h": hp_obj.h, "start_x": x, "start_y": y}
                self.selected_object = {"type": "hp", "idx": len(room["hotpoints"])-1-i}; self.refresh_canvas(); return
        if self.mode == "Select":
            if "player_pos" in room:
                px, py = room["player_pos"]; s = self.project.player.get("scale", 100)/100.0
                if px-100*s <= x <= px+100*s and py-200*s <= y <= py: self.drag_data = {"mode": "move_player", "obj": room, "off_x": x-px, "off_y": y-py}; self.selected_object = {"type": "player"}; return
            for i, hp in enumerate(reversed(room["hotpoints"])):
                hp_obj = Hotpoint(**hp) if isinstance(hp, dict) else hp
                if hp_obj.x <= x <= hp_obj.x+hp_obj.w and hp_obj.y <= y <= hp_obj.y+hp_obj.h: self.drag_data = {"mode": "move", "obj": hp_obj, "off_x": x-hp_obj.x, "off_y": y-hp_obj.y}; self.selected_object = {"type": "hp", "idx": len(room["hotpoints"])-1-i}; self.refresh_canvas(); return
            for i, wa in enumerate(room["walkable"]):
                wa_pts = wa['points'] if isinstance(wa, dict) else wa.points
                if min(wa_pts[0::2]) <= x <= max(wa_pts[0::2]): self.selected_object = {"type": "wa", "idx": i}; self.refresh_canvas(); return
            self.selected_object = None; self.refresh_canvas()
        elif self.mode == "Hotpoint":
            new_hp = Hotpoint(id=f"hp_{len(room['hotpoints'])+1}", x=x-50, y=y-50, w=100, h=100); room["hotpoints"].append(new_hp); self.selected_object = {"type": "hp", "idx": len(room["hotpoints"])-1}; self.refresh_obj_tree()
        elif self.mode == "Walkable":
            if self.temp_points and math.sqrt((x-self.temp_points[0])**2 + (y-self.temp_points[1])**2) < 25: self.finish_polygon(); return
            self.temp_points.extend([x, y]); self.refresh_canvas()

    def on_canvas_right_click(self, event):
        if self.mode == "Walkable": self.finish_polygon(); return
        if self.current_room_id:
            for hp in reversed(self.project.rooms[self.current_room_id]["hotpoints"]):
                hp_obj = Hotpoint(**hp) if isinstance(hp, dict) else hp
                if hp_obj.x <= (event.x/self.view_scale) <= hp_obj.x+hp_obj.w and hp_obj.y <= (event.y/self.view_scale) <= hp_obj.y+hp_obj.h: self.open_hp_settings(hp_obj); return

    def on_canvas_up(self, e): self.drag_data = {"obj":None,"mode":None}
    def on_canvas_drag(self, event):
        if not self.drag_data["obj"]: return
        x, y = int(event.x / self.view_scale), int(event.y / self.view_scale); o = self.drag_data["obj"]
        if self.drag_data["mode"] == "move_player": o["player_pos"] = [x - self.drag_data["off_x"], y - self.drag_data["off_y"]]
        elif self.drag_data["mode"] == "move": o.x, o.y = x - self.drag_data["off_x"], y - self.drag_data["off_y"]
        elif self.drag_data["mode"] == "resize": 
            o.w, o.h = max(20, self.drag_data["start_w"] + (x - self.drag_data["start_x"])), max(20, self.drag_data["start_h"] + (y - self.drag_data["start_y"]))
            if hasattr(o, 'image_path') and o.image_path and os.path.exists(o.image_path): raw = Image.open(o.image_path); o.scale_png = int((o.w / raw.width) * 100)
        self.refresh_canvas()

    def save_undo(self):
        if self.project: self.undo_stack.append(copy.deepcopy(self.project.rooms))
        if len(self.undo_stack) > 15: self.undo_stack.pop(0)
    def undo(self, event=None):
        if self.undo_stack: self.project.rooms = self.undo_stack.pop(); self.refresh_obj_tree(); self.refresh_canvas()
    def on_room_selected(self, e): sel = self.room_listbox.curselection(); self.current_room_id = list(self.project.rooms.keys())[sel[0]] if sel else None; self.refresh_obj_tree(); self.refresh_canvas()
    def add_room(self): 
        n = simpledialog.askstring("N", "Scene Name:"); rid = f"r_{int(time.time())}"
        if n: self.project.rooms[rid] = {"name":n, "background":"", "hotpoints":[], "walkable":[], "player_pos":[960,540]}; self.refresh_room_list(); self.room_listbox.select_set(tk.END); self.on_room_selected(None)
    def refresh_room_list(self): self.room_listbox.delete(0, tk.END); [self.room_listbox.insert(tk.END, r["name"]) for r in self.project.rooms.values()]
    def refresh_obj_tree(self):
        self.obj_tree.delete(*self.obj_tree.get_children())
        if self.current_room_id:
            r = self.project.rooms[self.current_room_id]
            for i, wa in enumerate(r.get("walkable", [])): self.obj_tree.insert("", "end", iid=f"wa_{i}", text=f"Area {i+1}")
            for i, hp in enumerate(r.get("hotpoints", [])):
                hp_obj = Hotpoint(**hp) if isinstance(hp, dict) else hp
                self.obj_tree.insert("", "end", iid=f"hp_{i}", text=hp_obj.id, image=self.icons_ui.get("Edit_small"))
    def on_obj_tree_select(self, e):
        sel = self.obj_tree.selection()
        if sel: sid = sel[0]; self.selected_object = {"type": "wa" if sid.startswith("wa_") else "hp", "idx": int(sid[3:])} if not sid=="player" else {"type":"player"}; self.refresh_canvas()
    def on_obj_tree_double_click(self, e):
        sel = self.obj_tree.selection(); sid = sel[0] if sel else ""
        if sid.startswith("hp_"): self.open_hp_settings(Hotpoint(**self.project.rooms[self.current_room_id]["hotpoints"][int(sid[3:])]) if isinstance(self.project.rooms[self.current_room_id]["hotpoints"][int(sid[3:])], dict) else self.project.rooms[self.current_room_id]["hotpoints"][int(sid[3:])])
    def on_obj_tree_right_click(self, event):
        iid = self.obj_tree.identify_row(event.y)
        if iid: self.obj_tree.selection_set(iid); self.on_obj_tree_select(None); m = tk.Menu(self.root, tearoff=0); m.add_command(label="🗑 Delete Object", command=self.delete_selected); m.post(event.x_root, event.y_root)
    def setup_canvas_events(self):
        self.canvas.bind("<Button-1>", self.on_canvas_down); self.canvas.bind("<B1-Motion>", self.on_canvas_drag); self.canvas.bind("<ButtonRelease-1>", self.on_canvas_up); self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.root.bind_all("<Delete>", self.delete_selected); self.root.bind("<Control-z>", self.undo); self.root.bind("<Escape>", lambda e: self.toggle_play() if self.is_playing else None)
    def new_project_dialog(self): 
        d = tk.Toplevel(self.root); d.title("NEW"); tk.Label(d, text="NAME:").pack(); ne = tk.Entry(d); ne.pack()
        rv = tk.StringVar(value="1920x1080"); tk.OptionMenu(d, rv, "1920x1080", "1280x720").pack()
        tk.Button(d, text="CREATE", command=lambda: [setattr(self, 'project', GamifikatorProject(ne.get(), rv.get())), self.init_workspace(), d.destroy()]).pack()
    def init_workspace(self): 
        if not self.project: return
        w, h = map(int, self.project.resolution.split("x")); self.view_scale = min(1100/w, 750/h); self.canvas.config(width=int(w*self.view_scale), height=int(h*self.view_scale)); self.refresh_room_list(); self.refresh_canvas()
    def save_project(self): 
        if self.project: p = filedialog.asksaveasfilename(defaultextension=".phx"); open(p, 'w', encoding='utf-8').write(self.project.to_json())
    def open_project(self):
        p = filedialog.askopenfilename(filetypes=[("PHX", "*.phx")])
        if p:
            self.project = GamifikatorProject.from_json(open(p, 'r', encoding='utf-8').read())
            for rid in self.project.rooms:
                r = self.project.rooms[rid]
                r["hotpoints"] = [Hotpoint(**h) if isinstance(h, dict) else h for h in r["hotpoints"]]
                r["walkable"] = [WalkableArea(**w) if isinstance(w, dict) else w for w in r["walkable"]]
            self.init_workspace(); self.room_listbox.select_set(0); self.on_room_selected(None)
    def select_background(self): 
        p = filedialog.askopenfilename()
        if p: self.project.rooms[self.current_room_id]["background"] = p; self.refresh_canvas()
    def delete_selected(self, e=None):
        if self.selected_object and self.current_room_id:
            self.save_undo(); r = self.project.rooms[self.current_room_id]
            if self.selected_object["type"] == "hp": del r["hotpoints"][self.selected_object["idx"]]
            elif self.selected_object["type"] == "wa": del r["walkable"][self.selected_object["idx"]]
            self.selected_object = None; self.refresh_obj_tree(); self.refresh_canvas()
    def finish_polygon(self):
        if len(self.temp_points) >= 6:
            room = self.project.rooms[self.current_room_id]
            try:
                new_poly = Polygon([(self.temp_points[i], self.temp_points[i+1]) for i in range(0, len(self.temp_points), 2)])
                polys = [Polygon([(p['points'][j], p['points'][j+1]) for j in range(0, len(p['points']), 2)]) if isinstance(p, dict) else Polygon([(p.points[j], p.points[j+1]) for j in range(0, len(p.points), 2)]) for p in room["walkable"]]
                merged = unary_union([new_poly] + polys)
                room["walkable"] = []
                if merged.geom_type == "Polygon": self.add_shapely_poly(merged)
                elif merged.geom_type == "MultiPolygon": [self.add_shapely_poly(p) for p in merged.geoms]
            except: room["walkable"].append(WalkableArea(id=f"wa_{int(time.time())}", points=self.temp_points[:]))
            self.temp_points = []; self.refresh_canvas(); self.refresh_obj_tree()
    def add_shapely_poly(self, poly):
        pts = []; [pts.extend([int(x), int(y)]) for x, y in poly.exterior.coords]
        self.project.rooms[self.current_room_id]["walkable"].append(WalkableArea(id=f"wa_{int(time.time())}", points=pts))

if __name__ == "__main__":
    root = tk.Tk(); app = GamifikatorEditor(root); root.mainloop()
