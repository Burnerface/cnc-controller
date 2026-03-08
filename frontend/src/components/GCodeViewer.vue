<template>
  <v-card color="surface-variant" rounded="lg" elevation="0" style="height:100%">
    <v-card-title class="text-caption text-medium-emphasis py-2 px-3 d-flex align-center">
      <v-icon size="small" class="mr-1">mdi-vector-polyline</v-icon>
      VISUALISEUR GCODE
      <v-spacer />
      <span v-if="fichierCharge" class="text-caption text-primary mr-2">{{ fichierCharge }}</span>
      <span v-if="store.job.actif" class="text-caption text-success mr-2">{{ store.job.progression }}%</span>

      <v-btn :icon="showCamera ? 'mdi-camera' : 'mdi-camera-outline'"
        :color="showCamera ? 'primary' : 'default'" variant="text" size="x-small"
        :disabled="!hasCamera" @click="showCamera = !showCamera" />

      <v-menu v-if="showCamera" :close-on-content-click="false">
        <template #activator="{ props: mp }">
          <v-btn icon="mdi-opacity" variant="text" size="x-small" v-bind="mp" />
        </template>
        <v-card color="surface" class="pa-3" width="180">
          <div class="text-caption mb-1">Opacité caméra</div>
          <v-slider v-model="cameraOpacity" min="0.05" max="1" step="0.05" color="primary" hide-details />
          <div class="text-caption mt-2 mb-1">Opacité GCode</div>
          <v-slider v-model="gcodeOpacity" min="0.1" max="1" step="0.05" color="primary" hide-details />
        </v-card>
      </v-menu>

      <v-btn
        :icon="modeCalib ? 'mdi-map-marker-plus' : 'mdi-map-marker-outline'"
        :color="modeCalib ? 'error' : (calibrated ? 'success' : 'default')"
        variant="text" size="x-small"
        :title="calibrated ? 'Recalibrer' : 'Calibrer (2 points)'"
        @click="demanderCalib" />

      <v-btn
        :icon="modeDeplacement ? 'mdi-cursor-move' : 'mdi-cursor-default'"
        :color="modeDeplacement ? 'warning' : 'default'"
        variant="text" size="x-small"
        :disabled="store.job.actif || !fichierCharge"
        @click="modeDeplacement = !modeDeplacement; modeZero = false; modeCalib = false" />

      <v-btn
        :icon="modeZero ? 'mdi-crosshairs-gps' : 'mdi-crosshairs'"
        :color="modeZero ? 'warning' : 'default'"
        variant="text" size="x-small"
        @click="modeZero = !modeZero; modeDeplacement = false; modeCalib = false" />

      <v-btn v-if="fichierCharge" icon="mdi-close" variant="text" size="x-small"
        color="error" :disabled="store.job.actif" @click="decharger" />

      <v-btn icon="mdi-fit-to-screen" variant="text" size="x-small" @click="resetZoom" />
    </v-card-title>
    <v-divider />
    <v-progress-linear v-if="store.job.actif"
      :model-value="store.job.progression" color="primary" height="2" />

    <v-alert v-if="horsLimites" type="error" variant="tonal" density="compact"
      class="mx-3 mt-2 mb-0 text-caption" icon="mdi-alert">
      Le GCode dépasse les limites de la machine
    </v-alert>

    <!-- Barre actions -->
    <div v-if="fichierCharge" class="action-bar px-3 py-2 d-flex align-center gap-2 flex-wrap">
      <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-play-speed"
        :disabled="simRunning || store.job.actif" :loading="simRunning"
        @click="simuler">Simuler</v-btn>
      <v-btn v-if="simRunning" size="small" variant="tonal" color="warning"
        prepend-icon="mdi-stop" @click="stopSim">Arrêter sim</v-btn>
      <v-divider vertical class="mx-1" />
      <v-btn size="small" variant="tonal" color="secondary" prepend-icon="mdi-crosshairs"
        :disabled="!store.connected || store.job.actif"
        @click="allerAuZero">Aller au zéro</v-btn>
      <v-btn v-if="!store.job.actif" size="small" variant="flat" color="success"
        prepend-icon="mdi-laser-pointer"
        :disabled="!store.connected || horsLimites"
        @click="showConfirmGravure = true">Graver</v-btn>
      <template v-if="store.job.actif">
        <v-btn v-if="!jobPaused" size="small" variant="tonal" color="warning"
          prepend-icon="mdi-pause" @click="pauseGravure">Pause</v-btn>
        <v-btn v-else size="small" variant="flat" color="success"
          prepend-icon="mdi-play" @click="reprendreGravure">Reprendre</v-btn>
      </template>
      <v-btn size="small" variant="flat" color="error" prepend-icon="mdi-stop"
        :disabled="!store.job.actif && !jobPaused"
        @click="showConfirmStop = true">Stop</v-btn>
      <v-spacer />
      <span class="text-caption text-medium-emphasis">
        Zéro: X{{ zeroOffset.x.toFixed(2) }} Y{{ zeroOffset.y.toFixed(2) }}
      </span>
    </div>

    <div ref="containerRef" class="viewer-outer"
      :class="[cursorClass, { 'border-error': horsLimites }]"
      @wheel.prevent="onWheel"
      @mousedown="onMouseDown"
      @mousemove="onMouseMove"
      @mouseup="onMouseUp"
      @mouseleave="onMouseUp"
      @click="onViewerClick">

      <div ref="worldRef" class="viewer-world" :style="worldStyle">
        <img v-if="showCamera && activeCameraUrl"
          :src="activeCameraUrl" class="camera-img"
          :style="{ opacity: cameraOpacity }" alt="" />
        <video v-if="showCamera && !activeCameraUrl && usbStream"
          ref="videoRef" class="camera-img"
          :style="{ opacity: cameraOpacity }"
          autoplay playsinline muted />

        <canvas ref="canvasLimites" class="canvas-abs" />
        <canvas ref="canvasGcode"   class="canvas-abs"
          :style="{ opacity: gcodeOpacity, transform: gcodeTransform }" />
        <!-- Simulation sur canvas séparé, même transform que gcode -->
        <canvas ref="canvasSim"     class="canvas-abs"
          :style="{ transform: gcodeTransform }" />
        <canvas ref="canvasHead"    class="canvas-abs" />

        <template v-if="modeCalib || calibrated">
          <div v-if="calib.p0" class="calib-marker"
            :style="{ left: calib.p0.wx+'px', top: calib.p0.wy+'px' }">
            <div class="calib-cross p0-cross" />
            <span class="calib-label p0-label">X0 Y0</span>
          </div>
          <div v-if="calib.p1" class="calib-marker"
            :style="{ left: calib.p1.wx+'px', top: calib.p1.wy+'px' }">
            <div class="calib-cross p1-cross" />
            <span class="calib-label p1-label">X{{ lim?.x }} Y{{ lim?.y }}</span>
          </div>
        </template>
      </div>

      <div v-if="modeCalib" class="mode-hint error-hint">
        <v-icon color="error" size="small" class="mr-1">mdi-map-marker-plus</v-icon>
        <span v-if="calibStep === 0">Étape 1/2 — Cliquez sur <strong>X0 Y0</strong></span>
        <span v-else>Étape 2/2 — Cliquez sur <strong>Xmax Ymax</strong></span>
      </div>
      <div v-else-if="modeZero" class="mode-hint warning-hint">
        <v-icon color="warning" size="small" class="mr-1">mdi-crosshairs-gps</v-icon>
        Cliquez pour définir le zéro de travail
      </div>
      <div v-else-if="modeDeplacement" class="mode-hint info-hint">
        <v-icon color="info" size="small" class="mr-1">mdi-cursor-move</v-icon>
        Glissez le GCode pour le repositionner
      </div>

      <!-- Vitesse simulation -->
      <div v-if="simRunning" class="sim-speed-control">
        <v-icon size="small" color="warning" class="mr-1">mdi-play-speed</v-icon>
        <span class="text-caption mr-2">Vitesse</span>
        <v-slider v-model="simSpeed" min="1" max="20" step="1"
          color="warning" hide-details density="compact" style="width:100px" />
        <span class="text-caption ml-1">×{{ simSpeed }}</span>
      </div>

      <div v-if="calibrated && !modeCalib" class="calib-info">
        <v-icon size="x-small" color="success" class="mr-1">mdi-check-circle</v-icon>
        {{ calibScaleX.toFixed(2) }} px/mm
      </div>

      <div v-if="!parsedPaths.length && !showCamera" class="canvas-empty">
        <v-icon size="32" class="mb-2">mdi-file-outline</v-icon>
        <div>Chargez un fichier GCode</div>
      </div>
    </div>

    <!-- Dialog recalibration -->
    <v-dialog v-model="showConfirmRecalib" max-width="380">
      <v-card color="surface" rounded="lg">
        <v-card-title class="py-3 px-4 d-flex align-center">
          <v-icon color="warning" class="mr-2">mdi-map-marker-alert</v-icon>
          Recalibrer ?
        </v-card-title>
        <v-card-text class="pa-4">
          Une calibration existe déjà. La remplacer effacera le positionnement actuel.
        </v-card-text>
        <v-card-actions class="px-4 pb-4">
          <v-btn variant="text" @click="showConfirmRecalib = false">Annuler</v-btn>
          <v-spacer />
          <v-btn color="warning" variant="flat" @click="startCalib">Recalibrer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Dialog gravure -->
    <v-dialog v-model="showConfirmGravure" max-width="440">
      <v-card color="surface" rounded="lg">
        <v-card-title class="py-3 px-4 d-flex align-center">
          <v-icon color="warning" class="mr-2">mdi-alert</v-icon>
          Confirmation avant gravure
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <v-alert type="warning" variant="tonal" density="compact" class="mb-3">
            Vérifiez les points suivants avant de démarrer
          </v-alert>
          <v-checkbox v-model="checks.piece"       color="success" hide-details density="compact" label="La pièce est correctement positionnée" class="mb-1" />
          <v-checkbox v-model="checks.lunettes"    color="success" hide-details density="compact" label="Les lunettes de protection sont portées" class="mb-1" />
          <v-checkbox v-model="checks.ventilation" color="success" hide-details density="compact" label="La ventilation / extraction est active"  class="mb-1" />
          <v-checkbox v-model="checks.zone"        color="success" hide-details density="compact" label="La zone de travail est dégagée"           class="mb-1" />
          <v-divider class="my-3" />
          <div class="text-caption text-medium-emphasis">
            Fichier : <strong class="text-white">{{ fichierCharge }}</strong><br/>
            Zéro : X{{ zeroOffset.x.toFixed(2) }} Y{{ zeroOffset.y.toFixed(2) }}
          </div>
        </v-card-text>
        <v-card-actions class="px-4 pb-4">
          <v-btn variant="text" @click="showConfirmGravure = false">Annuler</v-btn>
          <v-spacer />
          <v-btn color="success" variant="flat" prepend-icon="mdi-laser-pointer"
            :disabled="!tousChecks" @click="lancerGravure">Démarrer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Dialog stop -->
    <v-dialog v-model="showConfirmStop" max-width="360">
      <v-card color="surface" rounded="lg">
        <v-card-title class="py-3 px-4 d-flex align-center">
          <v-icon color="error" class="mr-2">mdi-stop-circle</v-icon>
          Arrêt d'urgence
        </v-card-title>
        <v-card-text class="pa-4">Voulez-vous vraiment stopper la gravure en cours ?</v-card-text>
        <v-card-actions class="px-4 pb-4">
          <v-btn variant="text" @click="showConfirmStop = false">Annuler</v-btn>
          <v-spacer />
          <v-btn color="error" variant="flat" @click="stopUrgence">Stopper</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackZero"  timeout="2000" color="success" location="bottom">
      Zéro défini : X{{ zeroOffset.x.toFixed(2) }} Y{{ zeroOffset.y.toFixed(2) }}
    </v-snackbar>
    <v-snackbar v-model="snackCalib" timeout="3000" color="info" location="bottom">
      Calibration OK — {{ calibScaleX.toFixed(2) }} × {{ calibScaleY.toFixed(2) }} px/mm
    </v-snackbar>
  </v-card>
