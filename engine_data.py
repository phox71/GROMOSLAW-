import json

class Hotpoint:
    def __init__(self, id, x, y, w=100, h=100, image_path="", swap_image_path="", action="comment", scale_png=100, opacity=100, flow=None, comments=None, comment_dur=2.0, comment_gap=0.5, is_item=False, required_item="", **kwargs):
        self.id = id
        self.x, self.y, self.w, self.h = x, y, w, h
        self.image_path = image_path
        self.swap_image_path = swap_image_path
        self.action = action
        self.scale_png = scale_png
        self.opacity = opacity
        self.flow = flow or {"p_com": True, "h_com": False, "unlock": False, "swap": False, "move": False}
        self.comments = comments or []
        self.comment_dur = comment_dur
        self.comment_gap = comment_gap
        self.is_item = is_item
        self.required_item = required_item
    def to_dict(self): return self.__dict__

class WalkableArea:
    def __init__(self, id, points=None):
        self.id = id
        self.points = points or []
    def to_dict(self): return self.__dict__

class GamifikatorProject:
    def __init__(self, name="New Project", resolution="1920x1080"):
        self.name = name
        self.resolution = resolution
        self.rooms = {}
        self.sprites = {}  # {sprite_id: {"name": str, "path": str}}
        self.animations = {}  # {anim_id: {"name": str, "sheet_path": str, "frames": int, "frame_w": int, "frame_h": int, "fps": int}}
        self.dialogs = {}  # {dlg_id: {name, hotpoint_id, trigger_item, start, nodes:{nid:{type,speaker,text,dur,give_item,choices,next,x,y}}}}
        self.scripts = {}  # {scr_id: {"name": str, "code": str, "scope": "global"|"room", "room_id": str, "trigger": "on_enter"|"on_exit"|"manual", "created": str}}
        self.wrong_item_msgs = [
            "To nie jest właściwy przedmiot.",
            "Potrzebuję czegoś innego.",
            "Hmm... nie sądzę.",
            "To tu nie pasuje.",
        ]
        self.player = {
            "scale": 100,
            "walk_speed": 10,
            "animations": {
                "idle":    {"path": "", "frames": 1},
                "walk_r":  {"path": "", "frames": 1},
                "walk_u":  {"path": "", "frames": 1},
                "walk_d":  {"path": "", "frames": 1},
                "walk_rd": {"path": "", "frames": 1},
                "walk_ru": {"path": "", "frames": 1},
            }
        }
    def to_json(self):
        def d(o): return o.to_dict() if hasattr(o, "to_dict") else o
        return json.dumps(self.__dict__, default=d, indent=4)
    @staticmethod
    def from_json(data):
        d = json.loads(data)
        p = GamifikatorProject(d["name"], d.get("resolution", "1920x1080"))
        p.rooms = d["rooms"]
        p.sprites = d.get("sprites", {})
        p.animations = d.get("animations", {})
        p.scripts = d.get("scripts", {})
        p.dialogs = d.get("dialogs", {})
        p.wrong_item_msgs = d.get("wrong_item_msgs", p.wrong_item_msgs)
        p.player = d.get("player", p.player)
        for k in ["walk_rd", "walk_ru"]:
            p.player["animations"].setdefault(k, {"path": "", "frames": 1})
        return p
