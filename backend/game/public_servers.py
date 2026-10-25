"""Stable fictional public-access proxies. These addresses never leave the simulation."""
from .services import SERVICES, service_fields

PUBLIC_SERVERS = []
for index, (operator, service, address, location, x, y) in enumerate([
    ('Harbor City Library', 'Public Access', 'harbor-library', 'Seattle', 164, 154),
    ('Redwood University', 'Guest Gateway', 'redwood-guest', 'San Francisco', 157, 188),
    ('Pacific Science Museum', 'Visitor Terminal', 'pacific-museum', 'Los Angeles', 173, 207),
    ('Canyon Transit Authority', 'Public Timetables', 'canyon-transit', 'Phoenix', 196, 214),
    ('Summit Community College', 'Student Gateway', 'summit-college', 'Denver', 209, 176),
    ('Lakeside Public Library', 'Reading Room', 'lakeside-library', 'Chicago', 248, 160),
    ('Maple Civic Network', 'Public Access', 'maple-civic', 'Toronto', 265, 146),
    ('Starlight Planetarium', 'Visitor Terminal', 'starlight-planetarium', 'Boston', 287, 155),
    ('Atlantic Port Authority', 'Public Access', 'atlantic-port', 'New York', 288, 181),
    ('Magnolia State University', 'Alumni Gateway', 'magnolia-alumni', 'Atlanta', 257, 201),
    ('Gulf Weather Service', 'Public Forecasts', 'gulf-weather', 'Miami', 271, 229),
    ('Sierra Civic Archive', 'Public Records', 'sierra-archive', 'Mexico City', 213, 251),
    ('Andes Open University', 'Guest Gateway', 'andes-open', 'Bogota', 274, 277),
    ('Orchid Botanical Institute', 'Visitor Terminal', 'orchid-botanical', 'Lima', 285, 322),
    ('Verde City Library', 'Public Access', 'verde-library', 'Sao Paulo', 345, 335),
    ('Austral Transit Cooperative', 'Public Access', 'austral-transit', 'Buenos Aires', 320, 375),
    ('Aurora Maritime Museum', 'Visitor Terminal', 'aurora-museum', 'Reykjavik', 419, 105),
    ('Westhaven Council', 'Public Records', 'westhaven-council', 'Dublin', 455, 143),
    ('Albion Telecommunications', 'Public Access', 'albion-public', 'London', 480, 160),
    ('Seine Open Library', 'Research Terminal', 'seine-library', 'Paris', 486, 180),
    ('Iberian Rail Cooperative', 'Public Timetables', 'iberian-rail', 'Madrid', 461, 207),
    ('Rhine Technical College', 'Guest Gateway', 'rhine-technical', 'Frankfurt', 505, 165),
    ('Baltic Civic Exchange', 'Public Access', 'baltic-civic', 'Stockholm', 522, 119),
    ('Adriatic Cultural Archive', 'Public Access', 'adriatic-archive', 'Rome', 523, 203),
    ('Danube Community Network', 'Public Access', 'danube-community', 'Vienna', 530, 173),
    ('Bosphorus Open Institute', 'Guest Gateway', 'bosphorus-open', 'Istanbul', 567, 195),
    ('Atlas Astronomy Society', 'Visitor Terminal', 'atlas-astronomy', 'Casablanca', 448, 232),
    ('Nile Public Archive', 'Reading Room', 'nile-archive', 'Cairo', 555, 234),
    ('Savannah Civic Network', 'Public Access', 'savannah-civic', 'Nairobi', 574, 294),
    ('Cape Technical Library', 'Public Access', 'cape-library', 'Cape Town', 516, 349),
    ('Cedar Public Library', 'Research Terminal', 'cedar-library', 'Beirut', 579, 217),
    ('Crescent Travel Exchange', 'Public Access', 'crescent-travel', 'Dubai', 623, 244),
    ('Monsoon Open College', 'Guest Gateway', 'monsoon-college', 'Mumbai', 654, 239),
    ('Lotus Civic Records', 'Public Access', 'lotus-civic', 'Bangkok', 725, 253),
    ('Straits Maritime Library', 'Public Access', 'straits-library', 'Singapore', 730, 294),
    ('Pearl Community Network', 'Public Access', 'pearl-community', 'Hong Kong', 782, 221),
    ('Han River Science Center', 'Visitor Terminal', 'han-science', 'Seoul', 826, 171),
    ('Kanto Open University', 'Guest Gateway', 'kanto-open', 'Tokyo', 862, 194),
    ('Coral City Library', 'Public Access', 'coral-library', 'Sydney', 859, 357),
    ('Southern Sky Observatory', 'Visitor Terminal', 'southern-sky', 'Auckland', 927, 405),
], 1):
    PUBLIC_SERVERS.append(dict(id=f'public-{index:02}', address=f'{address}.internal', name=f'{operator}: {service}',
                               operator=operator, category='Public', location=location, short_name=operator.upper(),
                               x=x, y=y, rank=0, security=1, fee=3 + index % 6, delay=10 + index % 17,
                               latency=4 + index % 9, port=3389 if index % 5 == 0 else 443 if index % 3 == 0 else 22, exploitable=False))
for index, server in enumerate(PUBLIC_SERVERS[5:]):
    server.update(service_fields(list(SERVICES)[index % len(SERVICES)]))

PUBLIC_BY_ID = {server['id']: server for server in PUBLIC_SERVERS}
