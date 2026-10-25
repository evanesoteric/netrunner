<script setup>
import { computed, ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useMailDraft } from '../mailDraft'
import { requestReference } from '../requestReference'
import { Mail, Send, Paperclip } from 'lucide-vue-next'
const props = defineProps({ slot: Object, busy: Boolean, api: Function, mutate: Function })
const emit = defineEmits(['bank'])
const mailbox = ref(null), folder = ref('inbox'), selected = ref(null), composing = ref(false), error = ref(''), result = ref(''), loading = ref(false), sending = ref(false)
const recipient = ref('dispatch@broker.internal'), subject = ref(''), body = ref(''), attachments = ref([]), reply = ref(null), intent = ref('message')
let version = 0, disposed = false, pending = null
const reader = ref(null)
function revealReader() { nextTick(() => { if (!disposed && matchMedia('(max-width:1000px)').matches) reader.value?.scrollIntoView({ block:'start' }) }) }
const search = ref(''), category = ref('all'), unread = ref(false)
const filters = ref({ q:'', category:'all', unread:'0' })
const hasDraft = computed(() => !!(subject.value || body.value || reply.value || attachments.value.length))
const missingAttachments = computed(() => attachments.value.filter(id => !props.slot.local_files.some(file => file.id === id)))
const { draftAvailable, persistDraft } = useMailDraft(
  `netrunner.mailDraft:${props.slot.id}:${props.slot.created_at}`,
  () => ({ recipient:recipient.value, subject:subject.value, body:body.value, attachments:attachments.value, reply:reply.value, intent:intent.value, pending }),
  draft => {
    if (!draft || typeof draft.recipient !== 'string' || typeof draft.subject !== 'string' || draft.subject.length > 180 || typeof draft.body !== 'string' || draft.body.length > 10000 || !Array.isArray(draft.attachments) || draft.attachments.length > 10 || draft.attachments.some(id => typeof id !== 'string') || !['message','deliver','confirm'].includes(draft.intent) || !(draft.reply === null || Number.isInteger(draft.reply))) return false
    recipient.value = draft.recipient; subject.value = draft.subject; body.value = draft.body
    attachments.value = draft.attachments; reply.value = draft.reply; intent.value = draft.intent
    pending = draft.pending?.request_id && typeof draft.pending.signature === 'string' ? draft.pending : null
    composing.value = hasDraft.value
    return true
  }, () => hasDraft.value,
)
function clearDraft() {
  subject.value = ''; body.value = ''; attachments.value = []; reply.value = null; intent.value = 'message'; pending = null
  composing.value = false; persistDraft()
}
function filterMail() {
  filters.value = { q:search.value, category:category.value, unread:unread.value ? '1' : '0' }
  selected.value = null; load(1, true)
}
async function markMatchingRead() {
  if (props.busy || !mailbox.value) return
  const response = await props.mutate({ action:'read_all', identity:mailbox.value.identity, folder:'inbox', snapshot:mailbox.value.snapshot, ...filters.value }, props.slot.id)
  if (response) { result.value = response.message; await load(1, true) }
}
async function load(page = 1, fresh = false) {
  const marker = ++version; loading.value = true; error.value = ''
  const query = new URLSearchParams({ folder:folder.value, page:String(page), ...filters.value })
  if (!fresh && mailbox.value) query.set('snapshot', mailbox.value.snapshot)
  try {
    const data = await props.api(`slots/${props.slot.id}/mail/?${query}`)
    if (!disposed && marker === version) {
      mailbox.value = data
      const refreshed = data.messages.find(message => message.id === selected.value?.id)
      if (refreshed) selected.value = refreshed
    }
  } catch (e) {
    if (!disposed && marker === version) {
      if (page > 1 && e.status === 400 && e.message === 'Mail page does not exist.') return load(1, true)
      error.value = e.message
    }
  }
  finally { if (!disposed && marker === version) loading.value = false }
}
function switchFolder(next) { folder.value = next; selected.value = null; composing.value = false; load(1, true) }
async function open(message) {
  selected.value = message; composing.value = false; result.value = ''; revealReader()
  if (!message.read && message.folder === 'inbox') {
    const response = await props.mutate({ action:'read', message_id:message.id, identity:mailbox.value.identity }, props.slot.id)
    if (response) message.read = true
  }
}
function compose(message = null, mode = 'message') {
  if (hasDraft.value) { composing.value = true; revealReader(); result.value = 'Draft reopened. Send or discard it before starting a different message.'; return }
  reply.value = message?.id || null; intent.value = mode
  recipient.value = message?.sender || 'dispatch@broker.internal'
  subject.value = message ? `Re: ${message.subject}`.slice(0,180) : ''
  body.value = mode === 'deliver' ? 'Contract work complete. Please verify the attached evidence.' : mode === 'confirm' ? 'Settlement transferred through Cipher Bank. Please verify the receipt and close this case.' : ''
  attachments.value = []; composing.value = true; result.value = ''; pending = null; revealReader()
}
async function send() {
  if (props.busy || sending.value || !mailbox.value || missingAttachments.value.length) return
  const payload = { action:'send', identity:mailbox.value.identity, recipient:recipient.value, subject:subject.value, body:body.value, attachments:attachments.value, reply_to:reply.value, intent:intent.value }
  const signature = JSON.stringify(payload)
  if (!pending || pending.signature !== signature) pending = { signature, request_id:requestReference() }
  persistDraft()
  sending.value = true
  try {
    const response = await props.mutate({ ...payload, request_id:pending.request_id }, props.slot.id)
    if (!disposed && response) { result.value = response.message; clearDraft(); selected.value = null; await load(1, true) }
  } finally { sending.value = false }
}
watch(() => [props.slot.mail_latest_id, props.slot.mail_unread], () => { if (!sending.value && mailbox.value) load(mailbox.value.page).catch(() => {}) })
onMounted(() => load(1, true))
onUnmounted(() => { disposed = true; version++ })
</script>
<template>
  <div class="eyebrow">COMMUNICATIONS / ENCRYPTED MAIL</div>
  <div class="page-heading"><div><h1>Every message matters<span>_</span></h1><p>Briefings, evidence deliveries and agency correspondence. Fictional in-game mail only.</p></div><span class="badge">{{ slot.mail_unread || 0 }} UNREAD</span></div>
  <div class="mail-toolbar"><button class="button secondary" @click="switchFolder('inbox')" :disabled="busy">Inbox</button><button class="button secondary" @click="switchFolder('sent')" :disabled="busy">Sent</button><button class="button primary" @click="compose()" :disabled="busy"><Send :size="14" />Compose</button><button class="text-link" @click="load(1,true)" :disabled="loading">Refresh mail</button><span class="micro">{{ mailbox?.address }}</span></div>
  <form class="mail-search" @submit.prevent="filterMail"><label>SEARCH MAIL<input v-model="search" aria-label="Search mail" maxlength="120" placeholder="Subject, message or contact" /></label><label>CATEGORY<select v-model="category" aria-label="Mail category"><option value="all">All mail</option><option value="contracts">Contracts</option><option value="agency">Agency cases</option><option value="receipts">Bank receipts</option><option value="personal">Personal messages</option></select></label><label class="mail-unread-filter"><input type="checkbox" v-model="unread" aria-label="Unread mail only" />Unread only</label><button class="button secondary" :disabled="loading || busy">Search</button><button v-if="folder === 'inbox'" type="button" class="text-link" :disabled="busy || loading || !mailbox?.messages.some(row => !row.read)" @click="markMatchingRead">Mark matching inbox read</button></form>
  <p v-if="hasDraft" class="info-banner mail-draft-state">{{ draftAvailable ? 'Draft saved in this browser for this runner.' : 'Draft recovery unavailable. Keep this tab open until your message is sent.' }}<button v-if="!composing" class="text-link" @click="composing = true">Resume draft</button><button class="text-link danger-text" :disabled="sending || busy" @click="clearDraft">Discard draft</button></p>
  <p v-if="error" class="message error" role="alert">{{ error }}</p><p v-if="result" class="info-banner" role="status">{{ result }}</p>
  <p v-if="mailbox?.has_newer" class="info-banner">New mail available. Refresh mail to include it.</p>
  <div class="mail-layout">
    <section class="panel mailbox-list" aria-label="Mail messages"><div class="panel-title"><span><Mail :size="16" />{{ folder.toUpperCase() }}</span><span class="micro">{{ mailbox?.total || 0 }} MESSAGES</span></div>
      <button v-for="message in mailbox?.messages || []" :key="message.id" class="mail-row" :class="{ unread: !message.read && folder === 'inbox', selected: selected?.id === message.id }" :data-mail-kind="message.kind" @click="open(message)" :disabled="busy || sending"><strong>{{ message.subject }}</strong><span>{{ folder === 'inbox' ? message.sender : message.recipient }}</span><small>{{ new Date(message.created_at).toLocaleString() }}{{ message.attachments.length ? ' · ATTACHMENTS' : '' }}</small></button>
      <p v-if="mailbox && !mailbox.messages.length" class="empty-state">No messages in this folder.</p>
      <nav class="bank-pagination" aria-label="Mail pages"><button class="text-link" :disabled="loading || !mailbox || mailbox.page <= 1" @click="load(mailbox.page-1)">Previous</button><span class="micro">{{ mailbox?.page || 1 }} / {{ mailbox?.pages || 1 }}</span><button class="text-link" :disabled="loading || !mailbox || mailbox.page >= mailbox.pages" @click="load(mailbox.page+1)">Next</button></nav>
    </section>
    <section ref="reader" class="panel mail-reader" :class="{ 'mail-reader-active': composing || !!selected }" aria-label="Message reader">
      <form v-if="composing" class="mail-compose" @submit.prevent="send">
        <h2>{{ intent === 'deliver' ? 'Deliver contract evidence' : intent === 'confirm' ? 'Confirm agency settlement' : 'Compose message' }}</h2>
        <label>TO<select v-model="recipient" aria-label="Email recipient" :disabled="intent !== 'message' || busy"><option v-for="contact in mailbox?.contacts || []" :key="contact">{{ contact }}</option></select></label>
        <label>SUBJECT<input v-model="subject" aria-label="Email subject" maxlength="180" required :disabled="busy" /></label>
        <label>MESSAGE<textarea v-model="body" aria-label="Email body" maxlength="10000" required :disabled="busy"></textarea></label>
        <fieldset><legend><Paperclip :size="14" /> LOCAL FILE ATTACHMENTS (UP TO 10)</legend><label v-for="file in slot.local_files" :key="file.id" class="mail-file"><input type="checkbox" v-model="attachments" :value="file.id" :disabled="busy || (!attachments.includes(file.id) && attachments.length >= 10)" />{{ file.name }} · {{ file.size }} MB · {{ file.encrypted ? 'ENCRYPTED' : 'READABLE' }}</label><small v-if="!slot.local_files.length">Local drive is empty.</small></fieldset>
        <p v-if="missingAttachments.length" class="message error">{{ missingAttachments.length }} selected attachment(s) are no longer on your drive. <button type="button" class="text-link" @click="attachments = attachments.filter(id => !missingAttachments.includes(id))">Remove unavailable attachments</button></p>
        <p v-if="intent === 'deliver'" class="micro">Recovery: attach the readable objective file. Deletion: receipts attach automatically. Clean-exit proof is required for both.</p>
        <div class="mail-toolbar"><button class="button primary" :disabled="busy || sending || !mailbox || !!missingAttachments.length">Send message</button><button type="button" class="button secondary" @click="composing = false" :disabled="busy || sending">Close draft</button></div>
      </form>
      <template v-else-if="selected"><span class="micro">{{ selected.sender }} → {{ selected.recipient }}</span><h2>{{ selected.subject }}</h2><time class="micro">{{ new Date(selected.created_at).toLocaleString() }}</time><span v-if="selected.assignment_status || selected.case_status" class="badge mail-status">{{ (selected.assignment_status || selected.case_status).toUpperCase() }}</span><pre class="mail-body">{{ selected.body }}</pre>
        <div v-if="selected.attachments.length" class="mail-attachments"><span class="micro">ARCHIVED ATTACHMENTS</span><p v-for="(file,index) in selected.attachments" :key="index">{{ file.name }}<template v-if="file.size"> · {{ file.size }} MB</template><small v-if="file.receipts">{{ file.receipts.join(', ') }}</small></p></div>
        <div v-if="selected.folder === 'inbox'" class="mail-toolbar"><button v-if="mailbox?.contacts.includes(selected.sender)" class="button secondary" :disabled="busy" @click="compose(selected)">Reply</button><button v-if="selected.assignment_id && selected.assignment_status === 'accepted' && selected.sender === 'dispatch@broker.internal'" class="button primary" :disabled="busy" @click="compose(selected, 'deliver')">Submit contract by email</button><template v-if="selected.case_id && selected.case_status !== 'closed' && selected.sender === 'enforcement@sib.internal'"><button class="button secondary" @click="emit('bank')">Open Cipher Bank</button><button class="button primary" :disabled="busy" @click="compose(selected, 'confirm')">Confirm settlement by email</button></template></div>
      </template>
      <p v-else class="empty-state">Select a message or compose a new one. Accepted contract briefings arrive automatically.</p>
    </section>
  </div>
</template>
