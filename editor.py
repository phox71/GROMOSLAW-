import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import json
import os
import time
from PIL import Image, ImageTk

class GamifikatorProject:
    def __init__(self, name="Nowy Projekt", resolution="1920x1080"):
        self.name = name
        self.resolution = resolution
        self.rooms = {} # id: {name, background, hotpoints: [], walkable: []}
        self.items = {}
        self.start_room_id = ""

    def to_json(self):
        return json.dumps(self.__dict__, indent=4)

    @classmethod
    def from_json(cls, data):
        proj = cls()
        proj.__dict__.update(json.loads(data))
        return proj

class GamifikatorEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("GAMIFIKATOR - Photoshop Style Editor")
        self.root.geometry("1400x900")
        self.root.configure(bg="#181818")
        
        self.project = None
        self.current_room_id = None
        self.mode = "Select"
        
        # Walkable drawing state
        self.temp_points = []
        self.selected_walkable = None
        
        # UI Scaling & Assets
        self.view_scale = 1.0
        self.bg_image_ref = None
        
        self.setup_ui()
        self.setup_canvas_events()

    def setup_ui(self):
        # 1. TOOLBAR (Photoshop Style)
        self.toolbar = tk.Frame(self.root, bg="#2b2b2b", height=40)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        
        btn_style = {"bg": "#2b2b2b", "fg": "#ccc", "relief": tk.FLAT, "activebackground": "#3d3d3d", "activeforeground": "white", "padx": 15}
        
        tk.Button(self.toolbar, text="Plik", **btn_style).pack(side=tk.LEFT) # Placeholder for menu
        tk.Button(self.toolbar, text="NEW", command=self.new_project_dialog, **btn_style).pack(side=tk.LEFT)
        tk.Button(self.toolbar, text="OPEN", command=self.open_project, **btn_style).pack(side=tk.LEFT)
        tk.Button(self.toolbar, text="SAVE", command=self.save_project, **btn_style).pack(side=tk.LEFT)
        
        self.btn_play = tk.Button(self.toolbar, text="\u25ba PLAY", command=self.toggle_play, bg="#007acc", fg="white", relief=tk.FLAT, font=("Arial", 9, "bold"), padx=20)
        self.btn_play.pack(side=tk.RIGHT, padx=5, pady=5)

        # 2. TOOL PANEL (Photoshop Vertical)
        self.tool_frame = tk.Frame(self.root, bg="#2b2b2b", width=50)
        self.tool_frame.pack(side=tk.LEFT, fill=tk.Y, padx=1)
        
        self.tools = {}
        tool_icons = {"Select": "S", "Walkable": "W", "Hotpoint": "H"}
        for mode, icon in tool_icons.items():
            btn = tk.Button(self.tool_frame, text=icon, command=lambda m=mode: self.set_mode(m), 
                           bg="#2b2b2b", fg="#aaa", width=3, height=2, relief=tk.FLAT, font=("Arial", 10, "bold"))
            btn.pack(pady=2, padx=5)
            self.tools[mode] = btn

        # 3. CANVAS AREA
        self.canvas_container = tk.Frame(self.root, bg="#181818")
        self.canvas_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(self.canvas_container, bg="#000", highlightthickness=1, highlightbackground="#333")
        self.canvas.pack(padx=20, pady=20)

        # 4. SIDEBAR
        self.sidebar = tk.Frame(self.root, bg="#2b2b2b", width=300)
        self.sidebar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Rooms List
        tk.Label(self.sidebar, text="WARSTWY / POKOJE", bg="#383838", fg="#ccc", font=("Arial", 9, "bold"), pady=5).pack(fill=tk.X)
        self.room_listbox = tk.Listbox(self.sidebar, bg="#1e1e1e", fg="#ccc", borderwidth=0, selectbackground="#007acc", height=10, relief=tk.FLAT)
        self.room_listbox.pack(fill=tk.X, padx=5, pady=5)
        self.room_listbox.bind("<<ListboxSelect>>", self.on_room_selected)
        
        r_btn_f = tk.Frame(self.sidebar, bg="#2b2b2b")
        r_btn_f.pack(fill=tk.X, padx=5)
        tk.Button(r_btn_f, text="+", command=self.add_room, bg="#444", fg="white", relief=tk.FLAT, width=3).pack(side=tk.LEFT, padx=2)
        tk.Button(r_btn_f, text="-", command=self.delete_room, bg="#444", fg="white", relief=tk.FLAT, width=3).pack(side=tk.LEFT, padx=2)

        # Properties
        tk.Label(self.sidebar, text="WŁAŚCIWOŚCI", bg="#383838", fg="#ccc", font=("Arial", 9, "bold"), pady=5).pack(fill=tk.X, pady=(20, 0))
        self.prop_scroll = tk.Frame(self.sidebar, bg="#2b2b2b")
        self.prop_scroll.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.setup_properties_ui()

        # STATUS BAR
        self.status_bar = tk.Frame(self.root, bg="#007acc", height=25)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = tk.Label(self.status_bar, text="Gotowy", bg="#007acc", fg="white", font=("Arial", 8))
        self.status_label.pack(side=tk.LEFT, padx=10)

    def setup_properties_ui(self):
        # Room props
        self.room_props = tk.Frame(self.prop_scroll, bg="#2b2b2b")
        self.room_props.pack(fill=tk.X)
        tk.Button(self.room_props, text="WGRAJ TŁO", command=self.select_background, bg="#444", fg="white", relief=tk.FLAT).pack(fill=tk.X, pady=2)
        self.bg_info = tk.Label(self.room_props, text="Brak tła", bg="#2b2b2b", fg="#888", font=("Arial", 8))
        self.bg_info.pack()

        # Walkable props (hidden by default)
        self.walkable_props = tk.Frame(self.prop_scroll, bg="#2b2b2b")
        tk.Label(self.walkable_props, text="SKALOWANIE BOHATERA", bg="#2b2b2b", fg="#C4A35A").pack(pady=5)
        self.scale_min = tk.Scale(self.walkable_props, from_=10, to=200, orient=tk.HORIZONTAL, label="MIN %", bg="#2b2b2b", fg="white", highlightthickness=0)
        self.scale_min.set(100)
        self.scale_min.pack(fill=tk.X)
        self.scale_max = tk.Scale(self.walkable_props, from_=10, to=200, orient=tk.HORIZONTAL, label="MAX %", bg="#2b2b2b", fg="white", highlightthickness=0)
        self.scale_max.set(100)
        self.scale_max.pack(fill=tk.X)
        tk.Button(self.walkable_props, text="ZAPISZ SKALOWANIE", command=self.save_walkable_params, bg="#007acc", fg="white", relief=tk.FLAT).pack(fill=tk.X, pady=10)

    def setup_canvas_events(self):
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Button-3>", self.finish_polygon)
        self.canvas.bind("<Motion>", self.on_canvas_motion)

    def set_mode(self, mode):
        self.mode = mode
        self.temp_points = []
        self.refresh_canvas()
        for m, btn in self.tools.items():
            btn.config(bg="#3d3d3d" if m == mode else "#2b2b2b", fg="white" if m == mode else "#aaa")
        self.status_label.config(text=f"Narzędzie: {mode}")

    def on_canvas_click(self, event):
        if not self.current_room_id: return
        x_abs, y_abs = int(event.x / self.view_scale), int(event.y / self.view_scale)
        
        if self.mode == "Walkable":
            self.temp_points.extend([x_abs, y_abs])
            self.refresh_canvas()
        elif self.mode == "Select":
            self.select_object(x_abs, y_abs)

    def finish_polygon(self, event=None):
        if self.mode == "Walkable" and len(self.temp_points) >= 6:
            new_wa = {
                "points": self.temp_points[:],
                "scale_min": 100,
                "scale_max": 100
            }
            self.project.rooms[self.current_room_id]["walkable"].append(new_wa)
            self.temp_points = []
            self.refresh_canvas()
            self.status_label.config(text="Dodano obszar Walkable")

    def on_canvas_motion(self, event):
        if not self.project: return
        x_abs, y_abs = int(event.x / self.view_scale), int(event.y / self.view_scale)
        self.status_label.config(text=f"X: {x_abs} Y: {y_abs} | {self.mode}")
        if self.mode == "Walkable" and self.temp_points:
            self.refresh_canvas()
            # Draw line to cursor
            last_x, last_y = self.temp_points[-2], self.temp_points[-1]
            self.canvas.create_line(last_x*self.view_scale, last_y*self.view_scale, event.x, event.y, fill="white", dash=(4,4))

    def select_object(self, x, y):
        # Check Walkable Areas
        room = self.project.rooms[self.current_room_id]
        self.selected_walkable = None
        self.walkable_props.pack_forget()
        
        for i, wa in enumerate(room["walkable"]):
            # Simple bounding box check for now
            pts = wa["points"]
            px, py = pts[0::2], pts[1::2]
            if min(px) <= x <= max(px) and min(py) <= y <= max(py):
                self.selected_walkable = i
                self.scale_min.set(wa["scale_min"])
                self.scale_max.set(wa["scale_max"])
                self.walkable_props.pack(fill=tk.X)
                break
        self.refresh_canvas()

    def save_walkable_params(self):
        if self.selected_walkable is not None:
            wa = self.project.rooms[self.current_room_id]["walkable"][self.selected_walkable]
            wa["scale_min"] = self.scale_min.get()
            wa["scale_max"] = self.scale_max.get()
            messagebox.showinfo("Zapisano", "Parametry skalowania zaktualizowane.")

    def refresh_canvas(self):
        self.canvas.delete("all")
        if not self.current_room_id: return
        
        room = self.project.rooms[self.current_room_id]
        
        # Background
        if room["background"] and os.path.exists(room["background"]):
            img = Image.open(room["background"])
            w_res, h_res = map(int, self.project.resolution.split('x'))
            img = img.resize((int(w_res * self.view_scale), int(h_res * self.view_scale)))
            self.bg_image_ref = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, image=self.bg_image_ref, anchor="nw")

        # Walkable Areas
        for i, wa in enumerate(room["walkable"]):
            color = "#007acc" if i == self.selected_object else "#005555"
            fill = "#007acc" if i == self.selected_walkable else ""
            scaled_pts = [p * self.view_scale for p in wa["points"]]
            self.canvas.create_polygon(scaled_pts, outline="cyan", fill=fill, stipple="gray25" if fill else "", width=2)

        # Drawing temp polygon
        if self.temp_points:
            scaled_temp = [p * self.view_scale for p in self.temp_points]
            if len(scaled_temp) >= 4:
                self.canvas.create_line(scaled_temp, fill="white", width=2)
            for i in range(0, len(scaled_temp), 2):
                self.canvas.create_oval(scaled_temp[i]-3, scaled_temp[i+1]-3, scaled_temp[i]+3, scaled_temp[i+1]+3, fill="white")

    def on_room_selected(self, event):
        selection = self.room_listbox.curselection()
        if selection:
            rid = list(self.project.rooms.keys())[selection[0]]
            self.current_room_id = rid
            room = self.project.rooms[rid]
            self.bg_info.config(text=os.path.basename(room["background"]) if room["background"] else "Brak tła")
            self.selected_walkable = None
            self.walkable_props.pack_forget()
            self.refresh_canvas()

    def add_room(self):
        if not self.project: return
        name = simpledialog.askstring("Nowy Pokój", "Nazwa:", initialvalue=f"Scena {len(self.project.rooms) + 1}")
        if name:
            rid = f"room_{int(time.time())}"
            self.project.rooms[rid] = {"name": name, "background": "", "hotpoints": [], "walkable": []}
            self.refresh_room_list()
            self.room_listbox.selection_set(tk.END)
            self.on_room_selected(None)

    def refresh_room_list(self):
        self.room_listbox.delete(0, tk.END)
        if self.project:
            for rid, data in self.project.rooms.items(): self.room_listbox.insert(tk.END, data["name"])

    def select_background(self):
        if not self.current_room_id: return
        path = filedialog.askopenfilename(filetypes=[("Obrazy PNG", "*.png")])
        if path:
            self.project.rooms[self.current_room_id]["background"] = path
            self.refresh_canvas()

    def new_project_dialog(self):
        d = tk.Toplevel(self.root); d.title("Nowy Projekt"); d.geometry("300x250"); d.grab_set()
        tk.Label(d, text="Nazwa:").pack(pady=5)
        ne = tk.Entry(d); ne.insert(0, "Moja Gra"); ne.pack()
        tk.Label(d, text="Rozdzielczość:").pack(pady=5)
        rv = tk.StringVar(value="1920x1080")
        rc = ttk.Combobox(d, textvariable=rv, values=["640x480", "1280x720", "1920x1080"]); rc.pack()
        def confirm():
            self.project = GamifikatorProject(ne.get(), rv.get())
            self.init_workspace(); d.destroy()
        tk.Button(d, text="UTWÓRZ", command=confirm, bg="#007acc", fg="white", relief=tk.FLAT).pack(pady=20)

    def init_workspace(self):
        if not self.project: return
        w_res, h_res = map(int, self.project.resolution.split('x'))
        self.view_scale = min(1100 / w_res, 750 / h_res)
        self.canvas.config(width=int(w_res * self.view_scale), height=int(h_res * self.view_scale))
        self.refresh_room_list()

    def save_project(self):
        if self.project:
            path = filedialog.asksaveasfilename(defaultextension=".phx")
            if path: 
                with open(path, 'w') as f: f.write(self.project.to_json())
                messagebox.showinfo("Zapisano", "OK")

    def open_project(self):
        path = filedialog.askopenfilename(filetypes=[("Gamifikator", "*.phx")])
        if path:
            with open(path, 'r') as f: self.project = GamifikatorProject.from_json(f.read())
            self.init_workspace(); self.refresh_room_list()

    def delete_room(self): pass
    def toggle_play(self): pass

if __name__ == "__main__":
    root = tk.Tk(); app = GamifikatorEditor(root); root.mainloop()
