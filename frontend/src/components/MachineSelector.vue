<template>
  <div class="d-flex align-center gap-2">
    <v-select
      v-model="store.machineActiveId"
      :items="machines"
      item-title="name"
      item-value="id"
      density="compact"
      variant="outlined"
      hide-details
      style="min-width:180px; max-width:240px"
    >
      <template #item="{ item, props: itemProps }">
        <v-list-item v-bind="itemProps">
          <template #prepend>
            <v-icon size="small" :color="item.raw.connected ? 'success' : 'error'">
              {{ typeIcon(item.raw.type) }}
            </v-icon>
          </template>
          <template #append>
            <v-btn icon="mdi-pencil" variant="text" size="x-small"
              @click.stop="editer(item.raw)" />
          </template>
        </v-list-item>
      </template>
      <template #selection="{ item }">
        <v-icon size="small" :color="item.raw.connected ? 'success' : 'grey'" class="mr-1">
          {{ typeIcon(item.raw.type) }}
        </v-icon>
        {{ item.raw.name }}
      </template>
    </v-select>

    <!-- Connexion -->
    <v-btn
      :color="machineActive?.connected ? 'error' : 'success'"
      :loading="connecting"
      size="small" variant="tonal"
      :prepend-icon="machineActive?.connected ? 'mdi-lan-disconnect' : 'mdi-lan-connect'"
      @click="toggleConnexion"
    >
      {{ machineActive?.connected ? 'Déco' : 'Connecter' }}
    </v-btn>

    <!-- Ajouter -->
    <v-btn icon="mdi-plus" variant="tonal" size="small" color="primary" @click="showDialog = true; machineEdit = null" />

    <MachineDialog v-model="showDialog" :machine="machineEdit" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useMachineStore } from '../stores/machine'
import MachineDialog from './MachineDialog.vue'

const store = useMachineStore()
const showDialog = ref(false)
const machineEdit = ref(null)
const connecting = ref(false)

const machines = computed(() => store.machines)
const machineActive = computed(() => store.machineActive)

function typeIcon(type) {
  return type === 'laser' ? 'mdi-laser-pointer'
       : type === 'cnc'   ? 'mdi-router'
       : 'mdi-swap-horizontal'
}

function editer(machine) {
  machineEdit.value = machine
  showDialog.value = true
}

async function toggleConnexion() {
  connecting.value = true
  try {
    if (machineActive.value?.connected) {
      await store.deconnecter()
    } else {
      await store.connecter()
    }
  } finally {
    connecting.value = false
  }
}
</script>
