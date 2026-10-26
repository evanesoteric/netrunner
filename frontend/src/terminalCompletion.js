// Completion only offers commands and names already available to this runner.
const commands = {
  terminal: ['assignments', 'select', 'ping', 'resolve', 'exploit', 'exploits', 'applets', 'use', 'trace', 'install', 'deploy', 'abort', 'accept', 'apps', 'brief', 'cat', 'cd', 'pwd', 'find', 'clear', 'connect', 'contracts', 'decrypt', 'disconnect', 'get', 'help', 'history', 'jump', 'lockpick', 'logcleaner', 'login', 'ls', 'rm', 'route', 'rumors', 'scan', 'status', 'submit'],
  mapper: ['help', 'scan'], decryptor: ['decrypt', 'help'], monitor: ['help', 'trace'],
  bank: ['accounts', 'balance', 'deposit', 'withdraw', 'loan', 'repay', 'help', 'history'], rootkit: ['help', 'install'], ransomware: ['deploy', 'help'],
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
    if (['ping', 'resolve', 'scan', 'connect', 'deploy'].includes(verb)) pool = [...[...(slot.network_directory || []), ...(slot.target_directory || [])].flatMap(node => [node.ip_address, node.address]), slot.active_contract?.target, slot.active_contract?.ip_address, slot.remote_ip, slot.remote_target]
    if (verb === 'jump') pool = (slot.backdoors || []).flatMap(node => [node.ip_address, node.target])
    if (verb === 'select') pool = (slot.accepted_contracts || []).map(job => String(job.id))
    if (verb === 'accept') pool = (slot.contracts || []).map(job => String(job.id))
    if (verb === 'exploit') pool = (slot.exploits || []).flatMap(item => [item.id, '/exploits/' + item.id])
    if (verb === 'use') pool = slot.installed_software || []
    if (verb === 'logcleaner') pool = (slot.installed_software || []).filter(id => id.startsWith('cleaner-'))
    if (['ls', 'cd', 'cat', 'get', 'rm', 'decrypt'].includes(verb)) {
      if (!slot.connected) {
        const cwd = slot.local_cwd || '/'
        pool = (slot.local_entries || []).filter(entry => verb === 'cd' ? entry.type === 'directory' : verb === 'decrypt' || verb === 'rm' ? entry.type === 'file' : true).map(entry => {
          const path = entry.path + (entry.type === 'directory' ? '/' : '')
          if (word.startsWith('/')) return path
          if (cwd === '/') return path.slice(1)
          return path.startsWith(cwd + '/') ? path.slice(cwd.length + 1) : '../' + path.slice(1)
        })
        if (['cd', 'ls'].includes(verb)) pool.push('/', '..')
      } else if (slot.connected) {
        const cwd = (slot.remote_cwd || '/').split('/').filter(Boolean)
        pool = (slot.remote_entries || []).filter(entry => ['ls', 'cd'].includes(verb) ? entry.type === 'directory' : entry.type !== 'directory').map(entry => {
          let path = entry.path
          if (!word.startsWith('/')) {
            const parts = path.split('/').filter(Boolean)
            let shared = 0
            while (shared < cwd.length && parts[shared] === cwd[shared]) shared++
            path = [...Array(cwd.length - shared).fill('..'), ...parts.slice(shared)].join('/') || '.'
          }
          return path + (entry.type === 'directory' ? '/' : '')
        })
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
