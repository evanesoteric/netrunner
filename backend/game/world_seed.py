"""Version-one world seed. Keep stable: migration 0005 also uses this data."""
MARKET_ADDRESS = 'null-exchange.internal'


def initial_servers():
    entries = []
    for index, (name, address, x, y) in enumerate([
        ('Vesper Transit: Dispatch Archive', 'vesper-dispatch.internal', 355, 230),
        ('Cobalt Media: Render Farm', 'cobalt-render.internal', 610, 190),
        ('Nimbus Freight: Inventory', 'nimbus-inventory.internal', 760, 310),
        ('Aster Labs: Legacy Backup', 'aster-backup.internal', 450, 280),
        ('Null Exchange', MARKET_ADDRESS, 400, 350),
    ]):
        market = address == MARKET_ADDRESS
        entries.append(dict(id=f'world-{index}', address=address, name=name, operator=name.split(':')[0],
                            category='Hidden market' if market else 'Opportunity', location='Off-grid',
                            short_name=name.split(':')[0].upper(), x=x, y=y, rank=0, security=1,
                            fee=6, delay=24, latency=8, hidden=market, market=market,
                            exploitable=not market, ransom_reward=800))
    return entries