</template>

<script setup>
import { ref, watch, computed, onMounted, onUnmounted, reactive, nextTick } from 'vue'
import { useMachineStore } from '../stores/machine'

const store = useMachineStore()

const containerRef  = ref(null)
const worldRef      = ref(null)
const canvasLimites = ref(null)
const canvasGcode   = ref(null)
const canvasSim     = ref(null)
const canvasHead    = ref(null)
const videoRef      = ref(null)

const fichierCharge       = ref(null)
const showCamera          = ref(false)
const cameraOpacity       = ref(0.6)
const gcodeOpacity        = ref(0.9)
const modeCalib           = ref(false)
const calibStep           = ref(0)
const modeZero            = ref(false)
const modeDeplacement     = ref(false)
const zeroOffset          = ref({ x: 0, y: 0 })
const snackZero           = ref(false)
const snackCalib          = ref(false)
const showConfirmRecalib  = ref(false)
const showConfirmGravure  = ref(false)
const showConfirmStop     = ref(false)
const jobPaused           = ref(false)
const simRunning          = ref(false)
const simSpeed            = ref(5)
const allCameras          = ref([])
const usbStream           = ref(null)
const checks = reactive({ piece: false, lunettes: false, ventilation: false, zone: false })
const tousChecks = computed(() => Object.values(checks).every(Boolean))

