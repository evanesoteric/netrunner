<script setup>
import { Terminal, Network, BriefcaseBusiness, Cpu, Landmark, Activity, ShieldCheck, KeyRound, LockKeyhole, Eraser, ScanLine, Play, X } from 'lucide-vue-next'
const props = defineProps({ slot: Object, busy: Boolean })
defineEmits(['launch', 'close'])
const icons = { terminal: Terminal, atlas: Network, broker: BriefcaseBusiness, market: Cpu, bank: Landmark, mapper: ScanLine, cracker: KeyRound, decryptor: ShieldCheck, cleaner: Eraser, monitor: Activity, rootkit: ShieldCheck, ransomware: LockKeyhole }
const software = () => props.slot.catalog.filter(item => props.slot.installed_software.includes(item.id))
const running = id => props.slot.running_apps.some(app => app.product_id === id)
</script>

<template>
  <div class="eyebrow">DESKTOP / APPLICATION LAUNCHER</div>
  <div class="page-heading"><div><h1>Tools of your trade<span>_</span></h1><p>Separate processes. Separate consoles. Your memory is the limit.</p></div><span class="badge">RAM {{ slot.ram_used }} / {{ slot.equipment.memory.ram }} GB</span></div>
  <div v-if="slot.running_apps.length" class="process-strip"><span class="micro">RUNNING</span><div v-for="app in slot.running_apps" :key="app.id"><button class="process-name" @click="$emit('launch', app.product_id)">{{ app.name }}</button><button :aria-label="`Close ${app.name}`" :disabled="busy" @click="$emit('close', app.id)"><X :size="13" /></button></div></div>
  <h2 class="section-heading">SYSTEM APPLICATIONS <span>BUILT IN</span></h2>
  <div class="launcher-grid"><article class="panel launcher-card" v-for="app in slot.builtins" :key="app.id"><component :is="icons[app.id]" :size="27" /><span class="micro">{{ app.ram ? `${app.ram} GB RAM` : 'SERVICE TERMINAL' }}</span><h2>{{ app.name }}</h2><p>{{ app.description }}</p><button class="button secondary wide" :disabled="busy" @click="$emit('launch', app.id)">{{ running(app.id) ? 'Open' : 'Launch' }} {{ app.name }}<Play :size="13" /></button></article></div>
  <h2 class="section-heading">INSTALLED SOFTWARE <span>{{ slot.installed_software.length }} LICENSES</span></h2>
  <div class="launcher-grid"><article class="panel launcher-card" v-for="item in software()" :key="item.id"><component :is="icons[item.kind]" :size="27" /><span class="micro">{{ item.grade === 'epic' ? 'EPIC / ' : '' }}{{ item.ram }} GB RAM / CLASS {{ item.power }}</span><h2>{{ item.name }}</h2><p>{{ item.label }}. {{ item.description }}</p><button class="button secondary wide" :disabled="busy" @click="$emit('launch', item.id)">{{ running(item.id) ? 'Open' : 'Launch' }} {{ item.name }}<Play :size="13" /></button></article></div>
</template>
