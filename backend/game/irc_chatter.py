"""Small, deterministic local conversations: no runtime AI, network or timers."""
import hashlib
import json
import random
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def content():
    return json.loads((Path(__file__).parent / 'data' / 'irc_chatter.json').read_text())


def rng_for(slot, purpose):
    seed = hashlib.sha256(f'{slot.pk}:{slot.created_at.isoformat()}:{purpose}'.encode()).digest()
    return random.Random(seed)


def ambient_message(slot, tick):
    data = content()
    thread_index, line = divmod(tick, 3)
    # Shuffle authored and template conversations in cycles rather than rolling the
    # same topic repeatedly. Every three ticks form one coherent conversation.
    pool_size = len(data['threads']) + len(data['templates']) * 4
    cycle, position = divmod(thread_index, pool_size)
    order = list(range(pool_size))
    rng_for(slot, f'order:{cycle}').shuffle(order)
    choice = order[position]
    rng = rng_for(slot, f'thread:{thread_index}')
    speakers = rng.sample(data['members'], 3)
    if choice < len(data['threads']):
        lines = data['threads'][choice]
    else:
        values = {key: rng.choice(pool) for key, pool in data['pools'].items()}
        lines = [text.format(**values) for text in data['templates'][(choice - len(data['threads'])) % len(data['templates'])]]
    return dict(nick=speakers[line], text=lines[line], kind='chat')
