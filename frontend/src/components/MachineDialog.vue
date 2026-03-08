<template>
  <v-dialog :model-value="modelValue" max-width="580" scrollable
    @update:model-value="$emit('update:modelValue', $event)">
    <v-card color="surface" rounded="lg">
      <v-card-title class="d-flex align-center py-3 px-4">
        <v-icon class="mr-2">{{ editMode ? 'mdi-pencil' : 'mdi-plus-circle' }}</v-icon>
        {{ editMode ? `Modifier — ${form.name}` : 'Ajouter une machine' }}
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" size="small"
          @click="$emit('update:modelValue', false)" />
      </v-card-title>
      <v-divider />

      <v-card-text class="pa-4">

        <!-- Nom -->
        <v-text-field v-model="form.name" label="Nom" density="compact"
          variant="outlined" class="mb-3" />

        <!-- Type -->
        <div class="text-caption mb-2 text-medium-emphasis">TYPE</div>
        <v-btn-toggle v-model="form.type" mandatory density="compact"
          color="primary" class="mb-4 w-100">
          <v-btn value="cnc"    size="small" class="flex-grow-1" prepend-icon="mdi-router">CNC</v-btn>
          <v-btn value="laser"  size="small" class="flex-grow-1" prepend-icon="mdi-laser-pointer">Laser</v-btn>
          <v-btn value="hybrid" size="small" class="flex-grow-1" prepend-icon="mdi-swap-horizontal">Hybride</v-btn>
        </v-btn-toggle>

        <!-- Simulateur -->
        <v-switch v-model="form.sim" label="Mode simulateur" color="warning"
          density="compact" class="mb-2" />

        <!-- Port -->
        <template v-if="!form.sim">
          <v-select v-model="form.port" label="Port série" :items="ports"
            density="compact" variant="outlined" class="mb-3">
            <template #append-inner>
              <v-btn icon="mdi-refresh" variant="text" size="x-small" @click.stop="chargerPorts" />
            </template>
          </v-select>
          <v-select v-model="form.baudrate" label="Baudrate"
            :items="[9600,19200,38400,57600,115200]"
            density="compact" variant="outlined" class="mb-3" />
        </template>

        <v-divider class="mb-3" />

        <!-- Limites -->
        <div class="text-caption mb-2 text-medium-emphasis">LIMITES (mm)</div>
        <v-row dense class="mb-3">
          <v-col cols="4">
            <v-text-field v-model.number="form.limites.x" label="X max" type="number"
              density="compact" variant="outlined" suffix="mm" />
          </v-col>
          <v-col cols="4">
            <v-text-field v-model.number="form.limites.y" label="Y max" type="number"
              density="compact" variant="outlined" suffix="mm" />
          </v-col>
          <v-col cols="4">
            <v-text-field v-model.number="form.limites.z" label="Z max" type="number"
              density="compact" variant="outlined" suffix="mm" />
          </v-col>
        </v-row>

        <v-divider class="mb-3" />

        <!-- Laser -->
        <template v-if="form.type === 'laser' || form.type === 'hybrid'">
          <div class="text-caption mb-2 text-medium-emphasis">LASER</div>
          <v-row dense class="mb-3">
            <v-col cols="6">
              <v-text-field v-model.number="form.laser_power_max" label="Puissance max (S)"
                type="number" density="compact" variant="outlined" />
            </v-col>
            <v-col cols="6">
              <v-text-field v-model.number="form.vitesse_gravure_max" label="Vitesse max gravure"
                type="number" density="compact" variant="outlined" suffix="mm/min" />
            </v-col>
          </v-row>
          <v-divider class="mb-3" />
        </template>

        <!-- CNC -->
        <template v-if="form.type === 'cnc' || form.type === 'hybrid'">
          <div class="text-caption mb-2 text-medium-emphasis">BROCHE / CNC</div>
          <v-row dense class="mb-3">
            <v-col cols="6">
              <v-text-field v-model.number="form.broche_max" label="Broche max"
                type="number" density="compact" variant="outlined" suffix="RPM" />
            </v-col>
            <v-col cols="6">
              <v-text-field v-model.number="form.vitesse_fraisage_max" label="Vitesse max fraisage"
                type="number" density="compact" variant="outlined" suffix="mm/min" />
            </v-col>
          </v-row>
          <v-divider class="mb-3" />
        </template>

        <!-- Caméras -->
        <div class="text-caption mb-2 text-medium-emphasis">CAMÉRAS</div>
        <v-row dense class="mb-2">
          <v-col cols="12">
            <v-select
              v-model="form.camera_positionnement_id"
              label="Caméra de positionnement (visualisateur)"
              :items="cameraItems"
              item-title="label"
              item-value="id"
              density="compact" variant="outlined" clearable
              prepend-inner-icon="mdi-camera-iris"
            >
              <template #item="{ item, props: p }">
                <v-list-item v-bind="p">
                  <template #prepend>
                    <v-icon size="small">
                      {{ item.raw.type === 'usb' ? 'mdi-usb' : 'mdi-web' }}
                    </v-icon>
                  </template>
                </v-list-item>
              </template>
            </v-select>
          </v-col>
          <v-col cols="12">
            <v-select
              v-model="form.camera_surveillance_id"
              label="Caméra de surveillance"
              :items="cameraItems"
              item-title="label"
              item-value="id"
              density="compact" variant="outlined" clearable
              prepend-inner-icon="mdi-cctv"
            >
              <template #item="{ item, props: p }">
                <v-list-item v-bind="p">
                  <template #prepend>
                    <v-icon size="small">
                      {{ item.raw.type === 'usb' ? 'mdi-usb' : 'mdi-web' }}
                    </v-icon>
                  </template>
                </v-list-item>
              </template>
            </v-select>
          </v-col>
        </v-row>
        <div class="text-caption text-medium-emphasis mb-2">
          Gérer les caméras dans
          <a href="#" class="text-primary" @click.prevent="$emit('update:modelValue', false)">
            Paramètres → Caméras
          </a>
        </div>

      </v-card-text>

      <v-divider />
      <v-card-actions class="px-4 py-3">
        <v-btn v-if="editMode" color="error" variant="tonal"
          prepend-icon="mdi-delete" @click="showConfirmDelete = true">
          Supprimer
        </v-btn>
        <v-spacer />
        <v-btn variant="text" @click="$emit('update:modelValue', false)">Annuler</v-btn>
        <v-btn color="primary" variant="flat" :loading="saving" @click="sauvegarder">
          {{ editMode ? 'Enregistrer' : 'Ajouter' }}
        </v-btn>
      </v-card-actions>
    </v-card>

    <!-- Confirm suppression -->
    <v-dialog v-model="showConfirmDelete" max-width="360">
      <v-card color="surface" rounded="lg">
        <v-card-title class="py-3 px-4 d-flex align-center">
          <v-icon color="error" class="mr-2">mdi-delete-alert</v-icon>
          Supprimer {{ form.name }} ?
        </v-card-title>
        <v-card-text class="pa-4">
          Cette action est irréversible.
        </v-card-text>
        <v-card-actions class="px-4 pb-4">
          <v-btn variant="text" @click="showConfirmDelete = false">Annuler</v-btn>
          <v-spacer />
          <v-btn color="error" variant="flat" @click="supprimer">Supprimer</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useMachineStore } from '../stores/machine'

