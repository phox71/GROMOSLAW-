import json

class Item:
    def __init__(self, id, name, icon_path=""):
        self.id = id
        self.name = name
        self.icon_path = icon_path
    def to_dict(self): return self.__dict__

class Hotpoint:
    def __init__(self, id, x, y, w=100, h=100, image_path="", swap_image_path="", action="comment", scale_png=100, opacity=100, flow=None, comments=None, give_item_id="", require_item_id="", dialogue_id=""):
        self.id = id
        self.x, self.y, self.w, self.h = x, y, w, h
        self.image_path = image_path
        self.swap_image_path = swap_image_path
        self.action = action
        self.scale_png = scale_png
        self.opacity = opacity
        self.flow = flow or {"p_com": True, "h_com": False, "unlock": False, "swap": False, "move": False}
        self.comments = comments or []
        self.give_item_id = give_item_id
        self.require_item_id = require_item_id
        self.dialogue_id = dialogue_id
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
        self.items = {} # Global items: {id: Item_dict}
        self.dialogues = {} # Global dialogues: {id: Dialogue_dict}
        self.player = {
            "scale": 100,
            "walk_speed": 10,
            "inventory": [], # List of item IDs
            "animations": {
                "idle": {"path": "", "frames": 1},
                "walk_r": {"path": "", "frames": 1},
                "walk_u": {"path": "", "frames": 1},
                "walk_d": {"path": "", "frames": 1}
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
        p.items = d.get("items", {})
        p.dialogues = d.get("dialogues", {})
        p.player = d.get("player", p.player)
        if "inventory" not in p.player: p.player["inventory"] = []
        return p
