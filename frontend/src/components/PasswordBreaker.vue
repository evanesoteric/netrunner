<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount, useId } from 'vue'
import { KeyRound } from 'lucide-vue-next'
const props = defineProps({ slot: Object, busy: Boolean, action: Function, modal: Boolean })
const emit = defineEmits(['exit'])
const id = useId(), tick = ref(Date.now()), offset = ref(0), port = computed(() => props.slot.login_service?.port)
let timer
watch(() => props.slot.server_time, value => { offset.value = Date.parse(value) - Date.now() }, { immediate: true })
const attempt = computed(() => props.slot.password_break)
const ready = computed(() => props.slot.password_result === 'ready' || props.slot.authenticated)
const progress = computed(() => attempt.value ? Math.min(.99, Math.max(0, (tick.value + offset.value - Date.parse(attempt.value.started_at)) / (attempt.value.duration * 1000))) : ready.value ? 1 : 0)
const seconds = computed(() => attempt.value ? Math.max(0, Math.ceil((Date.parse(attempt.value.finishes_at) - tick.value - offset.value) / 1000)) : 0)
const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%&*+-/<>?'
const password = computed(() => ready.value ? '************' : attempt.value ? Array.from({ length: 12 }, (_, i) => i < Math.floor(progress.value * 12) ? '*' : alphabet[(Math.floor(tick.value / 95) * (i + 7) + i * 13) % alphabet.length]).join('') : '')
const status = computed(() => props.slot.authenticated ? 'SESSION ACTIVE' : ready.value ? 'PASSWORD DECODED' : attempt.value ? seconds.value ? 'BREAKING PASSWORD' : 'VERIFYING PASSWORD' : props.slot.password_result === 'failed' ? 'INSUFFICIENT CAPABILITY' : props.slot.password_result === 'cancelled' ? 'ATTEMPT CANCELLED' : 'AWAITING TARGET')
const tool = computed(() => props.slot.running_apps.find(app => app.id === 'cracker'))
const product = computed(() => props.slot.catalog.find(item => item.id === tool.value?.product_id))
async function run(action) { if (action === 'login' && (!ready.value || props.slot.authenticated)) return; await props.action(action, props.slot.id) }
onMounted(() => { timer = setInterval(() => { tick.value = Date.now() }, 95) })
onBeforeUnmount(() => clearInterval(timer))
</script>
<template>
  <section class="panel password-breaker" aria-label="Lockpick password breaker">
    <div class="panel-title"><span><KeyRound :size="16" /> {{ tool?.name || 'LOCKPICK' }}</span><span class="panel-meta">SERVER LOGIN</span></div>
    <form class="decoder-display" :class="{ working: attempt }" @submit.prevent="run('login')">
      <div class="decoder-meta"><span>{{ slot.connected ? `${slot.remote_target}${port ? ':' + port : ''}` : 'NO REMOTE CONNECTION' }}</span><span>CLASS {{ product?.power }} / {{ tool?.ram }} GB</span></div>
      <label :for="`${id}-login`">LOGIN</label><input :id="`${id}-login`" class="login-user" aria-label="Login username" value="admin" readonly autocomplete="off" />
      <label :for="`${id}-password`">PASSWORD</label><input :id="`${id}-password`" class="decoder-password" aria-label="Password" :value="password" placeholder="Awaiting password breaker" readonly autocomplete="off" spellcheck="false" />
      <div class="decoder-progress" role="progressbar" aria-label="Password breaking progress" :aria-valuenow="Math.floor(progress * 100)" aria-valuemin="0" aria-valuemax="100"><i :style="{ width: `${progress * 100}%` }"></i></div>
      <div class="decoder-status"><strong role="status">{{ status }}</strong><span v-if="attempt">{{ seconds ? `${seconds}s ESTIMATED` : 'WAITING FOR SERVER' }}</span></div>
      <p v-if="!slot.connected">Connect to a target from the local terminal to open its login.</p>
      <p v-else-if="ready && !slot.authenticated">Password decoded. Login as admin to enter the system and start the trace.</p>
      <p v-else-if="slot.authenticated">Logged in as admin. Remote filesystem mounted.</p>
      <p v-else-if="!port">Scan this server with Cartograph to identify its authentication service.</p>
      <p v-else-if="attempt">Decoding password. Trace remains inactive until Login.</p>
      <p v-else-if="slot.password_result === 'failed'">This Lockpick cannot defeat the target's security class.</p>
      <p v-else>Port {{ port }} / compute charge: {{ (product?.tier || 0) + 1 }} CPH.</p>
      <div class="decoder-actions"><button v-if="attempt" type="button" class="button secondary" :disabled="busy" @click="run('cancel')">Cancel password breaker</button><button v-else-if="!ready" type="button" class="button secondary" :disabled="busy || !slot.connected || !port" @click="run('start')">Break password</button><button type="submit" class="button primary" :disabled="busy || !ready || slot.authenticated">Login</button><button v-if="modal" type="button" class="button secondary" @click="emit('exit')">Exit</button></div>
    </form>
  </section>
</template>
