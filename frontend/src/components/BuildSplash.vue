<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import ModalDialog from './ModalDialog.vue'
const props = defineProps({ product: Object })
const emit = defineEmits(['close'])
const progress = ref(0)
const stage = computed(() => progress.value >= 100 ? 'BUILD COMPLETE' : progress.value >= 65 ? 'Linking terminal modules…' : progress.value >= 25 ? 'Building software…' : 'Preparing licensed source…')
let timer
onMounted(() => { const started = Date.now(); timer = setInterval(() => { const elapsed = Date.now() - started; progress.value = Math.min(100, Math.floor(elapsed / 15)); if (elapsed >= 2100) emit('close') }, 75) })
onBeforeUnmount(() => clearInterval(timer))
</script>
<template><ModalDialog title="Software build" @close="emit('close')"><div class="build-splash"><span class="micro">LICENSE VERIFIED / LOCAL BUILD</span><h3>{{ props.product.name }}</h3><pre>resolve dependencies ........ OK
verify license .............. OK</pre><div class="decoder-progress build-progress" role="progressbar" aria-label="Software build progress" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100"><i :style="{ width: `${progress}%` }"></i></div><strong role="status">{{ stage }}</strong><span>{{ progress }}%</span><p v-if="progress === 100">{{ props.product.kind === 'cleaner' ? 'Logcleaner is available in the primary terminal.' : 'Software is ready in Applications.' }}</p><button class="text-link" @click="emit('close')">{{ progress === 100 ? 'Continue' : 'Skip animation' }}</button></div></ModalDialog></template>
