import json, os, uuid
from typing import Dict, Optional
from grbl_machine import GrblMachine

MACHINES_FILE = "data/machines.json"
FILES_DIR     = "data/files"

EXTRA_FIELDS = [
    "laser_power_max", "vitesse_gravure_max",
    "broche_max", "vitesse_fraisage_max",
    "camera_surveillance_id", "camera_positionnement_id",
]

class MachineManager:
    def __init__(self):
        self.machines: Dict[str, GrblMachine] = {}
        os.makedirs(FILES_DIR, exist_ok=True)
        self._load()

    def _load(self):
        if not os.path.exists(MACHINES_FILE):
            self._save_json({"machine_1": {
                "name": "Laser Simulateur", "type": "laser",
                "port": "", "baudrate": 115200, "sim": True,
                "limites": {"x": 300, "y": 300, "z": 50},
                "laser_power_max": 1000, "vitesse_gravure_max": 3000,
                "broche_max": 24000, "vitesse_fraisage_max": 2000,
                "camera_surveillance_id": None,
                "camera_positionnement_id": None,
            }})
        with open(MACHINES_FILE) as f:
            data = json.load(f)
        for mid, cfg in data.items():
            self.machines[mid] = GrblMachine(mid, cfg)

    def _save(self):
        data = {}
        for mid, m in self.machines.items():
            data[mid] = {
                "name": m.name, "type": m.type,
                "port": m.port, "baudrate": m.baudrate,
                "sim": m.sim, "limites": m.limites,
            }
            for f in EXTRA_FIELDS:
                data[mid][f] = getattr(m, f, None)
        self._save_json(data)

    def _save_json(self, data):
        os.makedirs(os.path.dirname(MACHINES_FILE), exist_ok=True)
        with open(MACHINES_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def list(self):
        return [m.to_dict() for m in self.machines.values()]

    def get(self, mid: str) -> Optional[GrblMachine]:
        return self.machines.get(mid)

    def add(self, config: dict) -> GrblMachine:
        mid = f"machine_{uuid.uuid4().hex[:8]}"
        m = GrblMachine(mid, config)
        self.machines[mid] = m
        self._save()
        return m

    def update(self, mid: str, config: dict) -> Optional[GrblMachine]:
        m = self.machines.get(mid)
        if not m: return None
        m.name     = config.get("name", m.name)
        m.type     = config.get("type", m.type)
        m.port     = config.get("port", m.port)
        m.baudrate = config.get("baudrate", m.baudrate)
        m.sim      = config.get("sim", m.sim)
        m.limites  = config.get("limites", m.limites)
        for f in EXTRA_FIELDS:
            if f in config:
                setattr(m, f, config[f])
        self._save()
        return m

    def delete(self, mid: str) -> bool:
        if mid not in self.machines: return False
        del self.machines[mid]
        self._save()
        return True

    def files_dir(self, mid: str) -> str:
        d = os.path.join(FILES_DIR, mid)
        os.makedirs(d, exist_ok=True)
        return d

    def list_files(self, mid: str) -> list:
        d = self.files_dir(mid)
        files = []
        for f in os.listdir(d):
            if f.endswith((".gcode",".nc",".gc",".ngc",".txt")):
                p = os.path.join(d, f)
                files.append({"name": f, "size": os.path.getsize(p), "modified": os.path.getmtime(p)})
        return sorted(files, key=lambda x: x["modified"], reverse=True)

    def file_path(self, mid: str, filename: str) -> str:
        return os.path.join(self.files_dir(mid), filename)

    def delete_file(self, mid: str, filename: str) -> bool:
        p = self.file_path(mid, filename)
        if os.path.exists(p):
            os.remove(p)
            return True
        return False
