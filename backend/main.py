from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import os, json, serial.tools.list_ports

from machine_manager import MachineManager

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

manager = MachineManager()

CAMERAS_FILE = "data/cameras.json"
CALIB_FILE   = "data/calibrations.json"

os.makedirs("data", exist_ok=True)

# ─── Helpers JSON ─────────────────────────────────────────────────────────

def _load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ─── Machines ─────────────────────────────────────────────────────────────

class MachineConfig(BaseModel):
    name: str
    type: str = "laser"
    port: str = ""
    baudrate: int = 115200
    sim: bool = False
    limites: dict = {"x": 300, "y": 300, "z": 50}
    laser_power_max: int = 1000
    vitesse_gravure_max: int = 3000
    broche_max: int = 24000
    vitesse_fraisage_max: int = 2000
    camera_surveillance_id: Optional[str] = None
    camera_positionnement_id: Optional[str] = None

@app.get("/machines")
def list_machines():
    return manager.list()

@app.post("/machines")
def add_machine(config: MachineConfig):
    m = manager.add(config.dict())
    return m.to_dict()

@app.put("/machines/{machine_id}")
def update_machine(machine_id: str, config: MachineConfig):
    m = manager.update(machine_id, config.dict())
    if not m:
        raise HTTPException(404, "Machine introuvable")
    return m.to_dict()

@app.delete("/machines/{machine_id}")
def delete_machine(machine_id: str):
    if not manager.delete(machine_id):
        raise HTTPException(404, "Machine introuvable")
    return {"ok": True}

@app.post("/machines/{machine_id}/connect")
async def connect_machine(machine_id: str):
    m = manager.get(machine_id)
    if not m: raise HTTPException(404, "Machine introuvable")
    await m.connect()
    return m.to_dict()

@app.post("/machines/{machine_id}/disconnect")
async def disconnect_machine(machine_id: str):
    m = manager.get(machine_id)
    if not m: raise HTTPException(404, "Machine introuvable")
    await m.disconnect()
    return m.to_dict()

@app.post("/machines/{machine_id}/command")
async def send_command(machine_id: str, body: dict):
    m = manager.get(machine_id)
    if not m: raise HTTPException(404, "Machine introuvable")
    await m.send_command(body.get("command", ""))
    return {"ok": True}

@app.post("/machines/{machine_id}/stop")
async def stop_machine(machine_id: str):
    m = manager.get(machine_id)
    if not m: raise HTTPException(404, "Machine introuvable")
    await m.stop()
    return {"ok": True}

@app.post("/machines/{machine_id}/pause")
async def pause_machine(machine_id: str):
    m = manager.get(machine_id)
    if not m: raise HTTPException(404, "Machine introuvable")
    m._paused = True
    m._pause_event.clear()
    m.state = "Hold"
    await m._broadcast({"type": "status", "data": m._status_payload()})
    await m._log("⏸ Gravure en pause")
    return {"ok": True}

@app.post("/machines/{machine_id}/resume")
async def resume_machine(machine_id: str):
    m = manager.get(machine_id)
    if not m: raise HTTPException(404, "Machine introuvable")
    m._paused = False
    m._pause_event.set()
    m.state = "Run"
    await m._broadcast({"type": "status", "data": m._status_payload()})
    await m._log("▶ Gravure reprise")
    return {"ok": True}

@app.post("/machines/{machine_id}/mode/{mode}")
async def set_mode(machine_id: str, mode: str):
    m = manager.get(machine_id)
    if not m: raise HTTPException(404, "Machine introuvable")
    if mode not in ("cnc", "laser"): raise HTTPException(400, "Mode invalide")
    m.mode_actif = mode
    await m.send_setting("$32", "1" if mode == "laser" else "0")
    await m._broadcast({"type": "mode", "mode": mode})
    return {"ok": True, "mode": mode}

# ─── Fichiers GCode ───────────────────────────────────────────────────────

@app.get("/machines/{machine_id}/files")
def list_files(machine_id: str):
    return manager.list_files(machine_id)

@app.post("/machines/{machine_id}/upload")
async def upload_file(machine_id: str, file: UploadFile = File(...)):
    path = manager.file_path(machine_id, file.filename)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    return {"ok": True, "filename": file.filename, "size": len(content)}

