<script setup>
defineProps({ slot: Object, busy: Boolean })
defineEmits(['connect'])
</script>
<template>
            <div class="eyebrow">WRAITH / PERSISTENT ACCESS</div><div class="page-heading"><div><h1>Backdoored Servers<span>_</span></h1><p>Direct connections. No proxy lease. Remote access logging suppressed.</p></div><span class="badge">{{ slot.backdoors.length }} PERSISTENT LINKS</span></div>
            <div v-if="!slot.backdoors.length" class="empty-state">No backdoors installed. Mount a server filesystem, launch Wraith Rootkit, and run install. Clean the initial access logs before leaving.</div>
            <div class="server-directory-grid"><article v-for="server in slot.backdoors" :key="server.target" class="panel directory-card"><span class="micro">WRAITH / ROOT ACCESS</span><h3>{{ server.name || server.title }}</h3><code>{{ server.target }}</code><p>Persistent link / no proxy chain required</p><button class="button primary" :disabled="busy || slot.connected || (slot.active_contract && slot.active_contract.target !== server.target)" @click="$emit('connect', server.target)">Connect to {{ server.target }}</button></article></div>
</template>
