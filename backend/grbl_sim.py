import re


class GrblSim:
    def __init__(self):
        self.pos   = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.work  = {"x": 0.0, "y": 0.0, "z": 0.0}  # offsets G92
        self.state = "Idle"
        self.relative = False
        self.settings = {
            "$0": "10", "$1": "25", "$2": "0", "$3": "0", "$4": "0",
            "$5": "0", "$6": "0", "$10": "1", "$11": "0.010", "$12": "0.002",
            "$13": "0", "$20": "0", "$21": "0", "$22": "0", "$23": "0",
            "$24": "25.000", "$25": "500.000", "$26": "250", "$27": "1.000",
            "$30": "1000", "$31": "0", "$32": "0",
            "$100": "250.000", "$101": "250.000", "$102": "250.000",
            "$110": "500.000", "$111": "500.000", "$112": "500.000",
            "$120": "10.000", "$121": "10.000", "$122": "10.000",
            "$130": "300.000", "$131": "300.000", "$132": "50.000",
        }

    def process(self, cmd: str) -> str:
        cmd = cmd.strip()
        if not cmd:
            return "ok"
        upper = cmd.upper()

        # Status report
        if upper == "?":
            x = self.pos["x"] - self.work["x"]
            y = self.pos["y"] - self.work["y"]
            z = self.pos["z"] - self.work["z"]
            return (
                f"<{self.state}|MPos:{self.pos['x']:.3f},{self.pos['y']:.3f},{self.pos['z']:.3f}"
                f"|WPos:{x:.3f},{y:.3f},{z:.3f}|Bf:15,128|FS:0,0>"
            )

        # Settings dump
        if upper == "$$":
            return "\n".join(f"{k}={v}" for k, v in self.settings.items()) + "\nok"

        # Soft reset
        if cmd == "\x18":
            self.state = "Idle"
            self.relative = False
            return "Grbl 1.1h ['$' for help]"

        # Feed hold / resume / unlock
        if upper == "!":
            self.state = "Hold"
            return "ok"
        if upper == "~":
            self.state = "Idle"
            return "ok"
        if upper == "$X":
            self.state = "Idle"
            return "ok"

        # Homing cycle — simule un retour à X0 Y0 Z0
        if upper == "$H":
            self.pos  = {"x": 0.0, "y": 0.0, "z": 0.0}
            self.work = {"x": 0.0, "y": 0.0, "z": 0.0}
            self.state = "Idle"
            return "ok"

        # Jog
        if upper.startswith("$J="):
            self._apply_move(cmd[3:], force_relative=True)
            return "ok"

        # G92 — définir offset de travail
        if upper.startswith("G92"):
            rest = upper[3:]
            if not rest.strip():
                # G92 seul = reset offsets
                self.work = {"x": 0.0, "y": 0.0, "z": 0.0}
            else:
                mx = re.search(r'X([-\d.]+)', rest)
                my = re.search(r'Y([-\d.]+)', rest)
                mz = re.search(r'Z([-\d.]+)', rest)
                # G92 Xn = "la position actuelle est Xn en coords travail"
                # donc offset = pos_machine - valeur_demandée
                if mx: self.work["x"] = self.pos["x"] - float(mx.group(1))
                if my: self.work["y"] = self.pos["y"] - float(my.group(1))
                if mz: self.work["z"] = self.pos["z"] - float(mz.group(1))
            return "ok"

        # G90 / G91 — mode absolu/relatif
        if "G90" in upper and not upper.startswith("G90."):
            self.relative = False
            # peut aussi contenir un move sur la même ligne
        if "G91" in upper and not upper.startswith("G91."):
            self.relative = True

        # G0, G1, G2, G3 — mouvement (avec ou sans espace après Gxx)
        if re.search(r'G0*[0123]\b', upper):
            self._apply_move(cmd)
            return "ok"

        # G38.2 — Z probe simulé : descend de 10mm et s'arrête
        if upper.startswith("G38"):
            mz = re.search(r'Z([-\d.]+)', upper)
            if mz:
                dist = float(mz.group(1))
                # Simuler contact après 10mm max
                self.pos["z"] = max(self.pos["z"] + max(dist, -10), 0)
            return "ok"

        # Setting $N=V
        match = re.match(r'\$(\d+)=([\d.]+)', cmd)
        if match:
            self.settings[f"${match.group(1)}"] = match.group(2)
            return "ok"

        return "ok"

    def _apply_move(self, cmd: str, force_relative: bool = False):
        upper = cmd.upper()
        is_rel = force_relative or self.relative

        # Détecter G91/G90 inline
        if "G91" in upper:
            is_rel = True
        if "G90" in upper:
            is_rel = False

        mx = re.search(r'X([-\d.]+)', upper)
        my = re.search(r'Y([-\d.]+)', upper)
        mz = re.search(r'Z([-\d.]+)', upper)

        if mx:
            v = float(mx.group(1))
            self.pos["x"] = (self.pos["x"] + v) if is_rel else (self.work["x"] + v)
        if my:
            v = float(my.group(1))
            self.pos["y"] = (self.pos["y"] + v) if is_rel else (self.work["y"] + v)
        if mz:
            v = float(mz.group(1))
            self.pos["z"] = (self.pos["z"] + v) if is_rel else (self.work["z"] + v)