const lim = computed(() => store.machineActive?.limites || null)

// ─── Caméra ───────────────────────────────────────────────────────────────
const activeCameraUrl = computed(() => {
  if (!store.machineActive?.camera_positionnement_id) return null
  const cam = allCameras.value.find(c => c.id === store.machineActive.camera_positionnement_id)
  return cam?.type === 'url' ? cam.url : null
})
const activeCameraUsb = computed(() => {
  if (!store.machineActive?.camera_positionnement_id) return null
  const cam = allCameras.value.find(c => c.id === store.machineActive.camera_positionnement_id)
  return cam?.type === 'usb' ? cam.device_id : null
})
const hasCamera = computed(() => !!activeCameraUrl.value || !!activeCameraUsb.value)

async function loadCameras() {
  const res = await fetch('/api/cameras')
  allCameras.value = await res.json()
}

watch([showCamera, activeCameraUsb], async ([show, deviceId]) => {
  if (show && deviceId) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia(
        deviceId ? { video: { deviceId: { exact: deviceId } } } : { video: true }
      )
      usbStream.value = stream
      if (videoRef.value) videoRef.value.srcObject = stream
    } catch (e) { console.error('USB cam error', e) }
  } else if (!show && usbStream.value) {
    usbStream.value.getTracks().forEach(t => t.stop())
    usbStream.value = null
  }
})
watch(videoRef, el => { if (el && usbStream.value) el.srcObject = usbStream.value })

