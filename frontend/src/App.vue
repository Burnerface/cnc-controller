<template>
  <v-app theme="dark">
    <HeaderBar />
    <v-main class="bg-background">
      <v-container fluid class="pa-3">
        <v-row dense>
          <v-col cols="12" md="3">
            <v-row dense>
              <v-col cols="12">
                <PositionCard @aller-zero-travail="allerZeroTravail" />
              </v-col>
              <v-col cols="12"><JogCard /></v-col>
              <v-col cols="12"><ConsoleCard /></v-col>
            </v-row>
          </v-col>
          <v-col cols="12" md="6">
            <GCodeViewer ref="gcodeViewer" />
          </v-col>
          <v-col cols="12" md="3">
            <v-row dense>
              <v-col cols="12"><FileManager /></v-col>
              <v-col cols="12"><CameraCard /></v-col>
            </v-row>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
    <SettingsDialog v-model="showSettings" />
    <MachineDialog v-model="showMachineDialog" />
  </v-app>
</template>

<script setup>
import { ref, onMounted, provide } from 'vue'
import { useMachineStore } from './stores/machine'
import HeaderBar from './components/HeaderBar.vue'
import PositionCard from './components/PositionCard.vue'
import JogCard from './components/JogCard.vue'
import ConsoleCard from './components/ConsoleCard.vue'
import GCodeViewer from './components/GCodeViewer.vue'
import FileManager from './components/FileManager.vue'
import CameraCard from './components/CameraCard.vue'
import SettingsDialog from './components/SettingsDialog.vue'
import MachineDialog from './components/MachineDialog.vue'

const store = useMachineStore()
const showSettings      = ref(false)
const showMachineDialog = ref(false)
const gcodeViewer       = ref(null)

provide('showSettings', showSettings)
provide('showMachineDialog', showMachineDialog)
provide('gcodeViewer', gcodeViewer)

// PositionCard → bouton "→ Zéro" → GCodeViewer.allerAuZeroTravail()
function allerZeroTravail() {
  gcodeViewer.value?.allerAuZeroTravail()
}

onMounted(() => {
  store.chargerMachines()
})
</script>
