<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { Mail, Send, Paperclip } from 'lucide-vue-next'
const props = defineProps({ slot: Object, busy: Boolean, api: Function, mutate: Function })
const emit = defineEmits(['bank'])
const mailbox = ref(null), folder = ref('inbox'), selected = ref(null), composing = ref(false), error = ref(''), result = ref(''), loading = ref(false), sending = ref(false)
const recipient = ref('dispatch@broker.internal'), subject = ref(''), body = ref(''), attachments = ref([]), reply = ref(null), intent = ref('message')
let version = 0, disposed = false, pending = null
function reference() {
  if (crypto.randomUUID) return crypto.randomUUID()
  const bytes = crypto.getRandomValues(new Uint8Array(16)); bytes[6] = bytes[6] & 15 | 64; bytes[8] = bytes[8] & 63 | 128
  const hex = [...bytes].map(n => n.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`
}
async function load(page = 1, fresh = false) {
  const marker = ++version; loading.value = true; error.value = ''
  const query = new URLSearchParams({ folder:folder.value, page:String(page) })
  if (!fresh && mailbox.value) query.set('snapshot', mailbox.value.snapshot)
  try {
    const data = await props.api(`slots/${props.slot.id}/mail/?${query}`)
    if (!disposed && marker === version) mailbox.value = data
  } catch (e) { if (!disposed && marker === version) error.value = e.message }
  finally { if (!disposed && marker === version) loading.value = false }
}
function switchFolder(next) { folder.value = next; selected.value = null; composing.value = false; load(1, true) }
async function open(message) {
  selected.value = message; composing.value = false; result.value = ''
  if (!message.read && message.folder === 'inbox') {
    const response = await props.mutate({ action:'read', message_id:message.id, identity:mailbox.value.identity }, props.slot.id)
    if (response) message.read = true
  }
}
function compose(message = null, mode = 'message') {
  reply.value = message?.id || null; intent.value = mode
  recipient.value = message?.sender || 'dispatch@broker.internal'
  subject.value = message ? `Re: ${message.subject}`.slice(0,180) : ''
  body.value = mode === 'deliver' ? 'Contract work complete. Please verify the attached evidence.' : mode === 'confirm' ? 'Settlement transferred through Cipher Bank. Please verify the receipt and close this case.' : ''
  attachments.value = []; composing.value = true; result.value = ''; pending = null
}
async function send() {
  if (props.busy || sending.value || !mailbox.value) return
  const payload = { action:'send', identity:mailbox.value.identity, recipient:recipient.value, subject:subject.value, body:body.value, attachments:attachments.value, reply_to:reply.value, intent:intent.value }
  const signature = JSON.stringify(payload)
  if (!pending || pending.signature !== signature) pending = { signature, request_id:reference() }
  sending.value = true
  try {
    const response = await props.mutate({ ...payload, request_id:pending.request_id }, props.slot.id)
    if (!disposed && response) { result.value = response.message; composing.value = false; selected.value = null; pending = null; await load(1, true) }
  } finally { sending.value = false }
}
watch(() => props.slot.mail_latest_id, () => { if (!sending.value && mailbox.value) load(mailbox.value.page) })
onMounted(() => load(1, true))
onUnmounted(() => { disposed = true; version++ })
</script>
<template>
  <div class="eyebrow">COMMUNICATIONS / ENCRYPTED MAIL</div>
  <div class="page-heading"><div><h1>Every message matters<span>_</span></h1><p>Briefings, evidence deliveries and agency correspondence. Fictional in-game mail only.</p></div><span class="badge">{{ slot.mail_unread || 0 }} UNREAD</span></div>
  <div class="mail-toolbar"><button class="button secondary" @click="switchFolder('inbox')" :disabled="busy">Inbox</button><button class="button secondary" @click="switchFolder('sent')" :disabled="busy">Sent</button><button class="button primary" @click="compose()" :disabled="busy"><Send :size="14" />Compose</button><button class="text-link" @click="load(1,true)" :disabled="loading">Refresh mail</button><span class="micro">{{ mailbox?.address }}</span></div>
  <p v-if="error" class="message error" role="alert">{{ error }}</p><p v-if="result" class="info-banner" role="status">{{ result }}</p>
  <p v-if="mailbox?.has_newer" class="info-banner">New mail available. Refresh mail to include it.</p>
  <div class="mail-layout">
    <section class="panel mailbox-list" aria-label="Mail messages"><div class="panel-title"><span><Mail :size="16" />{{ folder.toUpperCase() }}</span><span class="micro">{{ mailbox?.total || 0 }} MESSAGES</span></div>
      <button v-for="message in mailbox?.messages || []" :key="message.id" class="mail-row" :class="{ unread: !message.read && folder === 'inbox', selected: selected?.id === message.id }" :data-mail-kind="message.kind" @click="open(message)" :disabled="busy || sending"><strong>{{ message.subject }}</strong><span>{{ folder === 'inbox' ? message.sender : message.recipient }}</span><small>{{ new Date(message.created_at).toLocaleString() }}{{ message.attachments.length ? ' · ATTACHMENTS' : '' }}</small></button>
      <p v-if="mailbox && !mailbox.messages.length" class="empty-state">No messages in this folder.</p>
      <nav class="bank-pagination" aria-label="Mail pages"><button class="text-link" :disabled="loading || !mailbox || mailbox.page <= 1" @click="load(mailbox.page-1)">Previous</button><span class="micro">{{ mailbox?.page || 1 }} / {{ mailbox?.pages || 1 }}</span><button class="text-link" :disabled="loading || !mailbox || mailbox.page >= mailbox.pages" @click="load(mailbox.page+1)">Next</button></nav>
    </section>
    <section class="panel mail-reader" aria-label="Message reader">
      <form v-if="composing" class="mail-compose" @submit.prevent="send">
        <h2>{{ intent === 'deliver' ? 'Deliver contract evidence' : intent === 'confirm' ? 'Confirm agency settlement' : 'Compose message' }}</h2>
        <label>TO<select v-model="recipient" aria-label="Email recipient" :disabled="intent !== 'message' || busy"><option v-for="contact in mailbox?.contacts || []" :key="contact">{{ contact }}</option></select></label>
        <label>SUBJECT<input v-model="subject" aria-label="Email subject" maxlength="180" required :disabled="busy" /></label>
        <label>MESSAGE<textarea v-model="body" aria-label="Email body" maxlength="10000" required :disabled="busy"></textarea></label>
        <fieldset><legend><Paperclip :size="14" /> LOCAL FILE ATTACHMENTS (UP TO 10)</legend><label v-for="file in slot.local_files" :key="file.id" class="mail-file"><input type="checkbox" v-model="attachments" :value="file.id" :disabled="busy || (!attachments.includes(file.id) && attachments.length >= 10)" />{{ file.name }} · {{ file.size }} MB · {{ file.encrypted ? 'ENCRYPTED' : 'READABLE' }}</label><small v-if="!slot.local_files.length">Local drive is empty.</small></fieldset>
        <p v-if="intent === 'deliver'" class="micro">Recovery: attach the readable objective file. Deletion: receipts attach automatically. Clean-exit proof is required for both.</p>
        <div class="mail-toolbar"><button class="button primary" :disabled="busy || sending || !mailbox">Send message</button><button type="button" class="button secondary" @click="composing = false" :disabled="busy || sending">Cancel</button></div>
      </form>
      <template v-else-if="selected"><span class="micro">{{ selected.sender }} → {{ selected.recipient }}</span><h2>{{ selected.subject }}</h2><time class="micro">{{ new Date(selected.created_at).toLocaleString() }}</time><pre class="mail-body">{{ selected.body }}</pre>
        <div v-if="selected.attachments.length" class="mail-attachments"><span class="micro">ARCHIVED ATTACHMENTS</span><p v-for="(file,index) in selected.attachments" :key="index">{{ file.name }}<template v-if="file.size"> · {{ file.size }} MB</template><small v-if="file.receipts">{{ file.receipts.join(', ') }}</small></p></div>
        <div v-if="selected.folder === 'inbox'" class="mail-toolbar"><button class="button secondary" :disabled="busy" @click="compose(selected)">Reply</button><button v-if="selected.assignment_id && selected.sender === 'dispatch@broker.internal'" class="button primary" :disabled="busy" @click="compose(selected, 'deliver')">Submit contract by email</button><template v-if="selected.case_id && selected.sender === 'enforcement@sib.internal'"><button class="button secondary" @click="emit('bank')">Open Cipher Bank</button><button class="button primary" :disabled="busy" @click="compose(selected, 'confirm')">Confirm settlement by email</button></template></div>
      </template>
      <p v-else class="empty-state">Select a message or compose a new one. Accepted contract briefings arrive automatically.</p>
    </section>
  </div>
</template>
