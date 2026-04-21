import json
from dataclasses import dataclass, field

@dataclass
class Hotpoint:
    id: str
    x: int
    y: int
    w: int
    h: int
    action: str = "comment"
    item_req: str = "(none)"
    scale_png: int = 100
    is_locked: bool = False
    comments: list = field(default_factory=list)
    target_room: str = "(none)"
    flow: dict = field(default_factory=lambda: {"p_com": True, "h_com": False, "unlock": False, "swap": False, "move": False})
    description: str = ""

@dataclass
class WalkableArea:
    id: str
    points: list = field(default_factory=list)
    scale_min: int = 100
    scale_max: int = 100

class GamifikatorProject:
    def __init__(self, name="Nowy Projekt", resolution="1920x1080"):
        self.name = name
        self.resolution = resolution
        self.rooms = {} 
        self.items = {}
        self.player = {
            "animations": {
                "idle": {"path": "", "flip": False},
                "walk_r": {"path": "", "flip": False},
                "walk_u": {"path": "", "flip": False},
                "walk_d": {"path": "", "flip": False}
            },
            "walk_speed": 5,
            "scale": 100
        }

    def to_json(self):
        def d_conv(o):
            if isinstance(o, (Hotpoint, WalkableArea)): return o.__dict__
            if isinstance(o, list): return [d_conv(i) for i in o]
            if isinstance(o, dict): return {k: d_conv(v) for k, v in o.items()}
            return o
        data = self.__dict__.copy()
        data["rooms"] = d_conv(self.rooms)
        return json.dumps(data, indent=4)

    @classmethod
    def from_json(cls, data_str):
        d = json.loads(data_str)
        proj = cls(d.get("name", "Brak"), d.get("resolution", "1920x1080"))
        proj.items = d.get("items", {})
        proj.player = d.get("player", proj.player)
        for rid, rdata in d.get("rooms", {}).items():
            room = {
                "name": rdata["name"],
                "background": rdata["background"],
                "player_pos": rdata.get("player_pos", [960, 540]),
                "hotpoints": [Hotpoint(**hp) for hp in rdata.get("hotpoints", [])],
                "walkable": [WalkableArea(**wa) for wa in rdata.get("walkable", [])]
            }
            proj.rooms[rid] = room
        return proj
