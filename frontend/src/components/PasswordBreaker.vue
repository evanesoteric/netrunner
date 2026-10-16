<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { KeyRound } from 'lucide-vue-next'
import ServerLogin from './ServerLogin.vue'
const props = defineProps({ slot: Object, busy: Boolean, action: Function })
const tick = ref(Date.now()), offset = ref(0), port = computed(() => props.slot.login_service?.port)
let timer
watch(() => props.slot.server_time, value => { offset.value = Date.parse(value) - Date.now() }, { immediate: true })
const attempt = computed(() => props.slot.password_break)
const progress = computed(() => attempt.value ? Math.min(.99, Math.max(0, (tick.value + offset.value - Date.parse(attempt.value.started_at)) / (attempt.value.duration * 1000))) : props.slot.authenticated ? 1 : 0)
const seconds = computed(() => attempt.value ? Math.max(0, Math.ceil((Date.parse(attempt.value.finishes_at) - tick.value - offset.value) / 1000)) : 0)
const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%&*+-/<>?'
const decoded = 'ACCESSGRANTED'
const cells = computed(() => Array.from(decoded, (char, i) => ({ locked: props.slot.authenticated || (!!attempt.value && i < Math.floor(progress.value * decoded.length)), char: props.slot.authenticated || (!!attempt.value && i < Math.floor(progress.value * decoded.length)) ? char : attempt.value ? alphabet[(Math.floor(tick.value / 95) * (i + 7) + i * 13) % alphabet.length] : '·' })))
const status = computed(() => props.slot.authenticated ? 'ACCESS GRANTED' : attempt.value ? seconds.value ? 'BREAKING PASSWORD' : 'VERIFYING AUTHENTICATION' : props.slot.password_result === 'failed' ? 'INSUFFICIENT CAPABILITY' : props.slot.password_result === 'cancelled' ? 'ATTEMPT CANCELLED' : 'AWAITING TARGET')
const tool = computed(() => props.slot.running_apps.find(app => app.id === 'cracker'))
const product = computed(() => props.slot.catalog.find(item => item.id === tool.value?.product_id))
async function run(action) { await props.action(action, props.slot.id) }
onMounted(() => { timer = setInterval(() => { tick.value = Date.now() }, 95) })
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <section class="panel password-breaker" aria-label="Lockpick password breaker">
    <div class="panel-title"><span><KeyRound :size="16" /> {{ tool?.name || 'LOCKPICK' }}</span><span class="panel-meta">PASSWORD BREAKER</span></div>
    <ServerLogin :slot="slot" :busy="busy" :show-launch="false" />
    <div class="decoder-display" :class="{ working: attempt, granted: slot.authenticated }">
      <div class="decoder-meta"><span>{{ slot.connected ? `${slot.remote_target}${port ? ':' + port : ''}` : 'NO REMOTE CONNECTION' }}</span><span>CLASS {{ product?.power }} / {{ tool?.ram }} GB</span></div>
      <div class="decoder-cells" aria-hidden="true"><span v-for="(cell, index) in cells" :key="index" :class="{ locked: cell.locked }">{{ cell.char }}</span></div>
      <div class="decoder-progress" role="progressbar" aria-label="Password breaking progress" :aria-valuenow="Math.floor(progress * 100)" aria-valuemin="0" aria-valuemax="100"><i :style="{ width: `${progress * 100}%` }"></i></div>
      <div class="decoder-status"><strong role="status">{{ status }}</strong><span v-if="attempt">{{ seconds ? `${seconds}s ESTIMATED` : 'WAITING FOR SERVER' }}</span></div>
      <p v-if="!slot.connected">Connect to a target from the local terminal to open its login.</p>
      <p v-else-if="slot.authenticated">Remote filesystem mounted. Continue with your other tools.</p>
      <p v-else-if="!port">Scan this server with Cartograph to identify its authentication service.</p>
      <p v-else-if="attempt">Decoding authentication sequence. Trace starts after login.</p>
      <p v-else-if="slot.password_result === 'failed'">This Lockpick cannot defeat the target's security class. Fit a more capable version.</p>
      <p v-else>Ready to attack port {{ port }}. Compute charge: {{ (product?.tier || 0) + 1 }} CPH.</p>
      <div class="decoder-actions"><button v-if="attempt" class="button secondary" :disabled="busy" @click="run('cancel')">Cancel password breaker</button><button v-else class="button primary" :disabled="busy || !slot.connected || slot.authenticated || !port" @click="run('start')">Break password</button></div>
    </div>
  </section>
</template>