// ─── Calibration ──────────────────────────────────────────────────────────
const calib      = reactive({ p0: null, p1: null })
const calibrated = ref(false)
const CALIB_KEY  = computed(() => `calib_${store.machineActiveId}`)

function loadCalibFromStorage() {
  try {
    const raw = localStorage.getItem(CALIB_KEY.value)
    if (raw) {
      const data = JSON.parse(raw)
      calib.p0 = data.p0; calib.p1 = data.p1
      calibrated.value = !!(data.p0 && data.p1)
    } else {
      calib.p0 = null; calib.p1 = null; calibrated.value = false
    }
  } catch { calibrated.value = false }
}

function saveCalibToStorage() {
  localStorage.setItem(CALIB_KEY.value, JSON.stringify({ p0: calib.p0, p1: calib.p1 }))
  fetch(`/api/machines/${store.machineActiveId}/calibration`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ p0: calib.p0, p1: calib.p1 }),
  })
}

function demanderCalib() {
  if (calibrated.value) showConfirmRecalib.value = true
  else startCalib()
}

function startCalib() {
  showConfirmRecalib.value = false
  modeCalib.value = true; calibStep.value = 0
  calib.p0 = null; calib.p1 = null; calibrated.value = false
  modeDeplacement.value = false; modeZero.value = false
}

const calibScaleX = computed(() => {
  if (!calib.p0 || !calib.p1 || !lim.value?.x) return 1
  return Math.abs(calib.p1.wx - calib.p0.wx) / lim.value.x
})
const calibScaleY = computed(() => {
  if (!calib.p0 || !calib.p1 || !lim.value?.y) return 1
  return Math.abs(calib.p1.wy - calib.p0.wy) / lim.value.y
})

// ─── Zoom / Pan ───────────────────────────────────────────────────────────
const zoom  = ref(1)
const panX  = ref(0)
const panY  = ref(0)
const worldStyle = computed(() => ({
  transform: `translate(${panX.value}px, ${panY.value}px) scale(${zoom.value})`,
  transformOrigin: '0 0',
}))

const gcodeOffsetPx  = ref({ x: 0, y: 0 })
const gcodeTransform = computed(() =>
  `translate(${gcodeOffsetPx.value.x}px, ${gcodeOffsetPx.value.y}px)`
)

// ─── machine → canvas (avec fallback automatique sur les bounds GCode) ────
function machineToCanvas(mx, my) {
  const c = containerRef.value
  if (!c) return { cx: 0, cy: 0 }

  // Mode calibré : utiliser les 2 points de référence
  if (calibrated.value && calib.p0 && calib.p1) {
    return {
      cx: calib.p0.wx + mx * calibScaleX.value,
      cy: calib.p0.wy - my * calibScaleY.value,
    }
  }

  // Fallback : ajuster automatiquement sur les limites ou les bounds du GCode
  const l = lim.value
  if (l) {
    const s = Math.min(
      (c.clientWidth  - 80) / l.x,
      (c.clientHeight - 80) / l.y
    )
    const marginX = 40
    const marginY = 40 + (c.clientHeight - 80 - l.y * s) / 2
    return {
      cx: marginX + mx * s,
      cy: c.clientHeight - marginY - my * s,
    }
  }

  // Fallback sans limites : utiliser les bounds du GCode
  if (gcodeReady) {
    const bw = gcodeBounds.maxX - gcodeBounds.minX || 1
    const bh = gcodeBounds.maxY - gcodeBounds.minY || 1
    const s = Math.min(
      (c.clientWidth  - 80) / bw,
      (c.clientHeight - 80) / bh
    )
    const marginX = 40
    const marginY = 40
    return {
      cx: marginX + (mx - gcodeBounds.minX) * s,
      cy: c.clientHeight - marginY - (my - gcodeBounds.minY) * s,
    }
  }

  return { cx: mx, cy: my }
}

// ─── Hors limites ─────────────────────────────────────────────────────────
const horsLimites = computed(() => {
  if (!parsedPaths.length || !lim.value) return false
  const l = lim.value
  const offX = calibrated.value ?  gcodeOffsetPx.value.x / calibScaleX.value : 0
  const offY = calibrated.value ? -gcodeOffsetPx.value.y / calibScaleY.value : 0
  return parsedPaths.some(p => {
    const x = p.x + offX, y = p.y + offY
    return x < 0 || x > l.x || y < 0 || y > l.y
  })
})

