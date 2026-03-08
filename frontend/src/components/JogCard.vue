<template>
  <v-card color="surface-variant" rounded="lg" elevation="0">
    <v-card-title class="text-caption text-medium-emphasis py-2 px-3 d-flex align-center">
      <v-icon size="small" class="mr-1">mdi-gamepad-variant</v-icon>
      JOG
      <v-spacer />
      <v-btn
        :icon="locked ? 'mdi-lock' : 'mdi-lock-open'"
        :color="locked ? 'error' : 'success'"
        variant="text" size="x-small"
        :title="locked ? 'Verrouillé — cliquer pour déverrouiller ($X)' : 'Déverrouillé'"
        :disabled="!connected"
        @click="toggleLock"
      />
      <v-btn-toggle
        v-if="store.machineActive?.type === 'hybrid'"
        v-model="modeActif" mandatory density="compact"
        color="primary" size="x-small" class="ml-1"
        @update:model-value="basculerMode"
      >
        <v-btn value="cnc"   size="x-small">CNC</v-btn>
        <v-btn value="laser" size="x-small">Laser</v-btn>
      </v-btn-toggle>
    </v-card-title>
    <v-divider />
    <v-card-text class="pa-3">

      <v-alert v-if="locked" type="warning" variant="tonal" density="compact"
        class="mb-3 text-caption" icon="mdi-lock">
        Machine verrouillée — déverrouillez avant de joger
      </v-alert>

      <!-- Grille XY -->
      <div class="jog-grid mb-2">
        <div />
        <v-btn :disabled="!canJog || depasseLimite('Y', step)" icon variant="tonal" size="small"
          @click="jog('Y', step)"><v-icon>mdi-arrow-up</v-icon></v-btn>
        <div />
        <v-btn :disabled="!canJog || depasseLimite('X', -step)" icon variant="tonal" size="small"
          @click="jog('X', -step)"><v-icon>mdi-arrow-left</v-icon></v-btn>

        <!-- Centre : définir zéro travail ici -->
        <v-btn :disabled="!connected" icon variant="flat" color="primary" size="small"
          title="Définir la position actuelle comme zéro travail (G92 X0 Y0 Z0)"
          @click="definirZero">
          <v-icon>mdi-crosshairs</v-icon>
        </v-btn>

        <v-btn :disabled="!canJog || depasseLimite('X', step)" icon variant="tonal" size="small"
          @click="jog('X', step)"><v-icon>mdi-arrow-right</v-icon></v-btn>
        <div />
        <v-btn :disabled="!canJog || depasseLimite('Y', -step)" icon variant="tonal" size="small"
          @click="jog('Y', -step)"><v-icon>mdi-arrow-down</v-icon></v-btn>
        <div />
      </div>

      <!-- Z -->
      <div class="d-flex align-center justify-center gap-2 mb-2">
        <v-btn :disabled="!canJog || depasseLimite('Z', step)" icon variant="tonal" size="small"
          color="info" @click="jog('Z', step)">
          <v-icon>mdi-arrow-collapse-up</v-icon>
        </v-btn>
        <span class="text-caption text-medium-emphasis">Z</span>
        <v-btn :disabled="!canJog || depasseLimite('Z', -step)" icon variant="tonal" size="small"
          color="info" @click="jog('Z', -step)">
          <v-icon>mdi-arrow-collapse-down</v-icon>
        </v-btn>
        <v-btn v-if="isCNC" :disabled="!canJog" size="x-small" variant="tonal"
          color="warning" class="ml-2" title="Z-Probe : descendre jusqu'au contact"
          @click="zProbe">
          <v-icon size="small" class="mr-1">mdi-arrow-collapse-down</v-icon>Z-Probe
        </v-btn>
      </div>

      <!-- Step -->
      <v-btn-toggle v-model="stepIndex" mandatory density="compact"
        color="primary" class="w-100 mb-3">
        <v-btn v-for="(s, i) in steps" :key="i" size="x-small" class="flex-grow-1">{{ s }}</v-btn>
      </v-btn-toggle>

      <v-divider class="mb-3" />

      <!-- LASER -->
      <template v-if="isLaser">
        <div class="d-flex align-center mb-1">
          <v-icon size="small" color="warning" class="mr-1">mdi-laser-pointer</v-icon>
          <span class="text-caption text-medium-emphasis">PUISSANCE</span>
          <v-spacer />
          <span class="text-caption text-primary font-weight-bold">{{ puissanceLaser }}%</span>
        </div>
        <v-slider v-model="puissanceLaser" min="0" max="100" step="1"
          color="warning" track-color="surface" hide-details class="mb-2" />

        <div class="d-flex align-center mb-1">
          <v-icon size="small" color="orange" class="mr-1">mdi-speedometer</v-icon>
          <span class="text-caption text-medium-emphasis">VITESSE</span>
          <v-spacer />
          <span class="text-caption text-primary font-weight-bold">
            {{ vitessePct }}% — {{ vitesseActuelle }} mm/min
          </span>
        </div>
        <v-slider v-model="vitessePct" min="1" max="100" step="1"
          color="orange" track-color="surface" hide-details class="mb-3" />

        <div class="d-flex gap-2 flex-wrap">
          <v-btn size="x-small" variant="tonal" color="info"
            :disabled="!connected || locked" @click="focusLaser"
            title="Laser à 3% pour mise au point">
            <v-icon size="small" class="mr-1">mdi-image-filter-center-focus</v-icon>Focus (3%)
          </v-btn>
          <v-btn size="x-small" variant="tonal" color="warning"
            :disabled="!connected || locked" @click="testerLaser">
            <v-icon size="small" class="mr-1">mdi-flash</v-icon>Test (1s)
          </v-btn>
          <v-btn size="x-small" variant="tonal" color="error"
            :disabled="!connected" @click="eteindreLaser">
            <v-icon size="small" class="mr-1">mdi-power</v-icon>Éteindre
          </v-btn>
        </div>
      </template>

      <!-- CNC -->
      <template v-if="isCNC">
        <div class="d-flex align-center mb-1">
          <v-icon size="small" color="info" class="mr-1">mdi-rotate-right</v-icon>
          <span class="text-caption text-medium-emphasis">BROCHE</span>
          <v-spacer />
          <span class="text-caption text-primary font-weight-bold">
            {{ brochePct }}% — {{ broacheRPM }} RPM
          </span>
        </div>
        <v-slider v-model="brochePct" min="0" max="100" step="1"
          color="info" track-color="surface" hide-details class="mb-2" />

        <div class="d-flex align-center mb-1">
          <v-icon size="small" color="orange" class="mr-1">mdi-speedometer</v-icon>
          <span class="text-caption text-medium-emphasis">VITESSE FRAISAGE</span>
          <v-spacer />
          <span class="text-caption text-primary font-weight-bold">
            {{ vitessePct }}% — {{ vitesseActuelle }} mm/min
          </span>
        </div>
        <v-slider v-model="vitessePct" min="1" max="100" step="1"
          color="orange" track-color="surface" hide-details class="mb-3" />

        <div class="d-flex gap-2 flex-wrap">
          <v-btn size="x-small" variant="flat" color="info"
            :disabled="!connected || locked" @click="demarrerBroche">
            <v-icon size="small" class="mr-1">mdi-play</v-icon>Démarrer
          </v-btn>
          <v-btn size="x-small" variant="tonal" color="error"
            :disabled="!connected" @click="arreterBroche">
            <v-icon size="small" class="mr-1">mdi-stop</v-icon>Arrêter
          </v-btn>
        </div>
      </template>

    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useMachineStore } from '../stores/machine'

