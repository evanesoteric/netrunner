"""The fictional world's public product, relay, and contract catalogs."""
CURRENCY = {'name': 'Cipher', 'symbol': 'CPH'}
RANKS = ['Ghost', 'Signal', 'Operator', 'Spectre', 'Architect']
THRESHOLDS = [0, 100, 250, 450, 700]
SUCCESS_COOLDOWN = 300
FAILURE_COOLDOWN = 600


def rank_for(reputation):
    return max(i for i, threshold in enumerate(THRESHOLDS) if reputation >= threshold)


HARDWARE = {}
FAMILIES = {
    'cpu': ['Mica', 'Kestrel', 'Raptor', 'Chimera', 'Singularity'],
    'gateway': ['Peregrine', 'Nightjar', 'Blackglass', 'Obsidian', 'Event Horizon'],
    'memory': ['Reed', 'Lattice', 'Prism', 'Synapse', 'Mnemosyne'],
    'storage': ['Pebble', 'Slate', 'Basalt', 'Monolith', 'Deep Vault'],
}
for category, names in FAMILIES.items():
    for tier, family in enumerate(names, 1):
        for variant in ('standard', 'specialist'):
            specialist = variant == 'specialist'
            product_id = f'{category}-{tier}-{variant}'
            suffix = {'cpu': 'Sprint', 'gateway': 'Veil', 'memory': 'Dense', 'storage': 'Archive'}[category] if specialist else 'Core'
            stats = {
                'cpu': {'speed': tier * 2 + (2 if specialist else 0), 'description': 'Compute speed reduces time spent running intrusion tools.'},
                'gateway': {'hops': tier + (1 if specialist else 2), 'stealth': tier * (3 if specialist else 1), 'bandwidth': tier * (2 if specialist else 4), 'description': 'Veil favors trace resistance; Core favors longer routes and faster transfers.'},
                'memory': {'ram': tier * (18 if specialist else 12), 'description': 'RAM is shared by every running application. Close tools to reclaim it.'},
                'storage': {'capacity': tier * (240 if specialist else 160), 'description': 'Local storage must hold recovered contract files.'},
            }[category]
            HARDWARE[product_id] = {'id': product_id, 'category': category, 'name': f'{family} {suffix}', 'tier': tier, 'price': int({'cpu': 220, 'gateway': 280, 'memory': 190, 'storage': 170}[category] * tier ** 2 * (1.35 if specialist else 1)), **stats}

SOFTWARE = {}
TOOL_KINDS = {
    'mapper': ('Network mapper', 'Cartograph', 'scan <host>', 100, 2),
    'cracker': ('Authentication cracker', 'Lockpick', 'crack <port>', 160, 3),
    'decryptor': ('File decryptor', 'Rosetta', 'decrypt <file>', 180, 3),
    'cleaner': ('Log cleaner', 'Ashfall', 'erase', 110, 2),
    'monitor': ('Trace monitor', 'Tripwire', 'trace', 90, 2),
}
for kind, (label, family, usage, base, ram) in TOOL_KINDS.items():
    for tier in range(1, 6):
        for variant in ('standard', 'compact'):
            compact = variant == 'compact'
            product_id = f'{kind}-{tier}-{variant}'
            SOFTWARE[product_id] = {'id': product_id, 'category': 'software', 'kind': kind, 'name': f'{family} {tier}.0 {"Micro" if compact else "Pro"}', 'label': label, 'tier': tier, 'power': tier, 'ram': max(1, ram + tier - (2 if compact else 0)), 'speed': 0.8 if compact else 1.3, 'price': int(base * tier ** 2 * (1.4 if compact else 1)), 'usage': usage, 'description': 'Micro uses less RAM but runs slower.' if compact else 'Pro runs faster at the cost of more RAM.'}

# Epic licenses are sold only by the discovered Null Exchange.
for kind, name, price, usage, description in [
    ('rootkit', 'Wraith Rootkit', 2400, 'install', 'Persist a backdoor on the current mounted server. Future jumps bypass proxies and remote access logs.'),
    ('ransomware', 'Eclipse Ransomware', 1800, 'deploy <host>', 'Run up to three simulated operations against amber opportunity servers. Each completes after two minutes.'),
]:
    product_id = f'{kind}-epic'
    SOFTWARE[product_id] = dict(id=product_id, category='software', kind=kind, name=name,
                               label='Epic software', tier=2, power=5, ram=3, speed=1.3,
                               price=price, usage=usage, description=description,
                               black_market=True, grade='epic')

