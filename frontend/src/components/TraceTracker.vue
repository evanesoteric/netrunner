<script setup>
import { computed } from 'vue'
import { Radio } from 'lucide-vue-next'
const props = defineProps({ slot: Object, remaining: Number })
const danger = computed(() => props.slot.trace_active && props.remaining != null && props.remaining <= 30)
const percentage = computed(() => props.remaining == null || !props.slot.trace_budget ? 0 : Math.min(100, Math.max(0, 100 * (1 - props.remaining / props.slot.trace_budget))))
</script>
<template><aside v-if="slot.connected" class="remote-status trace-tracker" :class="{ danger, unresolved: slot.trace_active && remaining == null }" aria-label="Trace tracker"><Radio :size="22" /><div class="trace-tracker-info"><span>TRACE TRACKER / {{ slot.remote_target }}</span><strong>{{ slot.stealth_session ? 'WRAITH / LOGGING SUPPRESSED / NO TRACE' : !slot.authenticated ? 'LOGIN REQUIRED / TRACE INACTIVE' : remaining == null ? (slot.running_apps.some(app => app.id === 'monitor') ? 'TRACE ENCRYPTED' : 'TRACE MONITOR OFFLINE') : `TRACE ${remaining}s` }}</strong><small v-if="slot.trace_active && remaining == null">Run a capable Tripwire monitor to reveal the countdown.</small></div><div class="trace-meter" aria-label="Trace progress"><i :style="{ width: `${percentage}%` }"></i></div></aside></template>
