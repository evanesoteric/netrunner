<script setup>
import { LockKeyhole, ShieldCheck } from 'lucide-vue-next'
defineProps({ slot: Object, busy: Boolean, showLaunch: { type: Boolean, default: true } })
defineEmits(['open-cracker'])
</script>

<template>
  <section v-if="slot.connected" class="server-login" aria-label="Remote server login">
    <component :is="slot.authenticated ? ShieldCheck : LockKeyhole" :size="22" />
    <div class="server-login-details"><strong>{{ slot.remote_target }}</strong><small>{{ slot.authenticated ? 'ACCESS GRANTED / FILESYSTEM MOUNTED' : 'SECURE LOGIN / AUTHENTICATION REQUIRED' }}</small></div>
    <div v-if="!slot.authenticated" class="server-credentials"><span>USER <b>admin</b></span><span>PASSWORD <b>••••••••••••</b></span></div>
    <span class="login-trace-state">{{ slot.stealth_session ? 'WRAITH / NO TRACE' : slot.authenticated ? 'TRACE ACTIVE' : 'TRACE INACTIVE' }}</span>
    <button v-if="showLaunch && !slot.authenticated" class="button secondary" :disabled="busy" @click="$emit('open-cracker')">Open password breaker</button>
  </section>
</template>