@app.get("/machines/{machine_id}/files/{filename}/content")
def file_content(machine_id: str, filename: str):
    path = manager.file_path(machine_id, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Fichier introuvable")
    with open(path) as f:
        return {"content": f.read()}

@app.delete("/machines/{machine_id}/files/{filename}")
def delete_file(machine_id: str, filename: str):
    if not manager.delete_file(machine_id, filename):
        raise HTTPException(404, "Fichier introuvable")
    return {"ok": True}

@app.post("/machines/{machine_id}/run/{filename}")
async def run_file(machine_id: str, filename: str):
    m = manager.get(machine_id)
    if not m: raise HTTPException(404, "Machine introuvable")
    path = manager.file_path(machine_id, filename)
    if not os.path.exists(path): raise HTTPException(404, "Fichier introuvable")
    await m.run_file(path, filename)
    return {"ok": True}

@app.get("/machines/{machine_id}/settings")
async def get_settings(machine_id: str):
    m = manager.get(machine_id)
    if not m: raise HTTPException(404, "Machine introuvable")
    await m.load_settings()
    return {"ok": True}

@app.post("/machines/{machine_id}/settings")
async def post_setting(machine_id: str, body: dict):
    m = manager.get(machine_id)
    if not m: raise HTTPException(404, "Machine introuvable")
    await m.send_setting(body.get("key"), body.get("value"))
    return {"ok": True}

# ─── Calibration ──────────────────────────────────────────────────────────

@app.get("/machines/{machine_id}/calibration")
def get_calibration(machine_id: str):
    data = _load_json(CALIB_FILE, {})
    return data.get(machine_id, {})

@app.post("/machines/{machine_id}/calibration")
def save_calibration(machine_id: str, body: dict):
    data = _load_json(CALIB_FILE, {})
    data[machine_id] = body
    _save_json(CALIB_FILE, data)
    return {"ok": True}

@app.delete("/machines/{machine_id}/calibration")
def delete_calibration(machine_id: str):
    data = _load_json(CALIB_FILE, {})
    data.pop(machine_id, None)
    _save_json(CALIB_FILE, data)
    return {"ok": True}

# ─── Caméras ──────────────────────────────────────────────────────────────

class CameraConfig(BaseModel):
    id: Optional[str] = None
    name: str
    type: str = "url"          # url | usb
    url: Optional[str] = None  # pour type=url
    device_id: Optional[str] = None  # pour type=usb (deviceId navigator)
    machine_ids: list = []

@app.get("/cameras")
def list_cameras():
    return _load_json(CAMERAS_FILE, [])

@app.post("/cameras")
def add_camera(cam: CameraConfig):
    cameras = _load_json(CAMERAS_FILE, [])
    import uuid
    cam_dict = cam.dict()
    cam_dict["id"] = str(uuid.uuid4())[:8]
    cameras.append(cam_dict)
    _save_json(CAMERAS_FILE, cameras)
    return cam_dict

@app.put("/cameras/{camera_id}")
def update_camera(camera_id: str, cam: CameraConfig):
    cameras = _load_json(CAMERAS_FILE, [])
    for i, c in enumerate(cameras):
        if c["id"] == camera_id:
            cam_dict = cam.dict()
            cam_dict["id"] = camera_id
            cameras[i] = cam_dict
            _save_json(CAMERAS_FILE, cameras)
            return cam_dict
    raise HTTPException(404, "Caméra introuvable")

@app.delete("/cameras/{camera_id}")
def delete_camera(camera_id: str):
    cameras = _load_json(CAMERAS_FILE, [])
    cameras = [c for c in cameras if c["id"] != camera_id]
    _save_json(CAMERAS_FILE, cameras)
    return {"ok": True}

@app.get("/cameras/machine/{machine_id}")
def cameras_for_machine(machine_id: str):
    cameras = _load_json(CAMERAS_FILE, [])
    return [c for c in cameras if machine_id in c.get("machine_ids", [])]

# ─── Ports série ──────────────────────────────────────────────────────────

@app.get("/ports")
def list_ports():
    return [p.device for p in serial.tools.list_ports.comports()]

# ─── WebSocket ────────────────────────────────────────────────────────────

@app.websocket("/ws/{machine_id}")
async def websocket_endpoint(websocket: WebSocket, machine_id: str):
    m = manager.get(machine_id)
    if not m:
        await websocket.close(); return
    await websocket.accept()
    await m.add_client(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        m.remove_client(websocket)
