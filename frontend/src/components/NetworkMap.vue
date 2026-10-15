<script setup>
import { computed, ref, watch } from 'vue'
import { Network, ArrowUp, ArrowDown, X, Plus, Minus, RotateCcw } from 'lucide-vue-next'
const props = defineProps({ slot: Object, busy: Boolean })
const emit = defineEmits(['save'])
const route = ref([...props.slot.proxy_route]), zoom = ref(1), pan = ref({ x: 0, y: 0 }), drag = ref(null)
watch(() => `${props.slot.id}:${props.slot.proxy_route.join(',')}`, () => { route.value = [...props.slot.proxy_route] })
const nodes = computed(() => route.value.map(id => props.slot.relays.find(node => node.id === id)))
const points = computed(() => [props.slot.home_node, ...nodes.value, ...(props.slot.active_contract ? [props.slot.active_contract] : [])])
const polyline = computed(() => points.value.map(node => `${node.x},${node.y}`).join(' '))
const estimate = computed(() => ({ fee: 8 + nodes.value.reduce((sum, n) => sum + n.fee, 0), delay: nodes.value.reduce((sum, n) => sum + n.delay, 0), latency: nodes.value.reduce((sum, n) => sum + n.latency, 0) + Math.ceil(points.value.slice(1).reduce((sum, n, i) => sum + Math.hypot(n.x - points.value[i].x, n.y - points.value[i].y), 0) / 30) }))
const changed = computed(() => route.value.join(',') !== props.slot.proxy_route.join(','))
function toggle(node) {
  if (props.slot.connected) return
  const index = route.value.indexOf(node.id)
  if (index >= 0) route.value.splice(index, 1)
  else if (node.rank <= props.slot.rank && route.value.length < props.slot.equipment.gateway.hops) route.value.push(node.id)
}
function move(index, delta) { const copy = [...route.value]; [copy[index], copy[index + delta]] = [copy[index + delta], copy[index]]; route.value = copy }
function resetView() { zoom.value = 1; pan.value = { x: 0, y: 0 } }
function startDrag(event) {
  if (event.target.closest('[role="button"]')) return
  const bounds = event.currentTarget.getBoundingClientRect()
  drag.value = { x: event.clientX, y: event.clientY, origin: { ...pan.value }, factor: 1000 / bounds.width }
  event.currentTarget.setPointerCapture(event.pointerId)
}
function moveDrag(event) { if (drag.value) pan.value = { x: drag.value.origin.x + (event.clientX - drag.value.x) * drag.value.factor, y: drag.value.origin.y + (event.clientY - drag.value.y) * drag.value.factor } }
</script>

