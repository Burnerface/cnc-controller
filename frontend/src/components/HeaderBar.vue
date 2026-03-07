<template>
  <v-app-bar color="surface" elevation="2" height="56">

    <template #prepend>
      <span class="text-primary font-weight-bold ml-3 d-flex align-center">
        <v-icon icon="mdi-router" class="mr-2" />
        GRBLDeck
      </span>
    </template>

    <div class="d-flex align-center justify-center w-100">
      <MachineSelector />
    </div>

    <template #append>
      <v-chip :color="statusColor" variant="tonal" size="small" class="mr-2">
        <v-icon start :icon="statusIcon" size="small" />
        {{ store.status.state }}
      </v-chip>
      <v-btn v-if="!store.status.connected" color="primary" variant="tonal" size="small" prepend-icon="mdi-lan-connect" class="mr-1" :disabled="!store.machineActiveId" @click="store.connecter()">Connecter</v-btn>
      <v-btn v-else color="error" variant="tonal" size="small" prepend-icon="mdi-lan-disconnect" class="mr-1" @click="store.deconnecter()">Déconnecter</v-btn>
      <v-btn color="error" variant="flat" size="small" icon="mdi-stop-circle" class="mr-2" :disabled="!store.status.job.actif" @click="store.stopper()" />
      <v-btn icon="mdi-cog" variant="text" size="small" @click="showSettings = true" />
    </template>
  </v-app-bar>
</template>

<script setup>
import { inject, computed } from 'vue'
import { useMachineStore } from '../stores/machine'
import MachineSelector from './MachineSelector.vue'

const store = useMachineStore()
const showSettings = inject('showSettings')

const statusColor = computed(() => {
  switch (store.status.state) {
    case 'Idle': return 'success'
    case 'Run': return 'primary'
    case 'Hold': return 'warning'
    case 'Alarm': return 'error'
    default: return 'grey'
  }
})

const statusIcon = computed(() => {
  switch (store.status.state) {
    case 'Idle': return 'mdi-check-circle'
    case 'Run': return 'mdi-play-circle'
    case 'Hold': return 'mdi-pause-circle'
    case 'Alarm': return 'mdi-alert-circle'
    default: return 'mdi-circle-outline'
  }
})
</script>