PRODUCTS = {**HARDWARE, **SOFTWARE}
STARTER_EQUIPMENT = {kind: f'{kind}-1-standard' for kind in FAMILIES}
STARTER_SOFTWARE = ['mapper-1-standard', 'cracker-1-standard', 'cleaner-1-standard']
BUILTIN_APPS = {
    'terminal': {'id': 'terminal', 'name': 'Local terminal', 'description': 'Shell, broker reservations, remote file access, and deliveries.', 'ram': 1, 'console': True},
    'atlas': {'id': 'atlas', 'name': 'Atlas routing desk', 'description': 'Manage your server directory and build an ordered proxy chain.', 'ram': 1, 'console': False},
    'broker': {'id': 'broker', 'name': 'Contract broker', 'description': 'Read briefs, target addresses, clearance, and availability.', 'ram': 0, 'console': False},
    'market': {'id': 'market', 'name': 'Hardware & software exchange', 'description': 'Choose individual components and tool licenses.', 'ram': 0, 'console': False},
    'bank': {'id': 'bank', 'name': 'Cipher bank', 'description': 'Your separate account terminal and ledger.', 'ram': 0, 'console': True},
}
# Coordinates are on the original Atlas SVG, not real infrastructure.
RELAYS = [
    {'id': 'new-york', 'name': 'New York', 'operator': 'Hudson relay', 'x': 275, 'y': 174, 'delay': 18, 'latency': 8, 'fee': 5, 'rank': 0},
    {'id': 'reykjavik', 'name': 'Reykjavik', 'operator': 'Cold storage', 'x': 432, 'y': 94, 'delay': 28, 'latency': 12, 'fee': 9, 'rank': 0},
    {'id': 'london', 'name': 'London', 'operator': 'Docklands exchange', 'x': 472, 'y': 148, 'delay': 20, 'latency': 6, 'fee': 6, 'rank': 0},
    {'id': 'berlin', 'name': 'Berlin', 'operator': 'Spree mesh', 'x': 509, 'y': 145, 'delay': 22, 'latency': 7, 'fee': 7, 'rank': 0},
    {'id': 'sao-paulo', 'name': 'São Paulo', 'operator': 'Southbound', 'x': 334, 'y': 336, 'delay': 30, 'latency': 15, 'fee': 10, 'rank': 0},
    {'id': 'cape-town', 'name': 'Cape Town', 'operator': 'Cape ghost', 'x': 527, 'y': 359, 'delay': 26, 'latency': 12, 'fee': 8, 'rank': 0},
    {'id': 'mumbai', 'name': 'Mumbai', 'operator': 'Monsoon transit', 'x': 666, 'y': 228, 'delay': 24, 'latency': 9, 'fee': 8, 'rank': 0},
    {'id': 'singapore', 'name': 'Singapore', 'operator': 'Straits relay', 'x': 740, 'y': 285, 'delay': 32, 'latency': 11, 'fee': 11, 'rank': 0},
    {'id': 'tokyo', 'name': 'Tokyo', 'operator': 'Neon lattice', 'x': 852, 'y': 183, 'delay': 35, 'latency': 14, 'fee': 13, 'rank': 1},
    {'id': 'sydney', 'name': 'Sydney', 'operator': 'Harbour silence', 'x': 869, 'y': 367, 'delay': 40, 'latency': 17, 'fee': 15, 'rank': 1},
    {'id': 'anchorage', 'name': 'Anchorage', 'operator': 'Polar relay', 'x': 160, 'y': 110, 'delay': 48, 'latency': 19, 'fee': 18, 'rank': 2},
    {'id': 'helsinki', 'name': 'Helsinki', 'operator': 'White noise', 'x': 540, 'y': 110, 'delay': 52, 'latency': 16, 'fee': 20, 'rank': 3},
]
# Stable IDs preserve existing routes while the player sees individual servers.
SERVER_IDENTITIES = {
    'new-york': ('NY Public Library Terminal', 'NY Public Library', 'library-ny.internal', 'Public', 'New York', 'NY LIBRARY'),
    'reykjavik': ('Northstar University: Alumni Gateway', 'Northstar University', 'northstar-alumni.internal', 'Academic', 'Reykjavik', 'NORTHSTAR U.'),
    'london': ('Intel Corp: Public Access', 'Intel Corp', 'intel-public.internal', 'Corporate', 'London', 'INTEL PUBLIC'),
    'berlin': ('MilTech Research Center', 'MilTech', 'miltech-research.internal', 'Research', 'Berlin', 'MILTECH R&D'),
    'sao-paulo': ('Verde Financial: Public Gateway', 'Verde Financial', 'verde-gateway.internal', 'Financial', 'São Paulo', 'VERDE FIN.'),
    'cape-town': ('Cape Observatory Data Archive', 'Cape Observatory', 'cape-archive.internal', 'Research', 'Cape Town', 'CAPE ARCHIVE'),
    'mumbai': ('Helios Shipping: Logistics Server', 'Helios Shipping', 'helios-logistics.internal', 'Corporate', 'Mumbai', 'HELIOS LOG.'),
    'singapore': ('Straits Exchange: Market Feed', 'Straits Exchange', 'straits-feed.internal', 'Financial', 'Singapore', 'STRAITS EXCH.'),
    'tokyo': ('Shinsei Robotics: Visitor System', 'Shinsei Robotics', 'shinsei-visitor.internal', 'Corporate', 'Tokyo', 'SHINSEI VISITOR'),
    'sydney': ('Southern Cross University Mainframe', 'Southern Cross University', 'southern-cross.internal', 'Academic', 'Sydney', 'SOUTHERN CROSS'),
    'anchorage': ('PolarNet Satellite Control', 'PolarNet', 'polarnet-control.internal', 'Infrastructure', 'Anchorage', 'POLARNET CTRL'),
    'helsinki': ('White Noise Systems: Secure Relay', 'White Noise Systems', 'white-noise.internal', 'Infrastructure', 'Helsinki', 'WHITE NOISE'),
}
for server in RELAYS:
    name, operator, address, category, location, short_name = SERVER_IDENTITIES[server['id']]
    server.update(name=name, operator=operator, address=address, category=category, location=location, short_name=short_name)
