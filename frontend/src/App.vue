<script setup>
import { computed, ref, onMounted, onUnmounted, nextTick } from 'vue'
import { Terminal, Network, BriefcaseBusiness, Cpu, Landmark, Layers3, ArrowUpRight, ArrowRight, ChevronRight, Radio, ShieldCheck, LogOut, Plus, X, Check, Globe, Fingerprint, Activity, HardDrive, Code2, LockKeyhole, Zap } from 'lucide-vue-next'

const user = ref(null), slot = ref(null), saves = ref([]), page = ref('overview'), loading = ref(true), busy = ref(false), error = ref(''), notice = ref('')
const authMode = ref('register'), username = ref(''), password = ref(''), alias = ref(''), commandText = ref(''), logEl = ref(null), now = ref(Date.now()), selectedPosition = ref(1)
const ranks = ref([]), currency = ref({ name: 'Cipher', symbol: 'CPH' })
let clock
const nav = [{ id: 'overview', label: 'Overview', icon: Network }, { id: 'broker', label: 'Contract broker', icon: BriefcaseBusiness }, { id: 'terminal', label: 'Remote terminal', icon: Terminal }, { id: 'gateway', label: 'My gateway', icon: Cpu }, { id: 'bank', label: 'Cipher bank', icon: Landmark }]
const money = n => new Intl.NumberFormat('en-US').format(n ?? 0)
const progress = computed(() => slot.value?.next_rank_at ? Math.min(100, (slot.value.reputation - slot.value.rank_floor) / (slot.value.next_rank_at - slot.value.rank_floor) * 100) : 100)
const remaining = computed(() => slot.value?.mission_started ? Math.max(0, 180 - Math.floor((now.value - Date.parse(slot.value.mission_started)) / 1000)) : 180)
const power = computed(() => slot.value ? slot.value.hardware + slot.value.gateway + slot.value.software : 0)
const suggested = computed(() => ['scan', 'breach', 'extract', 'wipe', 'disconnect'][slot.value?.mission_step || 0])

