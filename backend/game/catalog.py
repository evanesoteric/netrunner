CURRENCY = {'name': 'Cipher', 'symbol': 'CPH'}
RANKS = ['Ghost', 'Signal', 'Operator', 'Spectre', 'Architect']
THRESHOLDS = [0, 100, 250, 450, 700]
UPGRADES = {
    'hardware': {'name': 'Processor', 'model': 'HEXA // compute array', 'description': 'More processing power. Less time exposed.', 'base_price': 300},
    'gateway': {'name': 'Gateway', 'model': 'VEIL // relay gateway', 'description': 'Route through deeper layers of the network.', 'base_price': 400},
    'software': {'name': 'Software', 'model': 'WRAITH // intrusion suite', 'description': 'Better tools mean a cleaner breach.', 'base_price': 350},
}
CONTRACTS = [
    {'id': f'{tier}-{index}', 'rank': tier, 'title': title, 'client': client, 'target': f'{target}.internal', 'reward': 220 + tier * 180 + index * 60, 'reputation': 35 + tier * 10, 'description': description}
    for tier, title, client, target, description in [
        (0, 'Recover the lost archive', 'Anonymous', 'helix-archive', 'Retrieve an abandoned research archive from a neglected Helix node.'),
        (1, 'A matter of discretion', 'Meridian Group', 'meridian-ledger', 'Recover a private ledger before the next corporate audit.'),
        (2, 'The glass protocol', 'Unknown sender', 'aegis-vault', 'Extract a classified protocol from the Aegis research vault.'),
        (3, 'Break the silence', 'Free Signal', 'citadel-core', 'Recover evidence buried inside a fortified Citadel node.'),
        (4, 'No gods in the machine', 'The Collective', 'oracle-nexus', 'Infiltrate the Oracle nexus and retrieve its sealed intelligence archive.'),
    ]
    for index in range(2)
]
# Each broker tier offers two distinct jobs.
for contract in CONTRACTS:
    if contract['id'].endswith('-1'):
        contract['title'] = ['An echo in the wires', 'Off the record', 'Ghost in the vault', 'A quiet extraction', 'The last firewall'][contract['rank']]
        contract['target'] = 'mirror-' + contract['target']

def rank_for(reputation):
    return max(i for i, threshold in enumerate(THRESHOLDS) if reputation >= threshold)
