<script setup>
import { computed, ref, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { Terminal, Network, BriefcaseBusiness, Cpu, Landmark, Layers3, ArrowUpRight, ArrowRight, ChevronRight, Radio, ShieldCheck, LogOut, Plus, X, Check, Globe, Fingerprint, Activity, Grid2X2, Play, LockKeyhole, NotebookPen } from 'lucide-vue-next'
import IrcUnderground from './components/IrcUnderground.vue'
import WorkspaceView from './components/WorkspaceView.vue'
import PasswordBreaker from './components/PasswordBreaker.vue'
import ModalDialog from './components/ModalDialog.vue'
import BuildSplash from './components/BuildSplash.vue'
import TraceTracker from './components/TraceTracker.vue'
import ServerLogin from './components/ServerLogin.vue'
import BrokerView from './components/BrokerView.vue'
import BackdoorsView from './components/BackdoorsView.vue'
import TerminalConsole from './components/TerminalConsole.vue'
import AppLauncher from './components/AppLauncher.vue'
import ExchangeView from './components/ExchangeView.vue'
import BlackMarket from './components/BlackMarket.vue'
import FieldNotes from './components/FieldNotes.vue'
import ServerHistory from './components/ServerHistory.vue'
import NetworkMap from './components/NetworkMap.vue'

const loginDialog = ref(false), buildProduct = ref(null), buildMode = ref('software')
const workspaceRef = ref(null)
const user = ref(null), slot = ref(null), saves = ref([]), page = ref('overview'), loading = ref(true), busy = ref(false), error = ref(''), notice = ref('')
const authMode = ref('register'), username = ref(''), password = ref(''), alias = ref(''), now = ref(Date.now()), selectedPosition = ref(1)
const ranks = ref([]), currency = ref({ name: 'Cipher', symbol: 'CPH' }), activeConsole = ref('terminal')
const restartOpen = ref(false), restartConfirmation = ref(''), responseTime = ref(Date.now())
let clock, poller, revision = 0, polling = false, serverOffset = 0
const nav = computed(() => [
  { id: 'overview', label: 'Desktop', icon: Network },
  { id: 'workspace', label: 'Workspace', icon: Grid2X2 },
  { id: 'broker', label: 'Contract broker', icon: BriefcaseBusiness },
  { id: 'bank', label: 'Cipher bank', icon: Landmark },
  { id: 'atlas', label: 'Atlas network', icon: Globe },
  { id: 'exchange', label: 'Store', icon: Cpu },
  { id: 'irc', label: 'IRC Underground', icon: Radio },
  { id: 'launcher', label: 'Applications', icon: Grid2X2 },
  { id: 'notes', label: 'Field Notes', icon: NotebookPen },
  { id: 'history', label: 'Server Histories', icon: Activity },
  { id: 'blackmarket', label: 'Null Exchange', icon: LockKeyhole, visible: !!slot.value?.market_unlocked },
  { id: 'backdoors', label: 'Backdoored Servers', icon: ShieldCheck, visible: !!slot.value?.installed_software.includes('rootkit-epic') },
  { id: 'saves', label: 'Save slots', icon: Layers3 },
].filter(item => item.visible !== false))
const money = n => new Intl.NumberFormat('en-US').format(n ?? 0)
const progress = computed(() => slot.value?.next_rank_at ? Math.min(100, (slot.value.reputation - slot.value.rank_floor) / (slot.value.next_rank_at - slot.value.rank_floor) * 100) : 100)
const serverNow = computed(() => now.value + (slot.value?.server_time ? Date.parse(slot.value.server_time) - responseTime.value : 0))
const remaining = computed(() => slot.value?.trace_deadline ? Math.max(0, Math.ceil((Date.parse(slot.value.trace_deadline) - serverNow.value) / 1000)) : null)
const elapsed = computed(() => slot.value?.trace_started_at ? Math.max(0, Math.floor((serverNow.value - Date.parse(slot.value.trace_started_at)) / 1000)) : 0)
const cooled = job => job.available_at && Date.parse(job.available_at) > now.value + serverOffset
const cooldown = job => Math.max(0, Math.ceil((Date.parse(job.available_at) - now.value - serverOffset) / 1000))
const currentProcess = computed(() => slot.value?.running_apps.find(app => app.id === activeConsole.value))

async function api(path, data) {
  const csrf = document.cookie.split('; ').find(c => c.startsWith('csrftoken='))?.split('=')[1]
  const response = await fetch('/api/' + path, { method: data === undefined ? 'GET' : 'POST', headers: { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRFToken': csrf } : {}) }, credentials: 'same-origin', ...(data !== undefined ? { body: JSON.stringify(data) } : {}) })
  const result = await response.json().catch(() => ({ error: 'Terminal unavailable. Check the server connection.' }))
  if (!response.ok) {
    const failure = new Error(result.error || 'Request failed. Please reconnect.')
    failure.status = response.status; failure.data = result; throw failure
  }
  return result
}
function updateSlot(value) {
  revision++; slot.value = value; responseTime.value = Date.now()
  if (value.server_time) serverOffset = Date.parse(value.server_time) - Date.now()
}
async function act(fn) {
  if (busy.value) return false
  busy.value = true; error.value = ''; notice.value = ''
  try { return await fn() } catch (e) { error.value = e.message; return false } finally { busy.value = false }
}
async function loadSaves() {
  saves.value = (await api('slots/')).slots
  if (!slot.value && saves.value.length) {
    let stored
    try { stored = Number(localStorage.getItem('netrunner.slot')) } catch { /* storage is optional */ }
    await selectSlot(saves.value.find(s => s.id === stored) || saves.value[0])
  }
}
async function selectSlot(save) {
  updateSlot(await api(`slots/${save.id}/`))
  try { localStorage.setItem('netrunner.slot', save.id) } catch { /* storage is optional */ }
  restartOpen.value = false; page.value = 'overview'
}
async function authenticate() {
  await act(async () => {
    await api(authMode.value === 'register' ? 'register/' : 'login/', { username: username.value, password: password.value })
    user.value = (await api('session/')).user; password.value = ''; await loadSaves()
  })
}
async function createSave() {
  await act(async () => {
    const created = await api('slots/', { position: selectedPosition.value, alias: alias.value })
    updateSlot(created)
    try { localStorage.setItem('netrunner.slot', created.id) } catch { /* storage is optional */ }
    alias.value = ''; page.value = 'overview'; await loadSaves()
  })
}
async function logOut() {
  await act(async () => { await api('logout/', {}); revision++; user.value = null; slot.value = null; saves.value = []; page.value = 'overview' })
}
async function navigate(item) {
  if (item.id === 'saves') return openSaves()
  if (['broker','bank','exchange'].includes(item.id)) {
    await act(async () => { updateSlot(await api(`slots/${slot.value.id}/`)); page.value=item.id })
    return
  }
  const application = { broker: 'broker', bank: 'bank', atlas: 'atlas', exchange: 'market' }[item.id]
  if (application) {
    await act(async () => {
      if (!slot.value.running_apps.some(app => app.id === application)) updateSlot(await api(`slots/${slot.value.id}/applications/`, { action: 'launch', product_id: application }))
      activeConsole.value = application
      page.value = item.id
    })
  } else page.value = item.id
}
function activate(app) {
  if (page.value === 'workspace') {
    const process = slot.value.running_apps.find(process => process.id === app)
    if (process) workspaceRef.value?.showApp(process.product_id, true)
    return
  }
  activeConsole.value = app; page.value = ({ atlas: 'atlas', broker: 'broker', market: 'exchange', bank: 'bank' }[app] || 'console'); nextTick(() => document.querySelector('input[aria-label$=" command"]')?.focus({ preventScroll: true })) }
async function launchApplication(productId, stay = false, expectedSlot = null) {
  if (expectedSlot !== null && slot.value?.id !== expectedSlot) return false
  if (['broker','bank','market'].includes(productId)) { await navigate({ id: productId === 'market' ? 'exchange' : productId }); return true }
  return act(async () => {
    const result = await api(`slots/${slot.value.id}/applications/`, { action: 'launch', product_id: productId })
    updateSlot(result)
    if (!stay) activate(result.running_apps.find(app => app.product_id === productId).id)
    await nextTick()
    if (page.value === 'workspace') workspaceRef.value?.showApp(productId)
    return true
  })
}
async function useApplet(productId) {
  const item = slot.value.catalog.find(item => item.id === productId)
  const success = await act(async () => {
    updateSlot(await api(`slots/${slot.value.id}/applets/`, { product_id: productId }))
    if (!slot.value.running_apps.some(app => app.id === 'terminal')) updateSlot(await api(`slots/${slot.value.id}/applications/`, { action:'launch', product_id:'terminal' }))
    activate('terminal')
    return true
  })
  if (success && item?.kind === 'cracker' && slot.value.connected) await openCracker()
}
async function closeApplication(application, stay = false, expectedSlot = null) {
  if (expectedSlot !== null && slot.value?.id !== expectedSlot) return false
  return act(async () => {
    updateSlot(await api(`slots/${slot.value.id}/applications/`, { action: 'close', application }))
    if (!stay && page.value !== 'workspace' && activeConsole.value === application) page.value = 'launcher'
    return true
  })
}
async function sendIrc(command, expectedSlot) {
  if (slot.value?.id !== expectedSlot) return false
  return act(async () => {
    const result = await api(`slots/${expectedSlot}/irc/`, { command })
    updateSlot(result.slot)
    return result.irc
  })
}
async function sendCommand(command, application) {
  return act(async () => { updateSlot(await api(`slots/${slot.value.id}/command/`, { command, application })); return true })
}
async function breakerAction(action, expectedSlot, productId = null) {
  if (slot.value?.id !== expectedSlot) return false
  const success = await act(async () => { updateSlot(await api(`slots/${expectedSlot}/password-breaker/`, { action, product_id: productId })); return true })
  if (action === 'login') {
    loginDialog.value = false
    if (success) { activate('terminal'); await nextTick(); document.querySelector('input[aria-label$=" command"]')?.focus({ preventScroll: true }) }
  }
  return success
}
function closeLoginDialog() {
  loginDialog.value = false
  nextTick(() => document.querySelector('input[aria-label$=" command"]')?.focus({ preventScroll: true }))
}
async function openCracker() {
  if (!slot.value?.connected) { error.value = 'Connect to a server before opening its login.'; return }
  if (!slot.value.catalog.some(item => item.kind === 'cracker' && slot.value.installed_software.includes(item.id))) { error.value = 'Buy a Lockpick license before opening the decoder.'; return }
  loginDialog.value = true
}
watch(() => `${slot.value?.id}:${slot.value?.created_at}:${slot.value?.connected}`, () => { loginDialog.value = false })
async function jumpBackdoor(target) {
  await act(async () => {
    updateSlot(await api(`slots/${slot.value.id}/backdoors/`, { target }))
    activate('terminal')
  })
}
async function contractAction(action, job) {
  await act(async () => {
    updateSlot(await api(`slots/${slot.value.id}/contracts/`, { action, contract_id: job.id }))
    notice.value = action === 'accept' ? `Contract ${job.id} reserved. Open your tools to begin.` : 'Contract aborted. Liability and reputation loss recorded.'
  })
}
async function trade(action, productId) {
  await act(async () => { const product = [...slot.value.catalog, ...slot.value.black_market_catalog].find(item => item.id === productId); updateSlot(await api(`slots/${slot.value.id}/loadout/`, { action, product_id: productId })); if (action === 'buy' && product?.category === 'software') { buildMode.value = 'software'; buildProduct.value = product } else if (action === 'equip' && product) { buildMode.value = 'hardware'; buildProduct.value = product }; notice.value = action === 'buy' ? (product?.kind === 'cleaner' ? 'Logcleaner installed in the primary terminal.' : 'Purchase complete. Hardware must be fitted; software applets are ready in the primary terminal.') : action === 'sell' ? 'Product sold. Payment recorded in your ledger.' : 'Component fitted.' })
}
async function saveRoute(nodes) {
  await act(async () => { updateSlot(await api(`slots/${slot.value.id}/route/`, { nodes })); notice.value = 'Proxy chain committed. Connection leases are charged when dialing a target.' })
}
async function editDirectory(action, serverId) {
  await act(async () => {
    updateSlot(await api(`slots/${slot.value.id}/directory/`, { action, server_id: serverId }))
    notice.value = action === 'add' ? 'Server added to your Atlas directory.' : 'Server removed from Atlas and the committed proxy chain.'
  })
}
async function restartRunner() {
  await act(async () => { updateSlot(await api(`slots/${slot.value.id}/restart/`, { confirmation: restartConfirmation.value })); restartOpen.value = false; restartConfirmation.value = ''; page.value = 'overview'; notice.value = 'Runner restarted. This slot has a fresh machine and 1,200 CPH.'; await loadSaves() })
}
function openSaves() { act(async () => { await loadSaves(); page.value = 'saves' }) }
async function refreshTrace() {
  if (!slot.value || busy.value || polling) return
  const urgent = slot.value.connected || slot.value.ransomware_ops.length || slot.value.broker_next_at || page.value === 'broker'
  // Idle pages still advance IRC every ten seconds; its own page already polls.
  if (!urgent && (page.value === 'irc' || Date.now() - responseTime.value < 10000)) return
  polling = true
  const marker = revision, id = slot.value.id
  try { const result = await api(`slots/${id}/`); if (revision === marker && !busy.value && slot.value?.id === id) updateSlot(result) } catch { /* commands report actionable connection errors */ } finally { polling = false }
}
onMounted(async () => {
  clock = setInterval(() => { now.value = Date.now() }, 1000)
  poller = setInterval(refreshTrace, 1000)
  try { const session = await api('session/'); user.value = session.user; ranks.value = session.ranks; currency.value = session.currency; if (user.value) await loadSaves() } catch (e) { error.value = e.message } finally { loading.value = false }
})
onUnmounted(() => { clearInterval(clock); clearInterval(poller) })
</script>

<template>
  <div class="app-shell" :inert="loginDialog || !!buildProduct">
    <aside class="sidebar">
      <a class="brand" href="#" @click.prevent="page = 'overview'" aria-label="Netrunner home"><span class="brand-icon"><Terminal :size="23" /></span><span>netrunner<span class="brand-dot">_</span><small>INDEPENDENT NETWORK ACCESS</small></span></a>
      <div class="workspace-label">WORKSPACE <span>V.0.19</span></div>
      <nav aria-label="Main navigation">
        <button v-for="item in nav" :key="item.id" :aria-label="item.label" :class="['nav-item', { active: page === item.id }]" @click="navigate(item)" :disabled="!slot || busy" :aria-current="page === item.id ? 'page' : undefined"><component :is="item.icon" :size="18" /><span>{{ item.label }}</span><span v-if="item.id === 'broker' && slot" class="nav-count">{{ slot.contracts.length }}</span><span v-if="item.id === 'terminal' && slot?.active_contract" class="live-dot"></span></button>
      </nav>
      <div class="sidebar-note"><Radio :size="17" /><span>A quieter kind of power.<br><strong>Leave no trace.</strong></span></div>
      <button v-if="user" class="mobile-saves icon-button" :disabled="busy" @click="openSaves" aria-label="Manage save slots"><Layers3 :size="20" /></button>
      <div class="sidebar-bottom">
        <div class="connection"><i></i> {{ user ? 'ENCRYPTED CONNECTION' : 'SECURE CHANNEL AVAILABLE' }}<span>256</span></div>
        <button v-if="user" class="profile" :disabled="busy" @click="openSaves"><span class="avatar">{{ (slot?.alias || user.username).slice(0, 2).toUpperCase() }}</span><span><strong>{{ slot?.alias || user.username }}</strong><small>{{ slot ? `SLOT 0${slot.position} / ${slot.rank_name.toUpperCase()}` : 'SELECT A SAVE SLOT' }}</small></span><Layers3 :size="16" /></button>
        <div v-else class="profile"><span class="avatar"><Fingerprint :size="20" /></span><span><strong>Identity unverified</strong><small>AWAITING AUTHENTICATION</small></span></div>
      </div>
    </aside>

    <div class="main-shell">
      <header class="topbar"><div class="breadcrumb">NETWORK <ChevronRight :size="12" /><span>{{ !user ? 'ACCESS TERMINAL' : !slot ? 'SAVE SLOTS' : page.replace('gateway', 'MY GATEWAY').replace('bank', 'CIPHER BANK').toUpperCase() }}</span></div><div class="topbar-right"><button v-if="slot" class="desktop-launch-button" aria-label="Terminal launcher" :disabled="busy" @click="launchApplication('terminal')"><Terminal :size="16" /><span>Terminal</span></button><button v-if="slot" class="desktop-launch-button" aria-label="Application launcher" @click="page = 'launcher'"><Grid2X2 :size="16" /><span>Applications</span></button><span class="system-status"><i></i> SYSTEM ONLINE</span><span class="utc">{{ new Date(now).toISOString().slice(11,19) }} UTC</span><button v-if="user" class="icon-button" @click="logOut" :disabled="busy" aria-label="Sign out"><LogOut :size="16" /></button></div></header>
      <main>
        <div v-if="error" class="message error" role="alert"><span>{{ error }}</span><button @click="error = ''" aria-label="Dismiss error"><X :size="16" /></button></div>
        <div v-if="notice" class="message success" role="status"><Check :size="16" />{{ notice }}</div>
        <div v-if="loading || (busy && user && !slot)" class="loading" role="status"><span class="live-dot"></span> ESTABLISHING SECURE CONNECTION…</div>

        <template v-else-if="!user">
          <div class="eyebrow"><span class="live-dot"></span> YOUR NEXT LIFE STARTS HERE</div>
          <section class="welcome-layout">
            <div class="welcome-copy"><div class="version-tag">NETRUNNER // EARLY ACCESS</div><h1>The network<br>doesn't sleep.<br><span>Neither do you.</span></h1><p>One gateway. A borrowed identity. An entire world behind a firewall. Take the contract, follow the signal, and build your reputation in the shadows.</p><div class="welcome-features"><span><ShieldCheck :size="16" /> Your identity. Your rules.</span><span><Layers3 :size="16" /> Three independent save slots.</span><span><Globe :size="16" /> A fictional network. Real decisions.</span></div><div class="signal-line"><span></span><small>NO SIGNAL IS EVER TRULY LOST</small></div></div>
            <section class="auth-panel"><div class="panel-title"><span><LockKeyhole :size="16" /> IDENTITY TERMINAL</span><i class="live-dot"></i></div><div class="auth-body"><span class="micro">// ESTABLISH YOUR IDENTITY</span><h2>{{ authMode === 'register' ? 'Enter the network.' : 'Welcome back, runner.' }}</h2><p>{{ authMode === 'register' ? 'Every legend begins with an alias.' : 'Your gateway is waiting for you.' }}</p><div class="tabs"><button :class="{ selected: authMode === 'register' }" @click="authMode = 'register'; error = ''">New identity</button><button :class="{ selected: authMode === 'login' }" @click="authMode = 'login'; error = ''">Sign in</button></div><form @submit.prevent="authenticate"><label for="handle">RUNNER HANDLE</label><div class="input-wrap"><span>@</span><input id="handle" v-model="username" autocomplete="username" maxlength="24" pattern="[A-Za-z0-9_-]+" placeholder="Choose your handle" required /></div><label for="password">PASSPHRASE</label><div class="input-wrap"><LockKeyhole :size="15" /><input id="password" v-model="password" type="password" :autocomplete="authMode === 'register' ? 'new-password' : 'current-password'" :minlength="authMode === 'register' ? 8 : 1" maxlength="128" placeholder="Enter your passphrase" required /></div><small class="field-hint" v-if="authMode === 'register'">8+ characters. Avoid common or all-numeric passwords.</small><button class="button primary wide" :disabled="busy">{{ busy ? 'Authenticating…' : authMode === 'register' ? 'Create identity' : 'Connect to gateway' }}<ArrowRight :size="17" /></button></form><div class="auth-footer"><ShieldCheck :size="14" /> Session protected. Passwords securely hashed.</div></div></section>
          </section>
          <section class="intro-strip"><div><span class="micro">01 / CONNECT</span><h3>Find your way in.</h3><p>Build a gateway that opens doors.</p></div><div><span class="micro">02 / EXECUTE</span><h3>Make the connection.</h3><p>Take contracts. Stay ahead of the trace.</p></div><div><span class="micro">03 / DISAPPEAR</span><h3>Become a ghost.</h3><p>Get paid. Rank up. Leave nothing behind.</p></div></section>
        </template>

        <template v-else-if="!slot || page === 'saves'">
          <div class="eyebrow">IDENTITY / {{ user.username }}</div><div class="page-heading"><div><h1>Choose your connection<span>_</span></h1><p>Three independent lives. One identity. Progress saves automatically.</p></div></div>
          <div class="save-grid"><section class="panel save-card" v-for="position in [1,2,3]" :key="position"><div class="panel-title"><span>SAVE SLOT 0{{ position }}</span><Layers3 :size="16" /></div><template v-if="saves.find(s => s.position === position)"><div class="save-body"><Fingerprint :size="32" /><h2>{{ saves.find(s => s.position === position).alias }}</h2><p>{{ saves.find(s => s.position === position).rank_name }} / {{ money(saves.find(s => s.position === position).balance) }} CPH</p><button class="button primary wide" :disabled="busy" @click="act(() => selectSlot(saves.find(s => s.position === position)))">Connect <ArrowRight :size="16" /></button></div></template><form v-else class="save-body" @submit.prevent="selectedPosition = position; createSave()"><Plus :size="32" /><h2>A clean slate.</h2><p>Your next story starts here.</p><label :for="`alias-${position}`">RUNNER ALIAS</label><input :id="`alias-${position}`" :value="selectedPosition === position ? alias : ''" @input="selectedPosition = position; alias = $event.target.value" maxlength="24" placeholder="Enter an alias" required /><button class="button secondary wide" :disabled="busy">Initialize slot <ArrowRight :size="16" /></button></form></section></div>
        </template>

        <template v-else>
          <div v-if="slot.running_apps.length" class="application-dock" aria-label="Running applications"><div v-for="app in slot.running_apps" :key="app.id" :class="{ selected: activeConsole === app.id && !['overview', 'launcher', 'workspace'].includes(page) }"><button @click="activate(app.id)"><span class="green-dot"></span>{{ app.name }}</button><button :aria-label="`Stop ${app.name}`" :disabled="busy" @click="closeApplication(app.id)"><X :size="12" /></button></div></div>
          <template v-if="page === 'overview'">
            <div class="eyebrow"><span class="live-dot"></span> PERSONAL DESKTOP / SLOT 0{{ slot.position }}</div>
            <div class="page-heading"><div><h1>Welcome back, {{ slot.alias }}<span>_</span></h1><p>Your gateway is online. What you do with it is up to you.</p></div><button class="button secondary" @click="page = 'launcher'">Application launcher <Grid2X2 :size="16" /></button></div>
            <section class="stats-grid"><article class="stat-card"><div class="stat-label">AVAILABLE BALANCE <Landmark :size="17" /></div><div class="stat-value">{{ money(slot.balance) }} <span>CPH</span></div><div class="stat-foot"><span class="green-dot"></span>Compute time and route leases cost CPH</div></article><article class="stat-card"><div class="stat-label">RUNNER RANK <ShieldCheck :size="17" /></div><div class="stat-value rank-value">{{ slot.rank_name }} <span>0{{ slot.rank + 1 }}</span></div><div class="stat-foot">{{ slot.reputation }} REP <span class="mini-progress"><i :style="{ width: `${progress}%` }"></i></span><span>{{ slot.next_rank_at || 'MAX' }}</span></div></article><article class="stat-card"><div class="stat-label">MEMORY ALLOCATION <Cpu :size="17" /></div><div class="stat-value">{{ slot.ram_used }} <span>/ {{ slot.equipment.memory.ram }} GB</span></div><div class="stat-foot">{{ slot.running_apps.length }} processes / {{ slot.completed }} contracts completed</div></article></section>
            <div class="desktop-grid"><section class="panel machine-panel"><div class="panel-title"><span><Cpu :size="16" /> YOUR MACHINE</span><span class="panel-meta">{{ slot.equipment.gateway.name.toUpperCase() }}</span></div><div class="machine-visual"><div class="machine-orbit"></div><Cpu :size="65" :stroke-width="1" /><span>{{ slot.equipment.gateway.name }}</span><small>{{ slot.equipment.gateway.hops }} PROXY HOPS / {{ slot.equipment.gateway.stealth }} STEALTH</small></div><div class="machine-components"><div v-for="(item, kind) in slot.equipment" :key="kind"><span>{{ kind.toUpperCase() }}</span><strong>{{ item.name }}</strong></div></div></section><section class="panel desktop-brief"><div class="panel-title"><span><BriefcaseBusiness :size="16" /> ASSIGNMENT DESK</span><span class="panel-meta">{{ slot.active_contract ? 'RESERVED' : 'NO ASSIGNMENT' }}</span></div><div class="briefing-body"><span class="micro">{{ slot.active_contract ? `CONTRACT ${slot.active_contract.id}` : '// INDEPENDENT OPERATOR' }}</span><h2>{{ slot.active_contract?.title || 'No handrails.\nNo shortcuts.' }}</h2><p>{{ slot.active_contract?.description || 'The broker supplies objectives. Your applications supply capabilities. You choose the tools, the route, and the risk.' }}</p><div v-if="slot.active_contract" class="brief-target">{{ slot.active_contract.target_name || slot.active_contract.target }}</div><div class="desk-facts"><span>{{ slot.installed_software.length }} TOOL LICENSES</span><span>{{ slot.proxy_route.length }} COMMITTED PROXIES</span><span>{{ slot.contracts.filter(job => !cooled(job)).length }} AVAILABLE JOBS</span></div></div></section></div>
            <section class="panel recovery-panel"><div><span class="micro">RUNNER RECOVERY</span><p>New jobs return over time. Sell spare equipment if funds are tight. Restarting erases this slot's progress and restores starter funding.</p></div><button class="text-link danger-text" @click="restartConfirmation = ''; restartOpen = true">Restart this runner</button></section>
          </template>
          <AppLauncher v-else-if="page === 'launcher'" :slot="slot" :busy="busy" @launch="launchApplication" @close="closeApplication" @use="useApplet" />
          <NetworkMap v-else-if="page === 'atlas'" :slot="slot" :busy="busy" @save="saveRoute" @directory="editDirectory" />
          <ServerHistory v-else-if="page === 'history'" :key="`${slot.id}:${slot.created_at}`" :slot-id="slot.id" :api="api" :remote-target="slot.remote_target" />
          <IrcUnderground v-else-if="page === 'irc'" :key="`${slot.id}:${slot.created_at}`" :slot="slot" :busy="busy" :api="api" :send="sendIrc" />
          <ExchangeView v-else-if="page === 'exchange'" :slot="slot" :busy="busy" @trade="trade" @use="useApplet" />
          <BrokerView v-else-if="page === 'broker'" :slot="slot" :busy="busy" :now="now" :offset="serverOffset" :ranks="ranks" @action="contractAction" />
          <template v-else-if="page === 'console' && currentProcess">
            <div class="eyebrow">OPERATIONS / {{ activeConsole.toUpperCase() }}</div><div class="page-heading"><div><h1>{{ currentProcess.name }}<span>_</span></h1><p>{{ currentProcess.ram }} GB allocated. Commands run inside this terminal.</p></div><span class="badge">{{ slot.connected ? 'REMOTE SESSION' : 'LOCAL SESSION' }}</span></div>
            <ServerLogin v-if="activeConsole === 'terminal'" :slot="slot" :busy="busy" @open-cracker="openCracker" />
            <TerminalConsole :slot="slot" :application="activeConsole" :busy="busy" :send="sendCommand" @open-cracker="openCracker" />
          </template>
          <template v-else-if="page === 'blackmarket' && slot.market_unlocked">
            <BlackMarket :slot="slot" :busy="busy" @trade="trade" />
          </template>
          <BackdoorsView v-else-if="page === 'backdoors' && slot.installed_software.includes('rootkit-epic')" :slot="slot" :busy="busy" @connect="jumpBackdoor" />
          <template v-else-if="page === 'bank'">
            <div class="eyebrow">SERVICES / CIPHER BANK TERMINAL</div><div class="page-heading"><div><h1>Your money. Off the grid<span>_</span></h1><p>Every route, compute charge, trade, and contract payment has a receipt.</p></div><span class="badge"><LockKeyhole :size="12" /> PRIVATE LEDGER</span></div><section class="bank-hero"><div><span class="micro">CIPHER // CURRENT ACCOUNT</span><h2>{{ money(slot.balance) }} <span>CPH</span></h2><p>Available balance</p></div><div class="bank-account"><Landmark :size="32" :stroke-width="1" /><span>ACCOUNT HOLDER</span><strong>{{ slot.alias }}</strong><small>NR-{{ String(slot.id).padStart(8,'0') }} / SLOT 0{{ slot.position }}</small></div></section>
            <TerminalConsole :slot="slot" application="bank" :busy="busy" :send="sendCommand" />
            <section class="panel ledger bank-ledger"><div class="panel-title"><span><Activity :size="16" /> TRANSACTION HISTORY</span><span class="panel-meta">LATEST 30 ENTRIES</span></div><div class="ledger-row" v-for="entry in slot.ledger" :key="entry.id"><div><span class="transaction-icon"><ArrowUpRight :size="16" /></span><strong>{{ entry.description }}</strong></div><time>{{ new Date(entry.created_at).toISOString().slice(0,16).replace('T',' ') }}</time><strong :class="entry.amount > 0 ? 'positive' : 'negative'">{{ entry.amount > 0 ? '+' : '−' }}{{ money(Math.abs(entry.amount)) }} <small>CPH</small></strong></div></section>
          </template>
          <KeepAlive><WorkspaceView v-if="page === 'workspace'" ref="workspaceRef" :key="`${user.username}:${slot.id}:${slot.created_at}`" :slot="slot" :username="user.username" :busy="busy" :api="api" :send="sendCommand" :launch="(product, id) => launchApplication(product, true, id)" :close="(app, id) => closeApplication(app, true, id)" :now="now" :offset="serverOffset" :ranks="ranks" :breaker-action="breakerAction" @open-cracker="openCracker" @route="saveRoute" @directory="editDirectory" @trade="trade" @contract="contractAction" @jump="jumpBackdoor" /></KeepAlive>
          <KeepAlive><FieldNotes v-if="page === 'notes'" :key="`${user.username}:${slot.id}:${slot.created_at}`" :slot-id="slot.id" :username="user.username" :api="api" /></KeepAlive>
          <section v-if="slot.ransomware_ops.length" class="panel ransomware-panel"><div class="panel-title"><span>ECLIPSE / ACTIVE INSTANCES</span><span class="panel-meta">{{ slot.ransomware_ops.length }} / 3</span></div><div v-for="operation in slot.ransomware_ops" :key="operation.target" class="ransomware-row"><code>{{ operation.ip_address || operation.target }}</code><span>{{ Math.max(0, Math.ceil((Date.parse(operation.due_at) - now - serverOffset) / 1000)) }}s</span><strong>{{ operation.reward }} CPH</strong></div></section>
          <div v-if="restartOpen" class="modal-backdrop" @click.self="restartOpen = false"><section class="panel restart-dialog" role="dialog" aria-modal="true" aria-labelledby="restart-title"><div class="panel-title"><span>RUNNER RESTART</span><button class="icon-button" @click="restartOpen = false" aria-label="Cancel restart"><X :size="17" /></button></div><form @submit.prevent="restartRunner"><h2 id="restart-title">Start over in slot 0{{ slot.position }}?</h2><p>This erases {{ slot.alias }}'s balance, reputation, contracts, equipment, routes, local files, notes, server histories, workspace arrangement, and transaction history. Your account and other save slots stay intact.</p><label for="restart-confirmation">TYPE {{ slot.alias }} TO CONFIRM</label><input id="restart-confirmation" v-model="restartConfirmation" autocomplete="off" required /><div class="dialog-actions"><button type="button" class="button secondary" @click="restartOpen = false">Cancel</button><button class="button primary" :disabled="busy || restartConfirmation !== slot.alias">Erase progress and restart</button></div></form></section></div>
        </template>
        <footer><span>NETRUNNER <span class="footer-slash">/</span> A WORLD BEHIND THE FIREWALL</span><span>FICTIONAL NETWORK. INDEPENDENT OPERATORS.<span class="green-dot"></span></span></footer>
      </main>
    </div>
  </div>
  <Teleport to="body"><TraceTracker v-if="user && slot" :slot="slot" :remaining="remaining" :elapsed="elapsed" /></Teleport>
  <ModalDialog v-if="loginDialog && slot" title="Remote system login" :restore-focus="false" @close="closeLoginDialog"><PasswordBreaker :slot="slot" :busy="busy" :action="breakerAction" modal @exit="closeLoginDialog" /></ModalDialog>
  <BuildSplash v-if="buildProduct" :product="buildProduct" :mode="buildMode" @close="buildProduct = null" />
</template>
