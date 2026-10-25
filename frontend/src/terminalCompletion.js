// Completion only offers commands and names already available to this runner.
const commands = {
  terminal: ['exploit', 'exploits', 'applets', 'use', 'trace', 'install', 'deploy', 'abort', 'accept', 'apps', 'brief', 'clear', 'connect', 'contracts', 'decrypt', 'disconnect', 'get', 'help', 'history', 'jump', 'lockpick', 'logcleaner', 'login', 'ls', 'rm', 'route', 'rumors', 'scan', 'status', 'submit'],
  mapper: ['help', 'scan'], decryptor: ['decrypt', 'help'], monitor: ['help', 'trace'],
  bank: ['balance', 'help', 'history'], rootkit: ['help', 'install'], ransomware: ['deploy', 'help'],
}
function subsequence(query, candidate) {
  let index = 0
  for (const char of candidate.toLowerCase()) if (char === query[index]) index++
  return index === query.length
}
export function completion(text, cursor, app, slot) {
  const before = text.slice(0, cursor), word = before.match(/\S*$/)[0]
  const start = cursor - word.length, end = cursor + (text.slice(cursor).match(/^\S*/)[0].length)
  const context = text.slice(0, start).trim().split(/\s+/).filter(Boolean)
  let pool = []
  if (!context.length) pool = commands[app] || ['help']
  else if (context.length === 1) {
    const verb = context[0].toLowerCase()
    if (['scan', 'connect', 'deploy'].includes(verb)) pool = [...(slot.network_directory || []).map(node => node.address), slot.active_contract?.target, slot.remote_target]
    if (verb === 'jump') pool = (slot.backdoors || []).map(node => node.target)
    if (verb === 'accept') pool = (slot.contracts || []).map(job => String(job.id))
    if (verb === 'exploit') pool = (slot.exploits || []).map(item => item.id)
    if (verb === 'use') pool = slot.installed_software || []
    if (verb === 'logcleaner') pool = (slot.installed_software || []).filter(id => id.startsWith('cleaner-'))
    if (['get', 'rm', 'decrypt'].includes(verb)) {
      pool = !slot.connected && ['rm', 'decrypt'].includes(verb) ? (slot.local_files || []).map(file => file.name) : [slot.active_contract?.file]
      const host = slot.remote_target || slot.active_contract?.target
      for (const entry of (!slot.connected && ['rm', 'decrypt'].includes(verb) ? [] : slot.mission_log) || []) {
        if (host && entry.text.startsWith(`Host: ${host}\n`)) {
          const file = entry.text.match(/^Archive: (.*?) \/ /m)?.[1]
          if (file && file !== 'missing') pool.push(file)
        }
      }
    }
  }
  pool = [...new Set(pool.filter(Boolean))].sort()
  const query = word.toLowerCase()
  const prefixes = pool.filter(item => item.toLowerCase().startsWith(query))
  const candidates = prefixes.length ? prefixes : pool.filter(item => subsequence(query, item))
  let common = candidates[0] || ''
  for (const item of candidates) while (common && !item.startsWith(common)) common = common.slice(0, -1)
  return { start, end, candidates, common: prefixes.length ? common : '' }
}