// ─── Parsing ──────────────────────────────────────────────────────────────
let parsedPaths  = []
let gcodeBounds  = { minX: 0, maxX: 100, minY: 0, maxY: 100 }
let gcodeReady   = false
let resizeObserver = null
let simAnimFrame   = null
let isDragging     = false
let dragStart      = { x: 0, y: 0 }
let gcodeOffsetStart = { x: 0, y: 0 }
let rafHead        = false

onMounted(() => {
  loadCameras()
  loadCalibFromStorage()
  resizeObserver = new ResizeObserver(() => { resizeCanvases(); drawAll() })
  if (containerRef.value) resizeObserver.observe(containerRef.value)
})
onUnmounted(() => {
  resizeObserver?.disconnect()
  stopSim()
  if (usbStream.value) usbStream.value.getTracks().forEach(t => t.stop())
})

watch(() => store.machineActiveId, () => {
  loadCameras(); loadCalibFromStorage(); drawAll()
})

function resizeCanvases() {
  const c = containerRef.value; if (!c) return
  const w = c.clientWidth, h = c.clientHeight
  for (const cv of [canvasLimites.value, canvasGcode.value, canvasSim.value, canvasHead.value]) {
    if (cv) { cv.width = w; cv.height = h }
  }
}

function drawAll() { drawLimites(); drawGcode(); drawHead() }

// ─── Charger GCode ────────────────────────────────────────────────────────
async function chargerGCode(filename) {
  fichierCharge.value = filename
  gcodeOffsetPx.value = { x: 0, y: 0 }
  stopSim()
  clearSimCanvas()
  const content = await store.contenuFichier(filename)
  parseGCode(content.split('\n'))
  await nextTick()
  resizeCanvases()
  drawAll()
}
defineExpose({ chargerGCode, allerAuZeroTravail })

function decharger() {
  fichierCharge.value = null; parsedPaths = []; gcodeReady = false
  gcodeOffsetPx.value = { x: 0, y: 0 }
  stopSim(); clearSimCanvas(); drawAll()
}

function parseGCode(lines) {
  parsedPaths = []
  let cx = 0, cy = 0
  let minX = Infinity, maxX = -Infinity
  let minY = Infinity, maxY = -Infinity

  for (const raw of lines) {
    const line = raw.split(';')[0].trim().toUpperCase()
    if (!line) continue
    const isRapid = /^G0*0\b/.test(line)
    const isCut   = /^G0*[123]\b/.test(line)
    if (!isRapid && !isCut) continue
    const mx = line.match(/X([-\d.]+)/), my = line.match(/Y([-\d.]+)/)
    if (mx) cx = parseFloat(mx[1])
    if (my) cy = parseFloat(my[1])
    parsedPaths.push({ x: cx, y: cy, rapid: isRapid })
    minX = Math.min(minX, cx); maxX = Math.max(maxX, cx)
    minY = Math.min(minY, cy); maxY = Math.max(maxY, cy)
  }

  if (parsedPaths.length) {
    gcodeBounds = { minX, maxX, minY, maxY }
    gcodeReady = true
  }
}

// ─── Dessins ──────────────────────────────────────────────────────────────
function drawLimites() {
  const canvas = canvasLimites.value; if (!canvas) return
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  if (!lim.value) return

  const p0 = machineToCanvas(0, 0)
  const p1 = machineToCanvas(lim.value.x, lim.value.y)

  ctx.strokeStyle = horsLimites.value ? 'rgba(255,82,82,0.8)' : 'rgba(255,184,0,0.7)'
  ctx.lineWidth = 2; ctx.setLineDash([8, 4])
  ctx.strokeRect(p0.cx, p1.cy, p1.cx - p0.cx, p0.cy - p1.cy)
  ctx.setLineDash([])
  ctx.fillStyle = horsLimites.value ? 'rgba(255,82,82,0.9)' : 'rgba(255,184,0,0.8)'
  ctx.font = '11px monospace'
  ctx.fillText(`${lim.value.x}×${lim.value.y} mm`, p0.cx + 4, p1.cy - 4)
  ctx.strokeStyle = 'rgba(255,255,255,0.1)'; ctx.lineWidth = 1
  ctx.beginPath(); ctx.moveTo(p0.cx, p0.cy); ctx.lineTo(p1.cx, p0.cy); ctx.stroke()
  ctx.beginPath(); ctx.moveTo(p0.cx, p0.cy); ctx.lineTo(p0.cx, p1.cy); ctx.stroke()
}

