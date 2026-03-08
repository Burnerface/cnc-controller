import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const API = '/api'

function getWsBase() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/api/ws`
}

function defaultMachineState() {
  return {
    connected: false,
    state: 'Disconnected',
    position: { x: 0, y: 0, z: 0 },
    job: { actif: false, fichier: null, progression: 0 },
    logs: [],
    files: [],
    ws: null,
    wsReconnectTimer: null,
  }
}

export const useMachineStore = defineStore('machine', () => {
  const machines        = ref([])
  const machineActiveId = ref(null)
  const machineStates   = ref({})

  // ─── État machine active ──────────────────────────────────────────────────
  function getState(id) {
    if (!machineStates.value[id]) {
      machineStates.value[id] = defaultMachineState()
    }
    return machineStates.value[id]
  }

  const activeState = computed(() =>
    machineActiveId.value ? getState(machineActiveId.value) : defaultMachineState()
  )

  const connected = computed(() => activeState.value.connected)
  const state     = computed(() => activeState.value.state)
  const position  = computed(() => activeState.value.position)
  const job       = computed(() => activeState.value.job)
  const logs      = computed(() => activeState.value.logs)
  const files     = computed(() => activeState.value.files)

  const status = computed(() => ({
    connected: connected.value,
    state:     state.value,
    position:  position.value,
    job:       job.value,
  }))

  const machineActive = computed(() =>
    machines.value.find(m => m.id === machineActiveId.value) || null
  )

  // ─── WebSocket — un par machine, ouvert dès le chargement ────────────────
  function connectWS(machineId) {
    const ms = getState(machineId)

    if (ms.ws && ms.ws.readyState <= 1) return // déjà ouvert ou en cours

    if (ms.ws) { ms.ws.onclose = null; ms.ws.close(); ms.ws = null }
    if (ms.wsReconnectTimer) { clearTimeout(ms.wsReconnectTimer); ms.wsReconnectTimer = null }

    const socket = new WebSocket(`${getWsBase()}/${machineId}`)

    socket.onopen = () => {
      console.log(`[WS] ${machineId} connecté`)
    }

    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        const s = getState(machineId)

        if (msg.type === 'status') {
          if (msg.data.connected !== undefined) s.connected = msg.data.connected
          if (msg.data.state     !== undefined) s.state     = msg.data.state
          if (msg.data.position  !== undefined) s.position  = { ...msg.data.position }
          if (msg.data.job       !== undefined) s.job       = { ...msg.data.job }
          // Déclencher la réactivité Vue
          machineStates.value[machineId] = { ...s }
        } else if (msg.type === 'log') {
          s.logs.push(msg.data)
          if (s.logs.length > 500) s.logs.shift()
        } else if (msg.type === 'error') {
          s.logs.push({ time: new Date().toLocaleTimeString(), message: `⚠ ${msg.message}` })
        }
      } catch (e) {
        console.error('[WS] Parse error', e)
      }
    }

    socket.onclose = () => {
      console.log(`[WS] ${machineId} fermé, reconnexion dans 2s`)
      const ms2 = getState(machineId)
      ms2.wsReconnectTimer = setTimeout(() => connectWS(machineId), 2000)
    }

    socket.onerror = (e) => console.error(`[WS] ${machineId} erreur`, e)

    ms.ws = socket
  }

  // ─── Machines ─────────────────────────────────────────────────────────────
  async function chargerMachines() {
    const res = await fetch(`${API}/machines`)
    machines.value = await res.json()

    // Ouvrir un WS pour CHAQUE machine dès le départ
    for (const m of machines.value) {
      connectWS(m.id)
    }

    if (!machineActiveId.value && machines.value.length > 0) {
      machineActiveId.value = machines.value[0].id
      await chargerFichiers()
    }
  }

  async function selectionnerMachine(id) {
    machineActiveId.value = id
    // Le WS est déjà ouvert, juste recharger les fichiers
    await chargerFichiers()
  }

  async function ajouterMachine(config) {
    const res = await fetch(`${API}/machines`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
    const machine = await res.json()
    machines.value.push(machine)
    // Ouvrir le WS pour la nouvelle machine
    connectWS(machine.id)
    return machine
  }

  async function modifierMachine(id, config) {
    const res = await fetch(`${API}/machines/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
    const updated = await res.json()
    const idx = machines.value.findIndex(m => m.id === id)
    if (idx !== -1) machines.value[idx] = updated
    return updated
  }

  async function supprimerMachine(id) {
    await fetch(`${API}/machines/${id}`, { method: 'DELETE' })
    const ms = machineStates.value[id]
    if (ms?.ws) { ms.ws.onclose = null; ms.ws.close() }
    if (ms?.wsReconnectTimer) clearTimeout(ms.wsReconnectTimer)
    delete machineStates.value[id]
    machines.value = machines.value.filter(m => m.id !== id)
    if (machineActiveId.value === id) {
      if (machines.value.length > 0) {
        await selectionnerMachine(machines.value[0].id)
      } else {
        machineActiveId.value = null
      }
    }
  }

  // ─── Connexion ────────────────────────────────────────────────────────────
  async function connecter(id) {
    const mid = id || machineActiveId.value
    await fetch(`${API}/machines/${mid}/connect`, { method: 'POST' })
  }

  async function deconnecter(id) {
    const mid = id || machineActiveId.value
    await fetch(`${API}/machines/${mid}/disconnect`, { method: 'POST' })
  }

  // ─── Commandes ────────────────────────────────────────────────────────────
  async function envoyerCommande(command, machineId) {
    const mid = machineId || machineActiveId.value
    await fetch(`${API}/machines/${mid}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command }),
    })
  }

  async function stopper(machineId) {
    const mid = machineId || machineActiveId.value
    await fetch(`${API}/machines/${mid}/stop`, { method: 'POST' })
  }

  // ─── Fichiers ─────────────────────────────────────────────────────────────
  async function chargerFichiers(machineId) {
    const mid = machineId || machineActiveId.value
    if (!mid) return
    const res = await fetch(`${API}/machines/${mid}/files`)
    const f = await res.json()
    getState(mid).files = f
    machineStates.value[mid] = { ...getState(mid) }
  }

  async function uploadFichier(file) {
    const form = new FormData()
    form.append('file', file)
    await fetch(`${API}/machines/${machineActiveId.value}/upload`, {
      method: 'POST', body: form,
    })
    await chargerFichiers()
  }

  async function contenuFichier(filename) {
    const res = await fetch(
      `${API}/machines/${machineActiveId.value}/files/${encodeURIComponent(filename)}/content`
    )
    const data = await res.json()
    return data.content
  }

  async function supprimerFichier(filename) {
    await fetch(
      `${API}/machines/${machineActiveId.value}/files/${encodeURIComponent(filename)}`,
      { method: 'DELETE' }
    )
    await chargerFichiers()
  }

  async function lancerFichier(filename) {
    await fetch(
      `${API}/machines/${machineActiveId.value}/run/${encodeURIComponent(filename)}`,
      { method: 'POST' }
    )
  }

  // ─── Settings ─────────────────────────────────────────────────────────────
  async function chargerSettings() {
    await fetch(`${API}/machines/${machineActiveId.value}/settings`, { method: 'GET' })
  }

  async function envoyerSetting(key, value) {
    await fetch(`${API}/machines/${machineActiveId.value}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key, value }),
    })
  }

  async function chargerPorts() {
    const res = await fetch(`${API}/ports`)
    return await res.json()
  }

  return {
    machines, machineActiveId, machineStates,
    status, logs, files,
    machineActive, position, connected, state, job,
    chargerMachines, selectionnerMachine,
    ajouterMachine, modifierMachine, supprimerMachine,
    connecter, deconnecter,
    envoyerCommande, stopper,
    chargerFichiers, uploadFichier, contenuFichier, supprimerFichier, lancerFichier,
    chargerSettings, envoyerSetting, chargerPorts,
  }
})