const store     = useMachineStore()
const connected = computed(() => store.connected)
const locked    = ref(false)

const steps     = [0.1, 1, 5, 10, 50]
const stepIndex = ref(1)
const step      = computed(() => steps[stepIndex.value])

const modeActif = ref(
  store.machineActive?.type === 'hybrid' ? 'laser' : (store.machineActive?.type || 'laser')
)
watch(() => store.machineActive?.type, (t) => {
  if (t && t !== 'hybrid') modeActif.value = t
})

const isLaser = computed(() => {
  const t = store.machineActive?.type
  return t === 'laser' || (t === 'hybrid' && modeActif.value === 'laser')
})
const isCNC = computed(() => {
  const t = store.machineActive?.type
  return t === 'cnc' || (t === 'hybrid' && modeActif.value === 'cnc')
})

const canJog  = computed(() => connected.value && !locked.value)
const limites = computed(() => store.machineActive?.limites || null)
const pos     = computed(() => store.position)

// Retourne true si le déplacement ferait dépasser les limites
function depasseLimite(axis, distance) {
  if (!limites.value || !canJog.value) return false
  const cur = pos.value[axis.toLowerCase()] || 0
  const nxt = cur + distance
  const max = limites.value[axis.toLowerCase()]
  if (max === undefined) return false
  return nxt < 0 || nxt > max
}

const puissanceLaser  = ref(50)
const laserPowerMax   = computed(() => store.machineActive?.laser_power_max || 1000)
const laserSValue     = computed(() => Math.round(puissanceLaser.value / 100 * laserPowerMax.value))

const vitessePct      = ref(50)
const vitesseActuelle = computed(() => {
  const max = isLaser.value
    ? (store.machineActive?.vitesse_gravure_max  || 3000)
    : (store.machineActive?.vitesse_fraisage_max || 2000)
  return Math.max(1, Math.round(vitessePct.value / 100 * max))
})

const brochePct  = ref(50)
const broacheRPM = computed(() =>
  Math.round(brochePct.value / 100 * (store.machineActive?.broche_max || 24000))
)

async function cmd(command) {
  await fetch(`/api/machines/${store.machineActiveId}/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command }),
  })
}

async function toggleLock() {
  if (locked.value) { await cmd('$X'); locked.value = false }
  else              { await cmd('!');  locked.value = true  }
}

async function jog(axis, distance) {
  if (!canJog.value || depasseLimite(axis, distance)) return
  await cmd(`$J=G91 G21 ${axis}${distance} F${vitesseActuelle.value}`)
}

// Bouton croix : définir la position actuelle comme zéro de travail
async function definirZero() {
  if (!connected.value) return
  await cmd('G92 X0 Y0 Z0')
}

async function basculerMode(mode) {
  await fetch(`/api/machines/${store.machineActiveId}/mode/${mode}`, { method: 'POST' })
}

async function focusLaser() {
  await cmd(`M3 S${Math.round(0.03 * laserPowerMax.value)}`)
}
async function testerLaser() {
  await cmd(`M3 S${laserSValue.value}`)
  setTimeout(() => cmd('M5'), 1000)
}
async function eteindreLaser() { await cmd('M5') }

async function demarrerBroche() { await cmd(`M3 S${broacheRPM.value}`) }
async function arreterBroche()  { await cmd('M5') }

async function zProbe() {
  await cmd('G91')
  await cmd('G38.2 Z-50 F50')
  await cmd('G92 Z0')
  await cmd('G90')
  await cmd('G0 Z2')
}
</script>

<style scoped>
.jog-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  place-items: center;
}
</style>
