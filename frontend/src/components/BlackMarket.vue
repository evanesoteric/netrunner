<script setup>
import { ShieldCheck, LockKeyhole } from 'lucide-vue-next'
defineProps({ slot: Object, busy: Boolean })
defineEmits(['trade'])
</script>

<template>
  <div class="eyebrow">HIDDEN SERVICE / NULL EXCHANGE</div>
  <div class="page-heading"><div><h1>Some doors stay open<span>_</span></h1><p>Epic licenses. Persistent access. Payment in Cipher.</p></div><span class="badge">INVITATION VERIFIED</span></div>
  <div class="product-grid epic-market"><article v-for="item in slot.black_market_catalog" :key="item.id" class="panel product-card epic-card" :data-product="item.id">
    <div class="contract-card-top"><span class="micro">EPIC / PERPETUAL LICENSE</span><span v-if="slot.installed_software.includes(item.id)" class="badge">OWNED</span></div>
    <component :is="item.kind === 'rootkit' ? ShieldCheck : LockKeyhole" :size="32" />
    <h2>{{ item.name }}</h2><span class="product-stat">{{ item.ram }} GB RAM / CLASS {{ item.power }}</span><p>{{ item.description }}</p>
    <code>{{ item.usage }}</code>
    <div class="product-footer"><strong>{{ item.price.toLocaleString() }} <small>CPH</small></strong><button class="button secondary" :disabled="busy || slot.connected || slot.installed_software.includes(item.id) || slot.balance < item.price" @click="$emit('trade', 'buy', item.id)">{{ slot.installed_software.includes(item.id) ? 'Owned' : slot.balance < item.price ? 'Insufficient CPH' : 'Buy epic license' }}</button></div>
  </article></div>
  <p class="info-banner">Launch purchased tools in Applications. Initial intrusion and installation can leave logs. Future Wraith jumps suppress logging and bypass proxy leases.</p>
</template>