function drawGcode() {
  const canvas = canvasGcode.value; if (!canvas || !gcodeReady) return
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // Déplacements rapides (G0) — gris fin
  ctx.beginPath(); ctx.strokeStyle = 'rgba(255,255,255,0.15)'; ctx.lineWidth = 0.8
  let pen = false
  for (const p of parsedPaths) {
    const { cx, cy } = machineToCanvas(p.x, p.y)
    if (p.rapid) { pen ? ctx.lineTo(cx, cy) : ctx.moveTo(cx, cy); pen = true }
    else pen = false
  }
  ctx.stroke()

  // Coupes (G1/G2/G3) — cyan ou rouge si hors limites
  ctx.beginPath()
  ctx.strokeStyle = horsLimites.value ? '#FF5252' : '#00E5FF'
  ctx.lineWidth = 1.2; pen = false
  for (const p of parsedPaths) {
    const { cx, cy } = machineToCanvas(p.x, p.y)
    if (!p.rapid) { pen ? ctx.lineTo(cx, cy) : ctx.moveTo(cx, cy); pen = true }
    else pen = false
  }
  ctx.stroke()
}

// ─── Simulation accélérée ─────────────────────────────────────────────────
// Trace le parcours complet de l'outil (rapides + coupes) avec un curseur mobile
function simuler() {
  if (!parsedPaths.length) return
  stopSim()
  clearSimCanvas()
  simRunning.value = true

  const canvas = canvasSim.value
  const ctx = canvas.getContext('2d')
  let idx = 0

  function step() {
    if (!simRunning.value) return

    const stepsPerFrame = Math.max(1, Math.floor(parsedPaths.length / 800 * simSpeed.value))

    for (let i = 0; i < stepsPerFrame && idx < parsedPaths.length; i++) {
      const prev = idx > 0 ? parsedPaths[idx - 1] : null
      const curr = parsedPaths[idx]

      if (prev) {
        const { cx: x1, cy: y1 } = machineToCanvas(prev.x, prev.y)
        const { cx: x2, cy: y2 } = machineToCanvas(curr.x, curr.y)

        ctx.beginPath()
        ctx.moveTo(x1, y1)
        ctx.lineTo(x2, y2)

        if (curr.rapid) {
          // Déplacement rapide : pointillé blanc fin
          ctx.setLineDash([4, 4])
          ctx.strokeStyle = 'rgba(255,255,255,0.4)'
          ctx.lineWidth = 0.8
        } else {
          // Coupe : trait orange plein
          ctx.setLineDash([])
          ctx.strokeStyle = '#FFB800'
          ctx.lineWidth = 1.5
        }
        ctx.stroke()
        ctx.setLineDash([])
      }
      idx++
    }

    // Curseur outil courant
    if (idx < parsedPaths.length) {
      const { cx, cy } = machineToCanvas(parsedPaths[idx].x, parsedPaths[idx].y)
      // Effacer zone curseur précédent avec un petit carré
      ctx.clearRect(cx - 8, cy - 8, 16, 16)
      // Redessiner le tracé dans cette zone est complexe — on dessine juste le curseur par-dessus
      ctx.beginPath(); ctx.arc(cx, cy, 4, 0, Math.PI * 2)
      ctx.fillStyle = '#FF6B35'; ctx.fill()
      ctx.beginPath()
      ctx.moveTo(cx - 8, cy); ctx.lineTo(cx + 8, cy)
      ctx.moveTo(cx, cy - 8); ctx.lineTo(cx, cy + 8)
      ctx.strokeStyle = '#FF6B35'; ctx.lineWidth = 1.5; ctx.stroke()
    }

    if (idx >= parsedPaths.length) {
      simRunning.value = false
      // Effacer le curseur à la fin
      drawFinalCursor()
      return
    }

    simAnimFrame = requestAnimationFrame(step)
  }

  simAnimFrame = requestAnimationFrame(step)
}

function drawFinalCursor() {
  // Dessiner un checkmark à la position finale
  if (!parsedPaths.length) return
  const last = parsedPaths[parsedPaths.length - 1]
  const { cx, cy } = machineToCanvas(last.x, last.y)
  const canvas = canvasSim.value; if (!canvas) return
  const ctx = canvas.getContext('2d')
  ctx.beginPath(); ctx.arc(cx, cy, 5, 0, Math.PI * 2)
  ctx.fillStyle = '#4CAF50'; ctx.fill()
}

function stopSim() {
  if (simAnimFrame) { cancelAnimationFrame(simAnimFrame); simAnimFrame = null }
  simRunning.value = false
}

function clearSimCanvas() {
  const c = canvasSim.value
  if (c) c.getContext('2d').clearRect(0, 0, c.width, c.height)
}