<template>
  <div class="eyebrow">ATLAS / GLOBAL ROUTING DESK</div><div class="page-heading"><div><h1>Take the long way around<span>_</span></h1><p>Choose relays in order. Your gateway is the origin; the reserved target is the destination.</p></div><span class="badge">{{ route.length }} / {{ slot.equipment.gateway.hops }} HOPS</span></div>
  <div class="atlas-layout"><section class="panel atlas-panel"><div class="panel-title"><span><Network :size="16" /> WORLD NETWORK</span><span class="panel-meta">{{ slot.connected ? 'ROUTE LOCKED / CONNECTED' : changed ? 'UNCOMMITTED ROUTE' : 'ROUTE COMMITTED' }}</span></div>
      <div class="atlas-map"><svg viewBox="0 0 1000 470" aria-label="Global proxy routing map" @pointerdown="startDrag" @pointermove="moveDrag" @pointerup="drag = null" @pointercancel="drag = null">
        <defs><pattern id="atlas-grid" width="50" height="47" patternUnits="userSpaceOnUse"><path d="M 50 0 L 0 0 0 47" fill="none" stroke="#1b3428" stroke-width=".6" /></pattern><radialGradient id="atlas-glow"><stop offset="0" stop-color="#163d29" /><stop offset="1" stop-color="#08110d" /></radialGradient></defs>
        <rect width="1000" height="470" fill="url(#atlas-glow)" /><rect width="1000" height="470" fill="url(#atlas-grid)" />
        <g :transform="`translate(${pan.x} ${pan.y}) translate(500 235) scale(${zoom}) translate(-500 -235)`">
          <g class="continents"><path d="M95 97L140 73 191 81 210 66 265 83 302 111 310 142 280 170 267 196 234 210 228 237 204 232 195 205 171 191 158 158 126 142 107 120Z" /><path d="M229 235L255 244 271 267 309 271 352 304 349 329 324 352 313 385 294 420 276 404 274 368 257 330 248 293 230 268Z" /><path d="M344 70L395 59 414 78 395 105 373 115 350 101Z" /><path d="M458 126L479 109 500 117 520 104 543 119 563 133 553 158 530 163 513 183 493 179 482 157 459 153Z" /><path d="M469 194L506 180 541 190 568 221 577 254 550 292 536 329 516 355 498 328 492 290 474 266 456 234Z" /><path d="M545 111L578 85 631 83 667 96 711 84 770 109 811 105 863 129 887 153 873 178 845 193 818 183 804 211 775 223 756 200 727 216 706 242 683 248 672 222 650 203 617 186 586 178 563 153Z" /><path d="M704 248L726 248 743 267 750 289 771 305 762 316 742 300 726 276Z" /><path d="M792 335L826 321 863 331 895 359 888 390 852 402 813 383 789 360Z" /><path d="M917 399L931 390 928 415 915 429 907 420Z" /><path d="M853 189L864 181 871 200 859 217 850 211Z" /><path d="M576 314L582 329 575 349 566 345Z" /></g>
          <polyline v-if="points.length > 1" :points="polyline" class="proxy-path" />
          <g class="map-home" :transform="`translate(${slot.home_node.x} ${slot.home_node.y})`"><rect x="-6" y="-6" width="12" height="12" /><text x="-35" y="-17">YOUR GATEWAY</text></g>
          <g v-for="node in slot.relays" :key="node.id" class="relay-node" :class="{ selected: route.includes(node.id), locked: node.rank > slot.rank }" :transform="`translate(${node.x} ${node.y})`" role="button" tabindex="0" :aria-label="`Route through ${node.name}`" :aria-pressed="route.includes(node.id)" :aria-disabled="slot.connected || (node.rank > slot.rank && !route.includes(node.id)) || (!route.includes(node.id) && route.length >= slot.equipment.gateway.hops)" @click="toggle(node)" @keydown.enter.prevent="toggle(node)" @keydown.space.prevent="toggle(node)">
            <title>{{ node.name }} / {{ node.operator }} / +{{ node.delay }}s / {{ node.fee }} CPH</title><circle class="relay-hit" r="14" /><circle class="relay-ring" r="8" /><circle r="3" /><text x="12" :y="node.id === 'berlin' ? 18 : -10">{{ node.name.toUpperCase() }}</text><text v-if="route.includes(node.id)" x="0" y="-14" class="hop-number">{{ route.indexOf(node.id) + 1 }}</text>
          </g>
          <g v-if="slot.active_contract" class="map-target" :transform="`translate(${slot.active_contract.x} ${slot.active_contract.y})`"><circle r="11" /><path d="M-16 0H16M0-16V16" /><text x="16" y="-16">{{ slot.active_contract.target.toUpperCase() }}</text></g>
        </g>
      </svg><div class="map-controls"><button aria-label="Zoom in" @click="zoom = Math.min(2.5, zoom + .25)"><Plus :size="15" /></button><button aria-label="Zoom out" @click="zoom = Math.max(.75, zoom - .25)"><Minus :size="15" /></button><button aria-label="Reset map view" @click="resetView"><RotateCcw :size="14" /></button></div><div class="map-legend"><span><i></i> RELAY</span><span><i class="selected-dot"></i> SELECTED HOP</span><span><i class="target-dot"></i> TARGET</span></div></div>
      <div class="panel-bottom">Drag to pan. Select a relay to append or remove it. Longer routes buy time but cost more CPH and add latency.</div>
    </section>
    <section class="panel route-panel"><div class="panel-title"><span>PROXY CHAIN</span><span class="panel-meta">ORDER MATTERS</span></div><div class="route-origin">01 / YOUR GATEWAY<small>{{ slot.equipment.gateway.name }}</small></div><ol class="route-order"><li v-for="(node, index) in nodes" :key="node.id"><div><strong>{{ node.name }}</strong><small>+{{ node.delay }}s / {{ node.fee }} CPH</small></div><button :disabled="slot.connected || index === 0" :aria-label="`Move ${node.name} earlier`" @click="move(index, -1)"><ArrowUp :size="13" /></button><button :disabled="slot.connected || index === nodes.length - 1" :aria-label="`Move ${node.name} later`" @click="move(index, 1)"><ArrowDown :size="13" /></button><button :disabled="slot.connected" :aria-label="`Remove ${node.name}`" @click="toggle(node)"><X :size="13" /></button></li></ol><p v-if="!nodes.length" class="empty-route">Direct connection. No proxies between you and the target.</p><div class="route-destination">DESTINATION<small>{{ slot.active_contract?.target || 'No contract reserved' }}</small></div><div class="route-summary"><span>Connection lease<strong>{{ estimate.fee }} CPH</strong></span><span>Added trace delay<strong>+{{ estimate.delay }}s</strong></span><span>Route latency<strong>{{ estimate.latency }} units</strong></span></div><button class="button primary wide" :disabled="busy || slot.connected || !changed" @click="emit('save', [...route])">Commit route <Network :size="15" /></button></section>
  </div>
  <h2 class="section-heading">RELAY DIRECTORY <span>FICTIONAL GLOBAL NETWORK</span></h2><div class="relay-directory"><button v-for="node in slot.relays" :key="node.id" :aria-label="`${route.includes(node.id) ? 'Remove relay' : 'Add relay'} ${node.name}`" :class="['panel', { selected: route.includes(node.id) }]" :disabled="slot.connected || (node.rank > slot.rank && !route.includes(node.id)) || (!route.includes(node.id) && route.length >= slot.equipment.gateway.hops)" @click="toggle(node)"><span>{{ node.name }}<small>{{ node.operator }}</small></span><strong>{{ node.rank > slot.rank && !route.includes(node.id) ? 'CLEARANCE LOCKED' : route.includes(node.id) ? `HOP ${route.indexOf(node.id) + 1}` : `+${node.delay}s / ${node.fee} CPH` }}</strong></button></div>
</template>
