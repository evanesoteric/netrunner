<script setup>
import { ref, onMounted, onBeforeUnmount, useId } from 'vue'
const props = defineProps({ title: String, restoreFocus: { type: Boolean, default: true } })
const emit = defineEmits(['close'])
const panel = ref(null), id = useId()
let previous
function keys(event) {
  if (event.key === 'Escape') { event.preventDefault(); emit('close'); return }
  if (event.key !== 'Tab') return
  const selector = 'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], [tabindex="0"]'
  const items = [...panel.value.querySelectorAll(selector), ...document.querySelectorAll('[data-modal-control]:not(:disabled)')].filter(item => item.getClientRects().length && !item.closest('[inert]'))
  if (!items.length) { event.preventDefault(); panel.value.focus(); return }
  const index = items.indexOf(document.activeElement)
  const next = index < 0 ? (event.shiftKey ? items.length - 1 : 0) : (index + (event.shiftKey ? -1 : 1) + items.length) % items.length
  event.preventDefault(); items[next].focus()
}
onMounted(() => { previous = document.activeElement; panel.value.focus(); document.addEventListener('keydown', keys) })
onBeforeUnmount(() => { document.removeEventListener('keydown', keys); if (props.restoreFocus && previous?.isConnected) setTimeout(() => previous.focus({ preventScroll: true }), 0) })
</script>
<template>
  <Teleport to="body"><div class="modal-backdrop system-dialog-backdrop" @click.self="emit('close')"><section ref="panel" class="panel system-dialog" role="dialog" aria-modal="true" :aria-labelledby="id" tabindex="-1"><h2 :id="id" class="system-dialog-title">{{ props.title }}</h2><slot /></section></div></Teleport>
</template>