// ─── Tête machine ─────────────────────────────────────────────────────────
function drawHead() {
  const canvas = canvasHead.value; if (!canvas) return
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // Marqueur zéro travail
  const { cx: zx, cy: zy } = machineToCanvas(zeroOffset.value.x, zeroOffset.value.y)
  ctx.beginPath(); ctx.arc(zx, zy, 6, 0, Math.PI * 2)
  ctx.strokeStyle = '#FFB800'; ctx.lineWidth = 1.5; ctx.stroke()
  ctx.beginPath()
  ctx.moveTo(zx-12, zy); ctx.lineTo(zx+12, zy)
  ctx.moveTo(zx, zy-12); ctx.lineTo(zx, zy+12)
  ctx.strokeStyle = '#FFB800'; ctx.stroke()

  if (!store.connected) return
  const { cx, cy } = machineToCanvas(store.position.x, store.position.y)
  ctx.beginPath(); ctx.arc(cx, cy, 5, 0, Math.PI * 2)
  ctx.fillStyle = '#FF6B35'; ctx.fill()
  ctx.beginPath()
  ctx.moveTo(cx-12, cy); ctx.lineTo(cx+12, cy)
  ctx.moveTo(cx, cy-12); ctx.lineTo(cx, cy+12)
  ctx.strokeStyle = '#FF6B35'; ctx.lineWidth = 1.5; ctx.stroke()
}

// ─── Watches ──────────────────────────────────────────────────────────────
watch(() => store.position, () => {
  if (rafHead) return; rafHead = true
  requestAnimationFrame(() => { drawHead(); rafHead = false })
}, { deep: true })
watch(() => store.job.actif, v => { if (!v) jobPaused.value = false })
watch(lim, () => { drawLimites(); drawGcode() }, { deep: true })
watch(calibrated, () => drawAll())
watch(gcodeOffsetPx, () => { drawLimites(); drawGcode() }, { deep: true })

// ─── Coords souris → monde ────────────────────────────────────────────────
function screenToWorld(ex, ey) {
  const rect = containerRef.value.getBoundingClientRect()
  return {
    wx: (ex - rect.left - panX.value) / zoom.value,
    wy: (ey - rect.top  - panY.value) / zoom.value,
  }
}

const cursorClass = computed(() => {
  if (modeCalib.value || modeZero.value) return 'cursor-crosshair'
  if (modeDeplacement.value) return 'cursor-move-mode'
  return ''
})

function onViewerClick(e) {
  if (modeCalib.value) {
    const { wx, wy } = screenToWorld(e.clientX, e.clientY)
    if (calibStep.value === 0) {
      calib.p0 = { wx, wy }; calibStep.value = 1
    } else {
      calib.p1 = { wx, wy }
      calibrated.value = true
      modeCalib.value = false; calibStep.value = 0
      saveCalibToStorage(); snackCalib.value = true
      drawAll()
    }
    return
  }
  if (modeZero.value) {
    const { wx, wy } = screenToWorld(e.clientX, e.clientY)
    let mx, my
    if (calibrated.value && calib.p0) {
      mx =  (wx - calib.p0.wx) / calibScaleX.value
      my = (calib.p0.wy - wy) / calibScaleY.value
    } else {
      const l = lim.value
      const c = containerRef.value
      if (l) {
        const s = Math.min((c.clientWidth-80)/l.x, (c.clientHeight-80)/l.y)
        mx =  (wx - 40) / s
        my = (c.clientHeight - 40 - wy) / s
      } else {
        mx = wx; my = wy
      }
    }
    zeroOffset.value = { x: parseFloat(mx.toFixed(3)), y: parseFloat(my.toFixed(3)) }
    snackZero.value = true; modeZero.value = false; drawHead()
    return
  }
}

function onMouseDown(e) {
  if (modeCalib.value || modeZero.value) return
  isDragging = true
  if (modeDeplacement.value && !store.job.actif && fichierCharge.value) {
    dragStart = { x: e.clientX, y: e.clientY }
    gcodeOffsetStart = { ...gcodeOffsetPx.value }
  } else {
    dragStart = { x: e.clientX - panX.value, y: e.clientY - panY.value }
  }
}
function onMouseMove(e) {
  if (!isDragging) return
  if (modeDeplacement.value && !store.job.actif && fichierCharge.value) {
    gcodeOffsetPx.value = {
      x: gcodeOffsetStart.x + (e.clientX - dragStart.x) / zoom.value,
      y: gcodeOffsetStart.y + (e.clientY - dragStart.y) / zoom.value,
    }
  } else {
    panX.value = e.clientX - dragStart.x
    panY.value = e.clientY - dragStart.y
  }
}
function onMouseUp() { isDragging = false }

function onWheel(e) {
  if (modeCalib.value || modeZero.value || modeDeplacement.value) return
  const f = e.deltaY < 0 ? 1.1 : 0.9
  const rect = containerRef.value.getBoundingClientRect()
  const mx = e.clientX - rect.left, my = e.clientY - rect.top
  panX.value = mx - (mx - panX.value) * f
  panY.value = my - (my - panY.value) * f
  zoom.value *= f
}