STARTER_ATLAS_NODES = ['london', 'berlin', 'new-york', 'reykjavik']
RELAY_BY_ID = {node['id']: node for node in RELAYS}
HOME_NODE = {'name': 'Your gateway', 'x': 196, 'y': 205}
CONTRACTS = []
for tier, (client, target, family, location) in enumerate([
    ('Anonymous', 'helix', 'Helix research', (564, 170)),
    ('Meridian Group', 'meridian', 'Meridian ledger', (790, 214)),
    ('Unknown sender', 'aegis', 'Aegis protocol', (312, 163)),
    ('Free Signal', 'citadel', 'Citadel evidence', (635, 160)),
    ('The Collective', 'oracle', 'Oracle intelligence', (825, 320)),
]):
    for index, (objective, encrypted) in enumerate([('retrieve', False), ('retrieve', True), ('delete', False)]):
        filename = ['research.dat', 'ledger.enc', 'audit.log'][index]
        CONTRACTS.append({'id': f'{tier}-{index}', 'rank': tier, 'title': f'{family} // {"sealed archive" if encrypted else "quiet removal" if objective == "delete" else "recovery"}', 'client': client, 'target': f'{target}-{index}.internal', 'reward': 220 + tier * 200 + index * 80, 'reputation': 35 + tier * 10, 'description': f'{"Remove" if objective == "delete" else "Recover"} {filename} from {target}-{index}.internal. {"The archive is encrypted. " if encrypted else ""}Leave no remote access logs and deliver proof through the broker.', 'objective': objective, 'file': filename, 'encrypted': encrypted, 'security': tier + 1, 'port': 443 if encrypted else 22, 'size': 24 + tier * 32 + (16 if encrypted else 0), 'x': location[0] + index * 8, 'y': location[1] + index * 8})
CONTRACT_BY_ID = {job['id']: job for job in CONTRACTS}
