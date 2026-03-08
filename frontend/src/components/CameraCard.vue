<template>
  <v-card color="surface-variant" rounded="lg" elevation="0">
    <v-card-title class="text-caption text-medium-emphasis py-2 px-3 d-flex align-center">
      <v-icon size="small" class="mr-1">mdi-camera</v-icon>
      CAMÉRA
      <v-spacer />
      <v-btn icon="mdi-cog" variant="text" size="x-small" @click="showConfig = true" />
    </v-card-title>
    <v-divider />

    <!-- Sélecteur caméra associée -->
    <div v-if="cameras.length > 0" class="px-2 pt-2">
      <v-select
        v-model="selectedCamId"
        :items="cameras"
        item-title="name"
        item-value="id"
        density="compact"
        variant="outlined"
        hide-details
        placeholder="Choisir une caméra"
        class="mb-2"
      />
    </div>

    <!-- Flux vidéo -->
    <div class="camera-container">
      <img
        v-if="activeCamera && activeCamera.type === 'url' && activeCamera.url"
        :src="activeCamera.url"
        class="camera-feed"
        alt="Caméra"
        @error="onError"
      />
      <div v-else class="camera-empty text-medium-emphasis text-caption">
        <v-icon size="32" class="mb-2">mdi-camera-off</v-icon>
        <div>{{ cameras.length ? 'Sélectionnez une caméra' : 'Aucune caméra configurée' }}</div>
        <v-btn size="x-small" variant="tonal" color="primary" class="mt-2" @click="showConfig = true">
          + Ajouter
        </v-btn>
      </div>
    </div>

    <!-- Dialog config caméras -->
    <v-dialog v-model="showConfig" max-width="560">
      <v-card color="surface" rounded="lg">
        <v-card-title class="d-flex align-center py-3 px-4">
          <v-icon class="mr-2">mdi-camera-plus</v-icon>
          Gestion des caméras
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" size="small" @click="showConfig = false" />
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">

          <!-- Liste caméras existantes -->
          <div v-for="cam in allCameras" :key="cam.id" class="cam-item mb-2 pa-2 rounded">
            <div class="d-flex align-center">
              <v-icon size="small" class="mr-2" :color="cam.type === 'usb' ? 'warning' : 'primary'">
                {{ cam.type === 'usb' ? 'mdi-usb' : 'mdi-web' }}
              </v-icon>
              <div class="flex-grow-1">
                <div class="text-caption font-weight-bold">{{ cam.name }}</div>
                <div class="text-caption text-medium-emphasis">
                  {{ cam.type === 'usb' ? `USB device ${cam.device}` : cam.url }}
                </div>
                <div class="text-caption text-medium-emphasis">
                  Machines : {{ cam.machine_ids.length ? cam.machine_ids.join(', ') : 'aucune' }}
                </div>
              </div>
              <v-btn icon="mdi-pencil" size="x-small" variant="text" @click="editCam(cam)" />
              <v-btn icon="mdi-delete" size="x-small" variant="text" color="error" @click="deleteCam(cam.id)" />
            </div>
          </div>

          <v-divider v-if="allCameras.length" class="my-3" />

          <!-- Formulaire ajout/édition -->
          <div class="text-caption font-weight-bold mb-2">
            {{ editingCam ? 'Modifier la caméra' : 'Ajouter une caméra' }}
          </div>

          <v-text-field v-model="form.name" label="Nom" density="compact" variant="outlined" class="mb-2" />

          <v-btn-toggle v-model="form.type" mandatory density="compact" color="primary" class="mb-3">
            <v-btn value="url" size="small">URL / IP</v-btn>
            <v-btn value="usb" size="small">USB</v-btn>
          </v-btn-toggle>

          <v-text-field
            v-if="form.type === 'url'"
            v-model="form.url"
            label="URL du flux (ex: http://192.168.1.x/stream)"
            density="compact"
            variant="outlined"
            class="mb-2"
          />
          <v-text-field
            v-else
            v-model.number="form.device"
            label="Numéro device USB (0, 1, 2...)"
            type="number"
            density="compact"
            variant="outlined"
            class="mb-2"
          />

          <!-- Association machines -->
          <div class="text-caption mb-1">Associer aux machines :</div>
          <div class="d-flex flex-wrap gap-1 mb-3">
            <v-chip
              v-for="m in store.machines"
              :key="m.id"
              :color="form.machine_ids.includes(m.id) ? 'primary' : 'default'"
              variant="tonal"
              size="small"
              clickable
              @click="toggleMachine(m.id)"
            >
              {{ m.name }}
            </v-chip>
          </div>

          <div class="d-flex gap-2">
            <v-btn v-if="editingCam" variant="text" @click="cancelEdit">Annuler</v-btn>
            <v-btn color="primary" variant="flat" :loading="saving" @click="saveCamera">
              {{ editingCam ? 'Modifier' : 'Ajouter' }}
            </v-btn>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useMachineStore } from '../stores/machine'

const store = useMachineStore()
const showConfig = ref(false)
const allCameras = ref([])
const selectedCamId = ref(null)
const saving = ref(false)
const editingCam = ref(null)

const form = ref({ name: '', type: 'url', url: '', device: 0, machine_ids: [] })

// Caméras associées à la machine active
const cameras = computed(() =>
  allCameras.value.filter(c => c.machine_ids.includes(store.machineActiveId))
)

const activeCamera = computed(() =>
  allCameras.value.find(c => c.id === selectedCamId.value) || null
)

async function loadCameras() {
  const res = await fetch('/api/cameras')
  allCameras.value = await res.json()
  // Auto-sélectionner la première caméra associée
  if (!selectedCamId.value && cameras.value.length > 0) {
    selectedCamId.value = cameras.value[0].id
  }
}

async function saveCamera() {
  saving.value = true
  try {
    if (editingCam.value) {
      await fetch(`/api/cameras/${editingCam.value.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form.value),
      })
    } else {
      await fetch('/api/cameras', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form.value),
      })
    }
    await loadCameras()
    resetForm()
  } finally {
    saving.value = false
  }
}

async function deleteCam(id) {
  await fetch(`/api/cameras/${id}`, { method: 'DELETE' })
  await loadCameras()
}

function editCam(cam) {
  editingCam.value = cam
  form.value = { ...cam }
}

function cancelEdit() {
  editingCam.value = null
  resetForm()
}

function resetForm() {
  editingCam.value = null
  form.value = { name: '', type: 'url', url: '', device: 0, machine_ids: [] }
}

function toggleMachine(id) {
  const idx = form.value.machine_ids.indexOf(id)
  if (idx === -1) form.value.machine_ids.push(id)
  else form.value.machine_ids.splice(idx, 1)
}

function onError() {
  selectedCamId.value = null
}

// Recharger quand on change de machine
watch(() => store.machineActiveId, () => {
  selectedCamId.value = cameras.value[0]?.id || null
})

onMounted(loadCameras)
</script>

<style scoped>
.camera-container {
  position: relative;
  width: 100%;
  aspect-ratio: 4/3;
  background: #000;
  overflow: hidden;
}
.camera-feed { width: 100%; height: 100%; object-fit: contain; }
.camera-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.cam-item { background: rgba(255,255,255,0.04); }
</style>