function resetZoom() { zoom.value = 1; panX.value = 0; panY.value = 0 }

// ─── Actions gravure ──────────────────────────────────────────────────────
async function lancerGravure() {
  showConfirmGravure.value = false
  checks.piece = checks.lunettes = checks.ventilation = checks.zone = false
  modeDeplacement.value = false
  const offX = calibrated.value ?  gcodeOffsetPx.value.x / calibScaleX.value : 0
  const offY = calibrated.value ? -gcodeOffsetPx.value.y / calibScaleY.value : 0
  const ox = zeroOffset.value.x - offX
  const oy = zeroOffset.value.y - offY
  await store.envoyerCommande(`G92 X${ox.toFixed(3)} Y${oy.toFixed(3)}`)
  await store.lancerFichier(fichierCharge.value)
}

async function pauseGravure() {
  jobPaused.value = true
  await fetch(`/api/machines/${store.machineActiveId}/pause`, { method: 'POST' })
}
async function reprendreGravure() {
  jobPaused.value = false
  await fetch(`/api/machines/${store.machineActiveId}/resume`, { method: 'POST' })
}
async function stopUrgence() {
  showConfirmStop.value = false; jobPaused.value = false
  await store.stopper()
}
async function allerAuZero() {
  await store.envoyerCommande(`G90 G0 X${zeroOffset.value.x} Y${zeroOffset.value.y}`)
}
</script>

<style scoped>
.viewer-outer {
  position: relative;
  height: calc(100% - 90px);
  min-height: 350px;
  overflow: hidden;
  background: #0D1117;
  user-select: none;
  transition: box-shadow 0.2s;
}
.border-error { box-shadow: inset 0 0 0 3px rgba(255,82,82,0.6) !important; }
.viewer-world {
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%;
  transform-origin: 0 0; will-change: transform;
}
.camera-img {
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%;
  object-fit: cover; pointer-events: none;
}
.canvas-abs {
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%; pointer-events: none;
}
.calib-marker {
  position: absolute; transform: translate(-50%,-50%); pointer-events: none;
}
.calib-cross { position: absolute; width:20px; height:20px; top:-10px; left:-10px; }
.p0-cross::before,.p0-cross::after,.p1-cross::before,.p1-cross::after {
  content:''; position:absolute;
}
.p0-cross::before { width:20px;height:2px;top:9px;left:0;background:#4CAF50; }
.p0-cross::after  { width:2px;height:20px;top:0;left:9px;background:#4CAF50; }
.p1-cross::before { width:20px;height:2px;top:9px;left:0;background:#FF5252; }
.p1-cross::after  { width:2px;height:20px;top:0;left:9px;background:#FF5252; }
.calib-label {
  position:absolute; font-size:10px; font-family:monospace;
  white-space:nowrap; padding:1px 4px; border-radius:3px; top:10px; left:10px;
}
.p0-label { color:#4CAF50;background:rgba(0,0,0,0.6);border:1px solid #4CAF50; }
.p1-label { color:#FF5252;background:rgba(0,0,0,0.6);border:1px solid #FF5252; }
.calib-info {
  position:absolute; top:8px; right:8px;
  background:rgba(0,0,0,0.6); border:1px solid rgba(76,175,80,0.5);
  border-radius:4px; padding:2px 8px; font-size:11px; color:#4CAF50; pointer-events:none;
}
.sim-speed-control {
  position: absolute; bottom: 12px; right: 12px;
  background: rgba(0,0,0,0.7); border: 1px solid #FFB800;
  border-radius: 6px; padding: 4px 10px;
  display: flex; align-items: center;
  font-size: 12px; color: #FFB800; z-index: 6;
}
.cursor-crosshair  { cursor: crosshair !important; }
.cursor-move-mode  { cursor: grab !important; }
.canvas-empty {
  position:absolute; inset:0; z-index:5;
  display:flex; flex-direction:column;
  align-items:center; justify-content:center;
  pointer-events:none; color:rgba(255,255,255,0.3);
}
.mode-hint {
  position:absolute; bottom:12px; left:50%; transform:translateX(-50%);
  border-radius:6px; padding:5px 14px; font-size:12px; z-index:6;
  pointer-events:none; backdrop-filter:blur(4px);
  display:flex; align-items:center; white-space:nowrap;
}
.warning-hint { background:rgba(0,0,0,0.7);border:1px solid #FFB800;color:#FFB800; }
.info-hint    { background:rgba(0,0,0,0.7);border:1px solid #00E5FF;color:#00E5FF; }
.error-hint   { background:rgba(0,0,0,0.7);border:1px solid #FF5252;color:#FF5252; }
.action-bar {
  background:rgba(0,0,0,0.2);
  border-bottom:1px solid rgba(255,255,255,0.06);
  min-height:44px;
}
</style>
