<template>
  <v-card color="surface-variant" rounded="lg" elevation="0">
    <v-card-title class="text-caption text-medium-emphasis py-2 px-3">
      <v-icon size="small" class="mr-1">mdi-crosshairs-gps</v-icon>
      POSITION
    </v-card-title>
    <v-divider />
    <v-card-text class="pa-3">
      <div class="d-flex flex-column gap-2 mb-3">
        <div v-for="axis in ['x','y','z']" :key="axis"
          class="d-flex align-center justify-space-between">
          <span class="text-overline font-weight-bold" :style="{ color: axisColor(axis) }">
            {{ axis.toUpperCase() }}
          </span>
          <span class="text-h6 font-weight-bold text-mono">
            {{ (store.position[axis] || 0).toFixed(3) }}
            <span class="text-caption text-medium-emphasis">mm</span>
          </span>
        </div>
      </div>
      <v-divider class="mb-2" />
      <div class="d-flex gap-2 flex-wrap">
        <v-btn size="small" variant="tonal" color="primary" prepend-icon="mdi-home"
          :disabled="!store.connected" @click="home"
          title="Cycle homing ($H) — cherche les fins de course">
          Home
        </v-btn>
        <v-btn size="small" variant="tonal" color="secondary"
          prepend-icon="mdi-map-marker-radius"
          :disabled="!store.connected" @click="allerZeroTravail"
          title="Aller au zéro de travail défini dans le visualisateur">
          → Zéro
        </v-btn>
        <v-btn size="small" variant="tonal" color="warning"
          prepend-icon="mdi-numeric-0-box-outline"
          :disabled="!store.connected" @click="definirZero"
          title="Définir la position actuelle comme zéro travail (G92 X0 Y0 Z0)">
          Déf. Zéro
        </v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { useMachineStore } from '../stores/machine'

const store = useMachineStore()
const emit = defineEmits(['aller-zero-travail'])

const axisColor = (axis) => ({ x: '#FF5252', y: '#00E676', z: '#40C4FF' })[axis]

async function cmd(command) {
  await fetch(`/api/machines/${store.machineActiveId}/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command }),
  })
}

// $H : cycle homing (cherche les fins de course, remet à X0 Y0 Z0)
async function home() {
  await cmd('$H')
}

// Aller au zéro de travail défini dans le visualisateur
function allerZeroTravail() {
  emit('aller-zero-travail')
}

// Définir la position actuelle comme zéro (G92 X0 Y0 Z0)
async function definirZero() {
  await cmd('G92 X0 Y0 Z0')
}
</script>

<style scoped>
.text-mono { font-family: 'Courier New', monospace; }
</style>
