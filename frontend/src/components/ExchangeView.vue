<script setup>
import { computed, ref } from 'vue'
import { Cpu, HardDrive, MemoryStick, Radio, Code2, ArrowRight } from 'lucide-vue-next'
const props = defineProps({ slot: Object, busy: Boolean })
defineEmits(['trade'])
const category = ref('gateway'), tier = ref('all'), ownedOnly = ref(false)
const categories = [{ id: 'gateway', label: 'Gateways' }, { id: 'cpu', label: 'Processors' }, { id: 'memory', label: 'Memory' }, { id: 'storage', label: 'Storage' }, ...['mapper', 'cracker', 'decryptor', 'cleaner', 'monitor'].map(id => ({ id, label: { mapper: 'Network mappers', cracker: 'Authentication crackers', decryptor: 'Decryptors', cleaner: 'Log cleaners', monitor: 'Trace monitors' }[id] }))]
const owned = item => [...props.slot.owned_hardware, ...props.slot.installed_software].includes(item.id)
const fitted = item => Object.values(props.slot.equipment).some(current => current.id === item.id)
const running = item => props.slot.running_apps.some(app => app.product_id === item.id)
const products = computed(() => props.slot.catalog.filter(item => (item.kind || item.category) === category.value && (tier.value === 'all' || item.tier === Number(tier.value)) && (!ownedOnly.value || owned(item))))
const money = n => new Intl.NumberFormat('en-US').format(n)
const stat = item => item.kind === 'monitor' ? `CLASS ${item.power} / PASSIVE TERMINAL TELEMETRY` : item.category === 'cpu' ? `${item.speed}× COMPUTE` : item.category === 'gateway' ? `${item.hops} HOPS / ${item.stealth} STEALTH / ${item.bandwidth} MB/s` : item.category === 'memory' ? `${item.ram} GB RAM` : item.category === 'storage' ? `${item.capacity} MB STORAGE` : `CLASS ${item.power} / ${item.ram} GB / ${item.speed}× SPEED`
const icon = item => ({ cpu: Cpu, gateway: Radio, memory: MemoryStick, storage: HardDrive }[item.category] || Code2)
</script>

<template>
  <div class="eyebrow">SERVICES / HARDWARE & SOFTWARE EXCHANGE</div><div class="page-heading"><div><h1>Build your own edge<span>_</span></h1><p>Individual components. Specialized tools. Every purchase is a choice.</p></div><span class="badge">{{ money(slot.balance) }} CPH</span></div>
  <section class="panel fitted-rig"><div v-for="(item, kind) in slot.equipment" :key="kind"><span class="micro">{{ kind.toUpperCase() }}</span><strong>{{ item.name }}</strong><small>{{ stat(item) }}</small></div></section>
  <div class="shop-filters"><label>CATEGORY<select v-model="category" aria-label="CATEGORY"><option v-for="entry in categories" :key="entry.id" :value="entry.id">{{ entry.label }}</option></select></label><label>TIER<select v-model="tier" aria-label="TIER"><option value="all">All tiers</option><option v-for="n in 5" :key="n" :value="n">Tier {{ n }}</option></select></label><label class="checkbox-label"><input v-model="ownedOnly" type="checkbox" /> Owned only</label><span class="micro">{{ products.length }} OPTIONS / MARKET CLEARANCE T{{ Math.min(5, slot.rank + 2) }}</span></div>
  <p v-if="slot.connected" class="info-banner">Remote session active. The exchange cannot modify equipment until you disconnect.</p>
  <div class="product-grid"><article class="panel product-card" v-for="item in products" :key="item.id" :data-product="item.id"><div class="contract-card-top"><span class="micro">TIER 0{{ item.tier }}</span><span v-if="fitted(item)" class="badge">FITTED</span><span v-else-if="owned(item)" class="badge">OWNED</span><span v-else class="micro">{{ item.category === 'software' ? 'PERPETUAL LICENSE' : 'HARDWARE' }}</span></div><component :is="icon(item)" :size="34" :stroke-width="1" /><h2>{{ item.name }}</h2><span class="product-stat">{{ stat(item) }}</span><p>{{ item.description }}</p><div class="product-footer"><strong>{{ money(item.price) }} <small>CPH</small></strong><button v-if="!owned(item)" class="button secondary" :disabled="busy || slot.connected || slot.balance < item.price || item.tier > slot.rank + 2" @click="$emit('trade', 'buy', item.id)">{{ item.tier > slot.rank + 2 ? 'Clearance locked' : slot.balance < item.price ? 'Insufficient CPH' : 'Buy' }}<ArrowRight :size="13" /></button><button v-else-if="item.category !== 'software' && !fitted(item)" class="button secondary" :disabled="busy || slot.connected" @click="$emit('trade', 'equip', item.id)">Fit component</button></div><button v-if="owned(item) && !fitted(item) && !running(item)" class="text-link resale" :disabled="busy || slot.connected" @click="$emit('trade', 'sell', item.id)">Sell for {{ money(Math.floor(item.price / 2)) }} CPH</button></article></div>
  <p v-if="!products.length" class="empty-state">No owned products in this category.</p>
</template>