async function api(path, data) {
  const csrf = document.cookie.split('; ').find(c => c.startsWith('csrftoken='))?.split('=')[1]
  const response = await fetch('/api/' + path, { method: data === undefined ? 'GET' : 'POST', headers: { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRFToken': csrf } : {}) }, credentials: 'same-origin', ...(data !== undefined ? { body: JSON.stringify(data) } : {}) })
  const result = await response.json().catch(() => ({ error: 'Terminal unavailable. Check the server connection.' }))
  if (!response.ok) throw new Error(result.error || 'Request failed. Please reconnect.')
  return result
}
async function act(fn) {
  if (busy.value) return
  busy.value = true; error.value = ''; notice.value = ''
  try { await fn() } catch (e) { error.value = e.message } finally { busy.value = false }
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
  slot.value = await api(`slots/${save.id}/`)
  try { localStorage.setItem('netrunner.slot', save.id) } catch { /* storage is optional */ }
  page.value = 'overview'
}
async function authenticate() {
  await act(async () => {
    await api(authMode.value === 'register' ? 'register/' : 'login/', { username: username.value, password: password.value })
    user.value = (await api('session/')).user
    password.value = ''
    await loadSaves()
  })
}
async function createSave() {
  await act(async () => {
    const created = await api('slots/', { position: selectedPosition.value, alias: alias.value })
    slot.value = created
    try { localStorage.setItem('netrunner.slot', created.id) } catch { /* storage is optional */ }
    alias.value = ''; page.value = 'overview'; await loadSaves()
  })
}
async function logOut() {
  await act(async () => { await api('logout/', {}); user.value = null; slot.value = null; saves.value = []; page.value = 'overview' })
}
async function acceptContract(contract) {
  await act(async () => { slot.value = await api(`slots/${slot.value.id}/accept/`, { contract_id: contract.id }); page.value = 'terminal' })
}
async function sendCommand(cmd = commandText.value) {
  if (!cmd.trim()) return
  await act(async () => { slot.value = await api(`slots/${slot.value.id}/command/`, { command: cmd }); commandText.value = ''; await nextTick(); if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight })
}
async function buyUpgrade(kind) {
  await act(async () => { slot.value = await api(`slots/${slot.value.id}/upgrade/`, { kind }); notice.value = 'Upgrade installed. Your gateway is ready.' })
}
function openSaves() { act(async () => { await loadSaves(); page.value = 'saves' }) }
onMounted(async () => {
  clock = setInterval(() => { now.value = Date.now() }, 1000)
  try { const session = await api('session/'); user.value = session.user; ranks.value = session.ranks; currency.value = session.currency; if (user.value) await loadSaves() } catch (e) { error.value = e.message } finally { loading.value = false }
})
onUnmounted(() => clearInterval(clock))
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <a class="brand" href="#" @click.prevent="page = 'overview'" aria-label="Netrunner home"><span class="brand-icon"><Terminal :size="23" /></span><span>netrunner<span class="brand-dot">_</span><small>INDEPENDENT NETWORK ACCESS</small></span></a>
      <div class="workspace-label">WORKSPACE <span>V.0.1</span></div>
      <nav aria-label="Main navigation">
        <button v-for="item in nav" :key="item.id" :aria-label="item.label" :class="['nav-item', { active: page === item.id }]" @click="page = item.id" :disabled="!slot"><component :is="item.icon" :size="18" /><span>{{ item.label }}</span><span v-if="item.id === 'broker' && slot" class="nav-count">{{ slot.contracts.length }}</span><span v-if="item.id === 'terminal' && slot?.active_contract" class="live-dot"></span></button>
      </nav>
      <div class="sidebar-note"><Radio :size="17" /><span>A quieter kind of power.<br><strong>Leave no trace.</strong></span></div>
      <button v-if="user" class="mobile-saves icon-button" @click="openSaves" aria-label="Manage save slots"><Layers3 :size="20" /></button>
      <div class="sidebar-bottom">
        <div class="connection"><i></i> {{ user ? 'ENCRYPTED CONNECTION' : 'SECURE CHANNEL AVAILABLE' }}<span>256</span></div>
        <button v-if="user" class="profile" @click="openSaves"><span class="avatar">{{ (slot?.alias || user.username).slice(0, 2).toUpperCase() }}</span><span><strong>{{ slot?.alias || user.username }}</strong><small>{{ slot ? `SLOT 0${slot.position} / ${slot.rank_name.toUpperCase()}` : 'SELECT A SAVE SLOT' }}</small></span><Layers3 :size="16" /></button>
        <div v-else class="profile"><span class="avatar"><Fingerprint :size="20" /></span><span><strong>Identity unverified</strong><small>AWAITING AUTHENTICATION</small></span></div>
      </div>
    </aside>

    <div class="main-shell">
      <header class="topbar"><div class="breadcrumb">NETWORK <ChevronRight :size="12" /><span>{{ !user ? 'ACCESS TERMINAL' : !slot ? 'SAVE SLOTS' : page.replace('gateway', 'MY GATEWAY').replace('bank', 'CIPHER BANK').toUpperCase() }}</span></div><div class="topbar-right"><span class="system-status"><i></i> SYSTEM ONLINE</span><span class="utc">{{ new Date(now).toISOString().slice(11,19) }} UTC</span><button v-if="user" class="icon-button" @click="logOut" :disabled="busy" aria-label="Sign out"><LogOut :size="16" /></button></div></header>
      <main>
        <div v-if="error" class="message error" role="alert"><span>{{ error }}</span><button @click="error = ''" aria-label="Dismiss error"><X :size="16" /></button></div>
        <div v-if="notice" class="message success" role="status"><Check :size="16" />{{ notice }}</div>
        <div v-if="loading" class="loading"><span class="live-dot"></span> ESTABLISHING SECURE CONNECTION…</div>

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
          <template v-if="page === 'overview'">
            <div class="eyebrow"><span class="live-dot"></span> GATEWAY CONNECTED / SLOT 0{{ slot.position }}</div><div class="page-heading"><div><h1>Welcome back, {{ slot.alias }}<span>_</span></h1><p>The network is quiet. Let's keep it that way.</p></div><button class="button secondary" @click="page = 'broker'">Find a contract <ArrowUpRight :size="16" /></button></div>
            <section class="stats-grid"><article class="stat-card"><div class="stat-label">AVAILABLE BALANCE <Landmark :size="17" /></div><div class="stat-value">{{ money(slot.balance) }} <span>CPH</span></div><div class="stat-foot"><span class="green-dot"></span>{{ currency.name }} wallet / connected</div></article><article class="stat-card"><div class="stat-label">RUNNER RANK <ShieldCheck :size="17" /></div><div class="stat-value rank-value">{{ slot.rank_name }} <span>0{{ slot.rank + 1 }}</span></div><div class="stat-foot">{{ slot.reputation }} REP <span class="mini-progress"><i :style="{ width: `${progress}%` }"></i></span><span>{{ slot.next_rank_at || 'MAX' }}</span></div></article><article class="stat-card"><div class="stat-label">CONTRACTS COMPLETED <BriefcaseBusiness :size="17" /></div><div class="stat-value">{{ String(slot.completed).padStart(2,'0') }}</div><div class="stat-foot">{{ slot.active_contract ? '1 active connection' : 'Ready for your next assignment' }}</div></article></section>
            <div class="dashboard-grid"><section class="panel network-panel"><div class="panel-title"><span><Network :size="16" /> NETWORK TOPOLOGY</span><span class="panel-meta">ENCRYPTED / LOCAL</span></div><div class="network-map"><div class="map-grid"></div><svg viewBox="0 0 600 240" aria-hidden="true"><path d="M75 120 L230 120 L360 55 L520 55 M230 120 L360 185 L520 185 M230 120 L460 120" /></svg><div class="node node-origin"><span><Cpu :size="23" /></span><strong>YOUR GATEWAY</strong><small>127.0.0.1 / LOCAL</small></div><div class="node node-relay"><span><Radio :size="21" /></span><strong>VEIL RELAY</strong><small>ENCRYPTED</small></div><div class="node node-top"><span><BriefcaseBusiness :size="18" /></span><strong>BROKER</strong></div><div class="node node-target"><span><Globe :size="21" /></span><strong>{{ slot.active_contract ? 'TARGET NODE' : 'THE NETWORK' }}</strong></div><div class="node node-bank"><span><Landmark :size="18" /></span><strong>CIPHER BANK</strong></div><div class="map-caption"><span class="live-dot"></span>{{ slot.active_contract ? `CONNECTED TO ${slot.active_contract.target}` : 'NO ACTIVE REMOTE CONNECTION' }}</div></div><div class="panel-bottom"><ShieldCheck :size="14" />{{ slot.active_contract ? 'Remote session in progress. Monitor your trace.' : 'Your gateway is secure. All systems operational.' }}<button @click="page = slot.active_contract ? 'terminal' : 'gateway'">{{ slot.active_contract ? 'Open terminal' : 'View gateway' }} <ArrowUpRight :size="14" /></button></div></section><section class="panel briefing"><div class="panel-title"><span><Terminal :size="16" /> RUNNER BRIEFING</span><span class="panel-meta">READ ME</span></div><div class="briefing-body"><span class="micro">// A MESSAGE FROM THE BROKER</span><h2>Small footprints.<br> Big opportunities.</h2><p>Only jobs within one rank of your clearance reach your inbox. Finish clean, get paid, and move up.</p><button class="text-link" @click="page = 'broker'">Browse available contracts <ArrowRight :size="15" /></button><div class="briefing-info"><Activity :size="17" /><span>{{ slot.contracts.length }} contracts match your clearance.</span></div></div></section></div>
            <section class="panel"><div class="panel-title"><span><BriefcaseBusiness :size="16" /> AVAILABLE CONTRACTS</span><button class="text-link small" @click="page = 'broker'">View all <ArrowUpRight :size="14" /></button></div><div class="contract-row" v-for="contract in slot.contracts.slice(0,2)" :key="contract.id"><span class="contract-icon"><BriefcaseBusiness :size="18" /></span><div class="contract-row-title"><strong>{{ contract.title }}</strong><small>{{ contract.client }} <span>/ {{ contract.target }}</span></small></div><span class="badge">{{ ranks[contract.rank] }}</span><strong class="reward">{{ money(contract.reward) }} <small>CPH</small></strong><button class="icon-button" @click="page = 'broker'" :aria-label="`View ${contract.title}`"><ArrowUpRight :size="18" /></button></div></section>
          </template>

          <template v-else-if="page === 'broker'">
            <div class="eyebrow">SERVICES / CONTRACT BROKER</div><div class="page-heading"><div><h1>Opportunity is encrypted<span>_</span></h1><p>Take the job. Complete the objective. Leave no trace.</p></div><span class="badge">CLEARANCE: {{ slot.rank_name.toUpperCase() }} ± 1</span></div><div class="info-banner"><ShieldCheck :size="18" /><span>Showing ranks {{ ranks[Math.max(0, slot.rank - 1)] }} through {{ ranks[Math.min(4, slot.rank + 1)] }}. Abandoned or traced contracts cost 60 reputation.</span></div><div class="contract-grid"><article class="panel contract-card" v-for="contract in slot.contracts" :key="contract.id"><div class="contract-card-top"><span class="micro">NR-{{ contract.id.replace('-', '0') }}</span><span :class="['badge', { elevated: contract.rank > slot.rank }]">{{ ranks[contract.rank] }}</span></div><BriefcaseBusiness :size="25" class="contract-glyph" /><h2>{{ contract.title }}</h2><span class="micro">{{ contract.client.toUpperCase() }}</span><p>{{ contract.description }}</p><div class="contract-spec"><span>System power required</span><strong :class="{ 'danger-text': power < 3 + contract.rank * 2 }">{{ 3 + contract.rank * 2 }} / yours {{ power }}</strong></div><div class="contract-spec"><span>Reputation</span><strong>+{{ contract.reputation }} REP</strong></div><div class="contract-card-bottom"><strong class="reward">{{ money(contract.reward) }} <small>CPH</small></strong><button class="button secondary" :disabled="busy || !!slot.active_contract || power < 3 + contract.rank * 2" @click="acceptContract(contract)">Accept job <ArrowUpRight :size="15" /></button></div><small v-if="power < 3 + contract.rank * 2" class="field-hint">Upgrade your gateway to meet the power requirement.</small></article></div><button v-if="slot.active_contract" class="button primary" @click="page = 'terminal'">Return to active contract <ArrowRight :size="16" /></button>
          </template>

          <template v-else-if="page === 'terminal'">
            <div class="eyebrow">OPERATIONS / REMOTE TERMINAL</div><div class="page-heading"><div><h1>Follow the signal<span>_</span></h1><p>{{ slot.active_contract ? slot.active_contract.title : 'No active remote connection.' }}</p></div><span v-if="slot.active_contract" :class="['badge', { elevated: remaining < 30 }]">TRACE WINDOW {{ remaining }}s</span></div><section class="panel terminal-panel"><div class="panel-title"><span><Terminal :size="16" /> {{ slot.active_contract?.target || 'LOCAL GATEWAY' }}</span><span class="panel-meta">SIMULATED NETWORK</span></div><div class="terminal-log" ref="logEl" role="log" aria-label="Mission output"><div class="terminal-banner">NETRUNNER REMOTE ACCESS PROTOCOL [v0.1]<br>Authorized simulation environment. All targets are fictional.<br>─────────────────────────────────────────────────────</div><div v-if="!slot.mission_log.length" class="terminal-muted">No connection established. Accept a contract through the broker.</div><pre v-for="(line, i) in slot.mission_log" :key="i">{{ line }}</pre><span v-if="slot.active_contract" class="terminal-cursor">█</span></div><form v-if="slot.active_contract" class="command-line" @submit.prevent="sendCommand()"><label for="command">{{ slot.alias }}@remote:~$</label><input id="command" v-model="commandText" placeholder="Type help for commands" autocomplete="off" spellcheck="false" maxlength="100" :disabled="busy" /><button class="icon-button" :disabled="busy || !commandText.trim()" aria-label="Execute command"><ArrowRight :size="18" /></button></form><div v-else class="terminal-empty-action"><button class="button secondary" @click="page = 'broker'">Connect through broker <ArrowUpRight :size="15" /></button></div></section><div v-if="slot.active_contract" class="terminal-toolbar"><span>NEXT COMMAND <button class="command-chip" @click="commandText = suggested">{{ suggested }}</button></span><button class="text-link danger-text" :disabled="busy" @click="sendCommand('abort')">Abort contract (−60 REP) <X :size="15" /></button></div><div class="terminal-help"><span v-for="(cmd, i) in ['scan', 'breach', 'extract', 'wipe', 'disconnect']" :key="cmd" :class="{ done: slot.mission_step > i }"><Check v-if="slot.mission_step > i" :size="13" /><span v-else>0{{ i + 1 }}</span>{{ cmd }}</span></div>
          </template>

          <template v-else-if="page === 'gateway'">
            <div class="eyebrow">HARDWARE / PERSONAL GATEWAY</div><div class="page-heading"><div><h1>Your edge in the network<span>_</span></h1><p>Invest in the machine that keeps you one step ahead.</p></div><span class="badge">SYSTEM POWER {{ power }} / 15</span></div><div class="info-banner"><Cpu :size="18" /><span>Every upgrade adds one system power. Higher-rank targets require more power. Equipment cannot change during a contract.</span></div><div class="upgrade-grid"><section class="panel upgrade-card" v-for="(item, kind) in slot.upgrades" :key="kind"><div class="panel-title"><span>{{ item.name.toUpperCase() }}</span><span class="panel-meta">LVL 0{{ item.level }}</span></div><div class="upgrade-body"><div class="hardware-art"><component :is="kind === 'hardware' ? Cpu : kind === 'gateway' ? HardDrive : Code2" :size="54" :stroke-width="1" /></div><span class="micro">{{ item.model }}</span><h2>{{ item.name }} MK.{{ item.level }}</h2><p>{{ item.description }}</p><div class="level-blocks"><i v-for="n in 5" :key="n" :class="{ filled: n <= item.level }"></i></div><div class="upgrade-price"><span>NEXT UPGRADE</span><strong>{{ item.level === 5 ? 'MAX LEVEL' : `${money(item.price)} CPH` }}</strong></div><button class="button secondary wide" :disabled="busy || !!slot.active_contract || item.level === 5 || slot.balance < item.price" @click="buyUpgrade(kind)">{{ item.level === 5 ? 'Fully upgraded' : slot.balance < item.price ? 'Insufficient funds' : 'Install upgrade' }}<Zap :size="16" /></button></div></section></div>
          </template>

          <template v-else-if="page === 'bank'">
            <div class="eyebrow">SERVICES / CIPHER BANK TERMINAL</div><div class="page-heading"><div><h1>Your money. Off the grid<span>_</span></h1><p>A separate ledger for every runner. All transactions recorded automatically.</p></div><span class="badge"><LockKeyhole :size="12" /> PRIVATE LEDGER</span></div><section class="bank-hero"><div><span class="micro">CIPHER // CURRENT ACCOUNT</span><h2>{{ money(slot.balance) }} <span>CPH</span></h2><p>Available balance</p></div><div class="bank-account"><Landmark :size="32" :stroke-width="1" /><span>ACCOUNT HOLDER</span><strong>{{ slot.alias }}</strong><small>NR-{{ String(slot.id).padStart(8,'0') }} / SLOT 0{{ slot.position }}</small></div></section><section class="panel ledger"><div class="panel-title"><span><Activity :size="16" /> TRANSACTION HISTORY</span><span class="panel-meta">LATEST 30 ENTRIES</span></div><div class="ledger-header"><span>TRANSACTION</span><span>DATE / UTC</span><span>AMOUNT</span></div><div class="ledger-row" v-for="entry in slot.ledger" :key="entry.id"><div><span class="transaction-icon"><component :is="entry.amount > 0 ? ArrowRight : ArrowUpRight" :size="16" /></span><strong>{{ entry.description }}</strong></div><time>{{ new Date(entry.created_at).toISOString().slice(0,16).replace('T',' ') }}</time><strong :class="entry.amount > 0 ? 'positive' : 'negative'">{{ entry.amount > 0 ? '+' : '−' }}{{ money(Math.abs(entry.amount)) }} <small>CPH</small></strong></div></section>
          </template>
        </template>
        <footer><span>NETRUNNER <span class="footer-slash">/</span> A WORLD BEHIND THE FIREWALL</span><span>FICTIONAL NETWORK. INDEPENDENT OPERATORS.<span class="green-dot"></span></span></footer>
      </main>
    </div>
  </div>
</template>