const props = defineProps({ modelValue: Boolean, machine: { type: Object, default: null } })
const emit = defineEmits(['update:modelValue'])

const store = useMachineStore()
const saving = ref(false)
const ports = ref([])
const editMode = ref(false)
const showConfirmDelete = ref(false)
const allCameras = ref([])

const cameraItems = computed(() => [
  { id: null, label: '— Aucune —', type: null },
  ...allCameras.value.map(c => ({
    id: c.id,
    label: `${c.name} (${c.type === 'usb' ? 'USB' : 'IP'})`,
    type: c.type,
  }))
])

const defaultForm = () => ({
  name: '', type: 'laser', port: '', baudrate: 115200, sim: false,
  limites: { x: 300, y: 300, z: 50 },
  laser_power_max: 1000, vitesse_gravure_max: 3000,
  broche_max: 24000, vitesse_fraisage_max: 2000,
  camera_surveillance_id: null,
  camera_positionnement_id: null,
})

const form = ref(defaultForm())

async function loadCameras() {
  const res = await fetch('/api/cameras')
  allCameras.value = await res.json()
}

watch(() => props.modelValue, async (val) => {
  if (!val) return
  showConfirmDelete.value = false
  await loadCameras()
  if (props.machine) {
    editMode.value = true
    form.value = {
      ...defaultForm(),
      ...props.machine,
      limites: { ...{ x: 300, y: 300, z: 50 }, ...(props.machine.limites || {}) },
    }
  } else {
    editMode.value = false
    form.value = defaultForm()
  }
  chargerPorts()
})

async function chargerPorts() {
  ports.value = await store.chargerPorts()
}

async function sauvegarder() {
  saving.value = true
  try {
    if (editMode.value) {
      await store.modifierMachine(form.value.id, form.value)
    } else {
      await store.ajouterMachine(form.value)
    }
    emit('update:modelValue', false)
  } finally {
    saving.value = false
  }
}

async function supprimer() {
  await store.supprimerMachine(form.value.id)
  showConfirmDelete.value = false
  emit('update:modelValue', false)
}
</script>
