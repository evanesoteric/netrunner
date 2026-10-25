<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
const props = defineProps({ slot: Object, busy: Boolean, api: Function, send: Function })
const channel = ref(null), text = ref(''), error = ref(''), output = ref(null), input = ref(null)
const protocol = ref('SSH'), mode = ref('all'), following = ref(true)
const offers = computed(() => (channel.value?.offers || []).filter(item => item.protocol === protocol.value && (mode.value === 'all' || item.mode === mode.value)))
let timer, version = 0, disposed = false, refreshing = false
function trackScroll() { if (output.value) following.value = output.value.scrollHeight - output.value.clientHeight - output.value.scrollTop < 35 }
async function update(value, force = false) {
  channel.value = value
  await nextTick()
  if (output.value && (following.value || force)) output.value.scrollTop = output.value.scrollHeight
}
async function refresh() {
  if (props.busy || refreshing) return
  refreshing = true
  const marker = version
  try {
    const result = await props.api(`slots/${props.slot.id}/irc/`)
    if (!disposed && marker === version && !props.busy) { error.value = ''; await update(result.irc) }
  } catch (failure) { if (!disposed && marker === version) error.value = failure.message } finally { refreshing = false }
}
async function submit(raw = text.value) {
  if (!raw.trim() || props.busy) return
  version++
  const result = await props.send(raw, props.slot.id)
  if (disposed) return
  if (result) { text.value = ''; error.value = ''; await update(result, true) }
  input.value?.focus({ preventScroll:true })
}
function owned(item) { return channel.value?.inventory.find(entry => entry.id === item.id) }
onMounted(async () => { await refresh(); if (disposed) return; input.value?.focus({ preventScroll:true }); timer = setInterval(refresh, 3000) })
onUnmounted(() => { disposed = true; clearInterval(timer) })
</script>

<template>
  <div class="eyebrow">UNDERGROUND / BOT TRADERS</div>
  <div class="page-heading"><div><h1>IRC Underground<span>_</span></h1><p>Classic channels. Exact fingerprints. Trade CPH for lifetime licenses or single-use exploits.</p></div><span class="badge">{{ slot.balance.toLocaleString() }} CPH</span></div>
  <p v-if="error" role="alert" class="info-banner">{{ error }}</p>
  <div class="irc-layout">
    <section class="panel irc-channel" aria-label="IRC channel">
      <header><strong>#zero-day</strong><span class="micro">CHAT EVERY ~10s / EXPLOIT DROPS EVERY 30s</span></header>
      <details class="irc-members micro"><summary>{{ channel ? `${channel.members.length} USERS ONLINE` : 'Connecting…' }} · #linux meets the underground</summary><div>{{ channel?.members.join(' · ') }}</div></details>
      <div ref="output" class="irc-messages" role="log" aria-label="IRC messages" aria-live="polite" tabindex="0" @scroll="trackScroll">
        <p v-for="message in channel?.messages || []" :key="`${message.at}:${message.nick}:${message.text}`" :class="{ 'irc-self': message.nick === slot.alias, 'irc-system': message.nick === 'ChanServ', 'irc-drop': message.kind === 'drop' }"><time>{{ new Date(message.at).toISOString().slice(11,19) }}</time> <strong>&lt;{{ message.nick }}&gt;</strong> <span>{{ message.text }}</span></p>
      </div>
      <div class="irc-shortcuts"><button v-for="command in ['/help', '/list', '/inventory', '/balance', '/clear']" :key="command" class="text-link" :disabled="busy" @click="submit(command)">{{ command }}</button><button v-if="!following" class="text-link" @click="following = true; update(channel, true)">Jump to latest</button></div>
      <form class="irc-input" @submit.prevent="submit()"><label for="irc-command">{{ slot.alias }} &gt;</label><input id="irc-command" ref="input" v-model="text" maxlength="240" autocomplete="off" spellcheck="false" aria-label="IRC command" placeholder="/msg hexdealer buy ssh-v1-r1-shot" :readonly="busy" /><button class="button secondary" :disabled="busy || !text.trim()">Send</button></form>
      <p class="irc-hint">Chat continues on other pages. Showing the latest {{ channel?.scrollback_limit || 200 }} messages. /clear clears saved chat; purchases stay in your stash and bank ledger.</p>
      <p class="irc-hint">/pay &lt;bot&gt; &lt;CPH&gt; &lt;exploit-id&gt; transfers the exact price and delivers your purchase atomically. These are simulated bots, not live players.</p>
    </section>
    <aside class="irc-trades">
      <section class="panel irc-inventory"><h2>Your exploit stash</h2><p v-if="!channel?.inventory.length" class="micro">No exploits yet. Pick a fingerprint below or ask /list.</p><article v-for="item in channel?.inventory || []" :key="item.id"><code>{{ item.id }}</code><span class="badge">{{ item.mode === 'license' ? 'LIFETIME' : `${item.quantity} ${item.quantity === 1 ? 'COPY' : 'COPIES'}` }}</span><small>{{ item.fingerprint }}</small></article><p class="irc-hint">Primary terminal: scan &lt;host&gt; → connect &lt;host&gt; → exploit &lt;id&gt;. Success opens an admin shell and starts a trace. Clean your logs.</p></section>
      <section class="panel irc-offers"><h2>Pinned trade board</h2><div class="irc-filters"><label>SERVICE<select v-model="protocol" aria-label="Exploit service"><option>SSH</option><option>HTTP</option><option>RDP</option></select></label><label>LICENSE<select v-model="mode" aria-label="Exploit license"><option value="all">All licenses</option><option value="license">Lifetime</option><option value="shot">Single use</option></select></label></div><article v-for="item in offers" :key="item.id" :data-exploit="item.id"><strong>{{ item.fingerprint }}</strong><code>{{ item.id }}</code><span class="micro">{{ item.bot }} / {{ item.mode === 'license' ? 'LIFETIME' : 'SINGLE USE' }} / {{ item.ram }} GB BURST</span><div><b>{{ item.price.toLocaleString() }} CPH</b><button class="button secondary" :disabled="busy || slot.balance < item.price || (item.mode === 'license' && !!owned(item))" @click="submit(`/msg ${item.bot} buy ${item.id}`)">{{ item.mode === 'license' && owned(item) ? 'Owned for life' : 'Trade in channel' }}</button></div></article></section>
    </aside>
  </div>
</template>
