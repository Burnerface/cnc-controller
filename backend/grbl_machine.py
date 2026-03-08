import asyncio, re, serial
from datetime import datetime
from typing import Optional, Set
from fastapi import WebSocket


class GrblMachine:
    def __init__(self, machine_id: str, config: dict):
        self.id         = machine_id
        self.name       = config.get("name", machine_id)
        self.type       = config.get("type", "cnc")
        self.port       = config.get("port", "")
        self.baudrate   = config.get("baudrate", 115200)
        self.sim        = config.get("sim", False)
        self.limites    = config.get("limites", {"x": 300, "y": 300, "z": 50})
        self.mode_actif = config.get("type", "cnc")
        self.laser_power_max           = config.get("laser_power_max", 1000)
        self.vitesse_gravure_max       = config.get("vitesse_gravure_max", 3000)
        self.broche_max                = config.get("broche_max", 24000)
        self.vitesse_fraisage_max      = config.get("vitesse_fraisage_max", 2000)
        self.camera_surveillance_id    = config.get("camera_surveillance_id", None)
        self.camera_positionnement_id  = config.get("camera_positionnement_id", None)

        self.serial: Optional[serial.Serial] = None
        self.connected = False
        self.state     = "Disconnected"
        self.position  = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.job       = {"actif": False, "fichier": None, "progression": 0}
        self._sim      = None
        self._paused   = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._ws_clients: Set[WebSocket] = set()
        self._read_task   = None
        self._status_task = None
        self._gcode_task  = None

    async def add_client(self, ws: WebSocket):
        self._ws_clients.add(ws)
        await self._send(ws, {"type": "status", "data": self._status_payload()})

    def remove_client(self, ws: WebSocket):
        self._ws_clients.discard(ws)

    async def _broadcast(self, msg: dict):
        dead = set()
        for ws in self._ws_clients:
            try: await ws.send_json(msg)
            except: dead.add(ws)
        self._ws_clients -= dead

    async def _send(self, ws, msg):
        try: await ws.send_json(msg)
        except: pass

    async def connect(self):
        if self.connected: return
        if self.sim:
            from grbl_sim import GrblSim
            self._sim = GrblSim()
            self.connected = True; self.state = "Idle"
            await self._broadcast({"type": "status", "data": self._status_payload()})
            await self._log("Simulateur connecté")
            self._status_task = asyncio.create_task(self._poll_status())
            return
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            await asyncio.sleep(2); self.serial.flushInput()
            self.connected = True; self.state = "Idle"
            await self._broadcast({"type": "status", "data": self._status_payload()})
            await self._log(f"Connecté sur {self.port} @ {self.baudrate}")
            self._read_task   = asyncio.create_task(self._read_serial())
            self._status_task = asyncio.create_task(self._poll_status())
        except Exception as e:
            await self._broadcast({"type": "error", "message": str(e)}); raise

    async def disconnect(self):
        for t in [self._gcode_task, self._status_task, self._read_task]:
            if t: t.cancel()
        if self.serial and self.serial.is_open: self.serial.close()
        self.serial = None; self._sim = None
        self.connected = False; self.state = "Disconnected"
        self.job = {"actif": False, "fichier": None, "progression": 0}
        self._paused = False; self._pause_event.set()
        await self._broadcast({"type": "status", "data": self._status_payload()})
        await self._log("Déconnecté")

    async def send_command(self, cmd: str):
        cmd = cmd.strip()
        if not cmd: return
        await self._log(f"> {cmd}")
        if self.sim and self._sim:
            response = self._sim.process(cmd)
            for line in response.split("\n"):
                line = line.strip()
                if line and line != "ok":
                    self._parse_response(line); await self._log(line)
            await self._broadcast({"type": "status", "data": self._status_payload()}); return
        if self.serial and self.serial.is_open:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.serial.write((cmd+"\n").encode()))

    async def stop(self):
        self._paused = False; self._pause_event.set()
        if self._gcode_task: self._gcode_task.cancel(); self._gcode_task = None
        self.job = {"actif": False, "fichier": None, "progression": 0}
        self.state = "Idle"
        await self._broadcast({"type": "status", "data": self._status_payload()})
        await self._log("⛔ Arrêt d'urgence")
        if not self.sim and self.serial and self.serial.is_open:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.serial.write(b"\x18"))

    async def run_file(self, filepath: str, filename: str):
        if self.job["actif"]: raise Exception("Tâche déjà en cours")
        with open(filepath) as f:
            lines = [l.strip() for l in f if l.strip() and not l.strip().startswith(";")]
        self._paused = False; self._pause_event.set()
        self.job = {"actif": True, "fichier": filename, "progression": 0}
        self.state = "Run"
        await self._broadcast({"type": "status", "data": self._status_payload()})
        self._gcode_task = asyncio.create_task(self._execute_gcode(lines))

    async def _execute_gcode(self, lines):
        total = len(lines)
        try:
            for i, line in enumerate(lines):
                if not self.connected: break
                await self._pause_event.wait()
                await self.send_command(line)
                await asyncio.sleep(0.02)
                self.job["progression"] = int((i+1)/total*100)
                await self._broadcast({"type": "status", "data": self._status_payload()})
        except asyncio.CancelledError: pass
        finally:
            self.job = {"actif": False, "fichier": None, "progression": 0}
            self._paused = False; self._pause_event.set(); self.state = "Idle"
            await self._broadcast({"type": "status", "data": self._status_payload()})
            await self._log("✓ Exécution terminée")

    async def _read_serial(self):
        loop = asyncio.get_event_loop()
        while self.connected and self.serial and self.serial.is_open:
            try:
                line = await loop.run_in_executor(None, self.serial.readline)
                line = line.decode("utf-8", errors="ignore").strip()
                if line:
                    self._parse_response(line); await self._log(line)
                    await self._broadcast({"type": "status", "data": self._status_payload()})
            except: await asyncio.sleep(0.1)

    async def _poll_status(self):
        while self.connected:
            if not self.sim and self.serial and self.serial.is_open:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: self.serial.write(b"?"))
            elif self.sim and self._sim:
                self._parse_response(self._sim.process("?"))
                await self._broadcast({"type": "status", "data": self._status_payload()})
            await asyncio.sleep(0.5)

    def _parse_response(self, line: str):
        m = re.match(r"<(\w+)[|,].*?MPos:([-\d.]+),([-\d.]+),([-\d.]+)", line)
        if m:
            self.state = m.group(1)
            self.position = {"x": float(m.group(2)), "y": float(m.group(3)), "z": float(m.group(4))}

    async def load_settings(self): await self.send_command("$$")
    async def send_setting(self, key, value): await self.send_command(f"{key}={value}")

    def _status_payload(self):
        return {"connected": self.connected, "state": self.state,
                "position": self.position, "job": self.job}

    async def _log(self, msg):
        await self._broadcast({"type": "log",
            "data": {"time": datetime.now().strftime("%H:%M:%S"), "message": msg}})

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "type": self.type,
            "port": self.port, "baudrate": self.baudrate,
            "sim": self.sim, "connected": self.connected, "state": self.state,
            "limites": self.limites, "mode_actif": self.mode_actif,
            "laser_power_max": self.laser_power_max,
            "vitesse_gravure_max": self.vitesse_gravure_max,
            "broche_max": self.broche_max,
            "vitesse_fraisage_max": self.vitesse_fraisage_max,
            "camera_surveillance_id": self.camera_surveillance_id,
            "camera_positionnement_id": self.camera_positionnement_id,
        }
