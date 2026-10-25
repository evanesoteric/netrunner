<script setup>
import { computed } from 'vue'
import { useTraceAudio } from '../traceAudio'
import { Radio, Volume2, VolumeX } from 'lucide-vue-next'
const props = defineProps({ slot: Object, remaining: Number, elapsed: Number })
const { enabled, supported, toggle } = useTraceAudio(props)
const danger = computed(() => props.slot.trace_active && props.remaining != null && props.remaining <= 30)
const percentage = computed(() => props.remaining == null || !props.slot.trace_budget ? 0 : Math.min(100, Math.max(0, 100 * (1 - props.remaining / props.slot.trace_budget))))
</script>
<template><aside v-if="slot.connected" class="remote-status trace-tracker" :class="{ danger, unresolved: slot.trace_active && remaining == null }" aria-label="Trace tracker"><Radio :size="22" /><div class="trace-tracker-info"><span>TRACE TRACKER / {{ slot.remote_name }} / {{ slot.remote_ip || slot.remote_target }}</span><strong>{{ slot.stealth_session ? 'WRAITH / LOGGING SUPPRESSED / NO TRACE' : !slot.authenticated ? 'LOGIN REQUIRED / TRACE INACTIVE' : remaining == null ? `TRACE ACTIVE / ${elapsed}s ELAPSED` : `TRACE ${remaining}s` }}</strong><small v-if="slot.trace_active && remaining == null">{{ slot.trace_monitor_product ? 'TRACE ENCRYPTED' : 'TRACE MONITOR OFFLINE' }} — select a capable Tripwire license to reveal time remaining.</small></div><div class="trace-meter" aria-label="Trace progress"><i :style="{ width: `${percentage}%` }"></i></div><button data-modal-control class="trace-audio-toggle" :disabled="!supported" :aria-label="enabled ? 'Mute trace audio' : 'Enable trace audio'" :aria-pressed="enabled" :title="!supported ? 'Audio unavailable in this browser' : enabled ? 'Mute trace audio' : 'Enable trace audio'" @click="toggle"><component :is="enabled ? Volume2 : VolumeX" :size="18" /></button></aside></template>
