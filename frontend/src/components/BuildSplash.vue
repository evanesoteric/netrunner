<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import ModalDialog from './ModalDialog.vue'
const props = defineProps({ product: Object, mode: { type: String, default: 'software' } })
const emit = defineEmits(['close'])
const progress = ref(0)
const fitting = computed(() => props.mode === 'hardware')
const stage = computed(() => fitting.value
  ? progress.value >= 100 ? 'FITTING COMPLETE' : progress.value >= 65 ? (props.product.category === 'gateway' ? 'Calibrating gateway links…' : 'Running hardware diagnostics…') : progress.value >= 25 ? 'Fitting component…' : 'Preparing installation…'
  : progress.value >= 100 ? 'BUILD COMPLETE' : progress.value >= 65 ? 'Linking terminal modules…' : progress.value >= 25 ? 'Building software…' : 'Preparing licensed source…')
let timer
onMounted(() => { const started = Date.now(); timer = setInterval(() => { const elapsed = Date.now() - started; progress.value = Math.min(100, Math.floor(elapsed / 15)); if (elapsed >= 2100) emit('close') }, 75) })
onBeforeUnmount(() => clearInterval(timer))
</script>
<template><ModalDialog :title="fitting ? 'Hardware fitting' : 'Software build'" @close="emit('close')"><div class="build-splash"><span class="micro">{{ fitting ? (product.category === 'gateway' ? 'GATEWAY INSTALLATION / LINK CALIBRATION' : 'COMPONENT INSTALLATION / DIAGNOSTICS') : 'LICENSE VERIFIED / LOCAL BUILD' }}</span><h3>{{ props.product.name }}</h3><pre v-if="fitting">verify compatibility ........ OK
reserve installation bay .... OK</pre><pre v-else>resolve dependencies ........ OK
verify license .............. OK</pre><div class="decoder-progress build-progress" role="progressbar" :aria-label="fitting ? 'Hardware fitting progress' : 'Software build progress'" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100"><i :style="{ width: `${progress}%` }"></i></div><strong role="status">{{ stage }}</strong><span>{{ progress }}%</span><p v-if="progress === 100">{{ fitting ? `${product.name} fitted to your rig.` : props.product.kind === 'cleaner' ? 'Logcleaner is available in the primary terminal.' : 'Software is ready in Applications.' }}</p><button class="text-link" @click="emit('close')">{{ progress === 100 ? 'Continue' : 'Skip animation' }}</button></div></ModalDialog></template>
