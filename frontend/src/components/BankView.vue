<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { Landmark, Activity, ArrowUpRight } from 'lucide-vue-next'
import TerminalConsole from './TerminalConsole.vue'
defineEmits(['mail'])
const props = defineProps({ slot: Object, busy: Boolean, api: Function, send: Function, transact: Function })
const info = ref(null), book = ref(null), loading = ref(false), submitting = ref(false), error = ref(''), message = ref('')
const principal = ref(500), repayment = ref(100), transfer = ref(100), direction = ref('deposit')
const money = value => new Intl.NumberFormat('en-US').format(value ?? 0)
const fee = computed(() => Math.floor((Number(principal.value || 0) * 5 + 99) / 100))
const disabled = computed(() => props.busy || submitting.value || !info.value)
const available = computed(() => info.value?.current_balance ?? props.slot.balance)
let version = 0, disposed = false, pending = null
async function load(page = 1, fresh = false) {
  const marker = ++version
  loading.value = true; error.value = ''
  const query = new URLSearchParams({ page:String(page) })
  if (!fresh && book.value) { query.set('snapshot', book.value.snapshot); query.set('identity', info.value.identity) }
  try {
    const result = await props.api(`slots/${props.slot.id}/bank/?${query}`)
    if (!disposed && marker === version) { info.value = result.bank; book.value = result.history }
  } catch (failure) { if (!disposed && marker === version) error.value = failure.message }
  finally { if (!disposed && marker === version) loading.value = false }
}
function transactionReference() {
  if (crypto.randomUUID) return crypto.randomUUID()
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128
  const hex = [...bytes].map(byte => byte.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`
}
async function action(kind, raw, settlement = null) {
  if (disabled.value) return
  const amount = Number(raw), signature = `${info.value.identity}:${kind}:${amount}:${settlement?.reference || ''}`
  if (!pending || pending.signature !== signature) pending = { signature, request_id:transactionReference() }
  submitting.value = true; version++; loading.value = false; message.value = ''; error.value = ''
  try {
    const result = await props.transact({ action:kind, amount, identity:info.value.identity, request_id:pending.request_id, ...(settlement ? { case_reference:settlement.reference, recipient:settlement.account } : {}) }, props.slot.id)
    if (!disposed && result) { info.value = result.bank; book.value = result.history; message.value = result.message; pending = null }
  } finally { submitting.value = false }
}
const favorable = entry => entry.account === 'loan' ? entry.amount < 0 : entry.amount > 0
watch(() => [props.slot.balance, props.slot.reserve_balance, props.slot.loan_balance], ([current, reserve, loan]) => {
  if (info.value) info.value = { ...info.value, current_balance:current, reserve_balance:reserve, loan_balance:loan, net_worth:current + reserve - loan - (info.value.enforcement_due || 0) }
})
watch(() => props.slot.enforcement_cases, notices => {
  if (!info.value || !notices) return
  const due = notices.filter(row => row.status === 'unpaid').reduce((sum,row) => sum + row.amount, 0)
  info.value = { ...info.value, enforcement_cases:notices, enforcement_due:due, net_worth:props.slot.balance + props.slot.reserve_balance - props.slot.loan_balance - due }
})
watch(() => props.slot.ledger_latest_id, (next, old) => { if (next !== old && info.value && !submitting.value) load(book.value?.page || 1) })
onMounted(() => load(1, true))
onUnmounted(() => { disposed = true; version++ })
</script>

<template>
  <div class="eyebrow">SERVICES / CIPHER BANK TERMINAL</div><div class="page-heading"><div><h1>Your money. Off the grid<span>_</span></h1><p>Current funds, reserves, credit and a complete transaction record.</p></div><span class="badge">PRIVATE LEDGER</span></div>
  <section class="bank-hero"><div><span class="micro">CIPHER // CURRENT ACCOUNT</span><h2>{{ money(available) }} <span>CPH</span></h2><p>Available for purchases, routes and compute</p></div><div class="bank-account"><Landmark :size="32" :stroke-width="1" /><span>ACCOUNT HOLDER</span><strong>{{ slot.alias }}</strong><small>NR-{{ String(slot.id).padStart(8,'0') }} / SLOT 0{{ slot.position }}</small></div></section>
  <div v-if="error" class="message error" role="alert">{{ error }}</div>
  <p v-if="message" class="info-banner" role="status">{{ message }}</p>
  <div class="bank-summary"><article class="panel"><span class="micro">RESERVE ACCOUNT</span><strong>{{ money(info?.reserve_balance ?? slot.reserve_balance) }} CPH</strong><small>Separate from automatic spending. Transfer back when needed.</small></article><article class="panel"><span class="micro">OUTSTANDING LOAN</span><strong>{{ money(info?.loan_balance ?? slot.loan_balance) }} CPH</strong><small>Includes the one-time fee. No compounding or automatic collection.</small></article><article class="panel"><span class="micro">NET WORTH</span><strong>{{ money(info?.net_worth ?? (slot.balance + (slot.reserve_balance || 0) - (slot.loan_balance || 0))) }} CPH</strong><small>Current + reserve − loan − unpaid settlements</small></article></div>
  <div class="bank-controls">
    <section class="panel bank-form"><h2>Move your funds</h2><p>Manual transfers within this save. Agency settlements require a manual transfer from current funds. Abort penalties can collect from current and reserve.</p><form @submit.prevent="action(direction, transfer)"><label>TRANSFER DIRECTION<select v-model="direction" aria-label="Transfer direction" :disabled="disabled"><option value="deposit">Current → Reserve</option><option value="withdraw">Reserve → Current</option></select></label><label>TRANSFER AMOUNT<input v-model="transfer" type="number" min="1" step="1" required :disabled="disabled" /></label><button class="button secondary" :disabled="disabled">Transfer CPH</button></form></section>
    <section class="panel bank-form"><h2>Runner credit</h2><p>One active loan. Limit {{ info ? money(info.loan_limit) : '…' }} CPH at your rank. Minimum 100 CPH.</p><form @submit.prevent="action('loan', principal)"><label>LOAN AMOUNT<input v-model="principal" type="number" min="100" :max="info?.loan_limit" step="1" required :disabled="disabled || !!info?.loan_balance" /></label><div class="bank-quote">Fixed fee (5%): <strong>{{ money(fee) }} CPH</strong><br>Total repayment: <strong>{{ money(Number(principal || 0) + fee) }} CPH</strong></div><button class="button secondary" :disabled="disabled || !!info?.loan_balance">Borrow CPH</button></form><small>No due date or offline charges. Repay before borrowing again.</small></section>
    <section class="panel bank-form"><h2>Repay a loan</h2><p v-if="info?.loan_balance">Original principal {{ money(info.loan_principal) }} CPH + fixed fee {{ money(info.loan_fee) }} CPH.</p><p v-else>No outstanding loan.</p><form @submit.prevent="action('repay', repayment)"><label>REPAYMENT AMOUNT<input v-model="repayment" type="number" min="1" :max="Math.min(available, info?.loan_balance || 0)" step="1" required :disabled="disabled || !info?.loan_balance" /></label><button class="text-link" type="button" :disabled="disabled || !info?.loan_balance" @click="repayment = info.loan_balance">Fill payoff amount</button><button class="button secondary" :disabled="disabled || !info?.loan_balance">Repay CPH</button></form><small>Paid from current funds. Partial repayments are welcome.</small></section>
  </div>
  <section v-if="info?.enforcement_cases?.length" class="panel bank-form agency-settlements"><h2>Agency settlement transfers</h2><p>Pay Meridian Legal Services using the case reference, then confirm by replying to the agency email. No automatic collection or escalating fees.</p><article v-for="caseFile in info.enforcement_cases" :key="caseFile.id" class="settlement-form"><strong>{{ caseFile.target }} · {{ caseFile.status.toUpperCase() }}</strong><form v-if="caseFile.status === 'unpaid'" @submit.prevent="action('settle', caseFile.amount, caseFile)"><label>BENEFICIARY ACCOUNT<input :value="caseFile.account" readonly /></label><label>CASE REFERENCE<input :value="caseFile.reference" readonly /></label><label>SETTLEMENT AMOUNT<input :value="caseFile.amount + ' CPH'" readonly /></label><button class="button secondary" :disabled="disabled">Transfer {{ money(caseFile.amount) }} CPH to Meridian</button></form><p v-else>Bank transfer received. Email confirmation required to close this case.</p></article><button class="text-link" @click="$emit('mail')">Open Email to confirm settlement</button></section>
  <TerminalConsole :slot="slot" application="bank" :busy="busy" :send="send" />
  <section class="panel ledger bank-ledger"><div class="panel-title"><span><Activity :size="16" /> TRANSACTION HISTORY</span><span class="panel-meta">{{ book?.total || 0 }} TRANSACTIONS · ALL ACCOUNTS</span></div>
    <div class="bank-history-controls"><button class="button secondary" :disabled="loading || busy" @click="load(1, true)">Refresh history</button><span v-if="book?.has_newer" class="micro" role="status">New transactions available. Refresh to include them.</span><span v-if="loading" class="micro" role="status">Loading ledger…</span></div>
    <div class="ledger-row" v-for="entry in book?.entries || []" :key="entry.id"><div><span class="transaction-icon"><ArrowUpRight :size="16" /></span><div class="bank-entry-copy"><strong>{{ entry.description }}</strong><small>{{ entry.account.toUpperCase() }} · ENTRY {{ entry.id }}<template v-if="entry.reference"> · REF {{ entry.reference.slice(0,8) }}</template></small></div></div><time>{{ new Date(entry.created_at).toLocaleString() }}</time><strong :class="favorable(entry) ? 'positive' : 'negative'">{{ entry.amount > 0 ? '+' : '−' }}{{ money(Math.abs(entry.amount)) }} <small>CPH</small><small class="bank-after">{{ entry.account === 'loan' ? 'Debt' : 'Balance' }} after: {{ entry.balance_after == null ? '—' : money(entry.balance_after) + ' CPH' }}</small></strong></div>
    <p v-if="book && !book.entries.length" class="empty-state">No transactions recorded.</p>
    <nav class="bank-pagination" aria-label="Transaction history pages"><button class="button secondary" :disabled="loading || busy || !book || book.page <= 1" @click="load(book.page-1)">Previous page</button><span class="micro">Page {{ book?.page || 1 }} of {{ book?.pages || 1 }} · {{ book?.page_size || 25 }} per page</span><button class="button secondary" :disabled="loading || busy || !book || book.page >= book.pages" @click="load(book.page+1)">Next page</button></nav>
  </section>
</template>
