import alltheitems.__main__ as ati

import bottle
import collections
import contextlib
import datetime
import itertools
import json
import pathlib
import random
import re
import xml.sax.saxutils

import alltheitems.item
import alltheitems.util
import alltheitems.world

class FillLevel:
    def __init__(self, stack_size, total_items, max_slots, *, is_smart_chest=True):
        self.stack_size = stack_size
        self.total_items = total_items
        self.max_slots = max_slots
        self.is_smart_chest = is_smart_chest

    def __str__(self):
        if self.total_items == 0:
            return '{} is empty.'.format('SmartChest' if self.is_smart_chest else 'Chest')
        elif self.total_items == self.max_items:
            return '{} is full.'.format('SmartChest' if self.is_smart_chest else 'Chest')
        else:
            stacks, items = self.stacks
            return '{} is filled {}% ({} {stack}{}{} out of {} {stack}s).'.format('SmartChest' if self.is_smart_chest else 'Chest', int(100 * self.fraction), stacks, '' if stacks == 1 else 's', ' and {} item{}'.format(items, '' if items == 1 else 's') if items > 0 else '', self.max_slots, stack='item' if self.stack_size == 1 else 'stack')

    @property
    def fraction(self):
        return self.total_items / self.max_items

    def is_empty(self):
        return self.total_items == 0

    def is_full(self):
        return self.total_items == self.max_items

    @property
    def max_items(self):
        return self.max_slots * self.stack_size

    @property
    def stacks(self):
        return divmod(self.total_items, self.stack_size)

CONTAINERS = [ # layer coords of all counted container blocks in a SmartChest
    (3, -7, 3),
    (3, -7, 4),
    (4, -7, 4),
    (5, -7, 3),
    (5, -7, 4),
    (2, -6, 3),
    (3, -6, 2),
    (3, -6, 3),
    (2, -5, 2),
    (2, -5, 3),
    (3, -5, 3),
    (2, -4, 3),
    (3, -4, 2),
    (3, -4, 3),
    (3, -3, 2),
    (4, -3, 2),
    (5, -3, 2),
    (6, -3, 2),
    (5, -2, 2),
    (6, -2, 2),
    (5, 0, 2),
    (5, 0, 3)
]

STONE_VARIANTS = {
    0: 'stone',
    1: 'granite',
    2: 'polished granite',
    3: 'diorite',
    4: 'polished diorite',
    5: 'andesite',
    6: 'polished andesite'
}

HOPPER_FACINGS = {
    0: 'down',
    1: 'up', #for droppers
    2: 'north',
    3: 'south',
    4: 'west',
    5: 'east'
}

TORCH_FACINGS = {
    1: 'to its west',
    2: 'to its east',
    3: 'to its north',
    4: 'to its south',
    5: 'below'
}

HTML_COLORS = {
    'cyan': '#0ff',
    'cyan2': '#0ff',
    'gray': '#777',
    'red': '#f00',
    'orange': '#f70',
    'yellow': '#ff0',
    'white': '#fff',
    'white2': '#fff',
    None: 'transparent'
}

def hopper_chain_connected(start_coords, end_coords, *, world=None, chunk_cache=None, block_at=None):
    if world is None:
        world = alltheitems.world.World()
    if chunk_cache is None:
        chunk_cache = {}
    if block_at is None:
        block_at=world.block_at
    visited_coords = set()
    x, y, z = start_coords
    while (x, y, z) != end_coords:
        if (x, y, z) in visited_coords:
            return False, 'hopper chain points into itself at {} {} {}'.format(x, y, z)
        visited_coords.add((x, y, z))
        block = block_at(x, y, z, chunk_cache=chunk_cache)
        if block['id'] != 'minecraft:hopper':
            return False, 'block at {} {} {} is not a <a href="/block/minecraft/hopper">hopper</a>'.format(x, y, z, *end_coords)
        if block['damage'] & 0x7 == 0:
            y -= 1 # down
        elif block['damage'] & 0x7 == 2:
            z -= 1 # north
        elif block['damage'] & 0x7 == 3:
            z += 1 # south
        elif block['damage'] & 0x7 == 4:
            x -= 1 # west
        elif block['damage'] & 0x7 == 5:
            x += 1 # east
        else:
            raise ValueError('Unknown hopper facing {} at {}'.format(block['damage'] & 0x7, (x, y, z)))
    return True, None

def smart_chest_schematic(document_root=ati.document_root):
    layers = {}
    with (document_root / 'static' / 'smartchest.txt').open() as smart_chest_layers:
        current_y = None
        current_layer = None
        for line in smart_chest_layers:
            if line == '\n':
                continue
            match = re.fullmatch('layer (-?[0-9]+)\n', line)
            if match:
                # new layer
                if current_y is not None:
                    layers[current_y] = current_layer
                current_y = int(match.group(1))
                current_layer = []
            else:
                current_layer.append(line.rstrip('\r\n'))
        if current_y is not None:
            layers[current_y] = current_layer
    return sorted(layers.items())

def chest_iter():
    """Returns an iterator yielding tuples (x, corridor, y, floor, z, chest)."""
    with (ati.assets_root / 'json' / 'cloud.json').open() as cloud_json:
        cloud_data = json.load(cloud_json)
    for y, floor in enumerate(cloud_data):
        for x, corridor in sorted(((int(x), corridor) for x, corridor in floor.items()), key=lambda tup: tup[0]):
            for z, chest in enumerate(corridor):
                yield x, corridor, y, floor, z, chest

def chest_coords(item, *, include_meta=False):
    if not isinstance(item, alltheitems.item.Item):
        item = alltheitems.item.Item(item)
    for x, corridor, y, _, z, chest in chest_iter():
        if item == chest:
            if include_meta:
                return (x, y, z), len(corridor), None if isinstance(chest, str) else chest.get('name'), None if isinstance(chest, str) else chest.get('sorter')
            else:
                return x, y, z
    if include_meta:
        return None, 0, None, None

def global_error_checks(*, chunk_cache=None, block_at=alltheitems.world.World().block_at):
    cache_path = ati.cache_root / 'cloud-globals.json'
    max_age = datetime.timedelta(hours=1, minutes=random.randrange(0, 60)) # use a random value between 1 and 2 hours for the cache expiration
    if cache_path.exists() and datetime.datetime.utcfromtimestamp(cache_path.stat().st_mtime) > datetime.datetime.utcnow() - max_age:
        # cached check results are recent enough
        with cache_path.open() as cache_f:
            cache = json.load(cache_f)
        return cache
    # cached check results are too old, recheck
    if chunk_cache is None:
        chunk_cache = {}
    # error check: input hopper chain
    start = 14, 61, 32 # the first hopper after the buffer elevator
    end = -1, 25, 52 # the half of the uppermost overflow chest into which the hopper chain is pointing
    is_connected, message = hopper_chain_connected(start, end, chunk_cache=chunk_cache, block_at=block_at)
    if not is_connected:
        return 'Input hopper chain at {} is not connected to the unsorted overflow at {}: {}.'.format(start, end, message)
    if ati.cache_root.exists():
        with cache_path.open('w') as cache_f:
            json.dump(message, cache_f, sort_keys=True, indent=4)

def chest_error_checks(x, y, z, base_x, base_y, base_z, item, item_name, exists, stackable, durability, has_smart_chest, has_sorter, has_overflow, filler_item, sorting_hopper, missing_overflow_hoppers, north_half, south_half, corridor_length, pre_sorter, layer_coords, block_at, items_data, chunk_cache, document_root):
    if stackable and has_sorter:
        # error check: overflow exists
        if not has_overflow:
            if len(missing_overflow_hoppers) == 3:
                return 'Missing overflow hoppers.'
            elif len(missing_overflow_hoppers) > 1:
                return 'Overflow hoppers at x={} do not exist.'.format(missing_overflow_hoppers)
            elif len(missing_overflow_hoppers) == 1:
                return 'Overflow hopper at x={} does not exist, is {}.'.format(next(iter(missing_overflow_hoppers)), block_at(next(iter(missing_overflow_hoppers)), base_y - 7, base_z - 1)['id'])
            else:
                return 'Missing overflow.'
        # error check: pre-sorter for lower floors
        if y > 4:
            if pre_sorter is None:
                return 'Preliminary sorter coordinate missing from cloud.json.'
            pre_sorting_hopper = block_at(pre_sorter, 30, 52, chunk_cache=chunk_cache)
            if pre_sorting_hopper['id'] != 'minecraft:hopper':
                return 'Preliminary sorter is missing (should be at {} 30 52).'.format(pre_sorter)
            if pre_sorting_hopper['damage'] != 3:
                return 'Preliminary sorting hopper ({} 30 52) should be pointing south, but is facing {}.'.format(pre_sorter, HOPPER_FACINGS[pre_sorting_hopper['damage']])
            empty_slots = set(range(5))
            for slot in pre_sorting_hopper['tileEntity']['Items']:
                empty_slots.remove(slot['Slot'])
                if slot['Slot'] == 0:
                    if not item.matches_slot(slot):
                        return 'Preliminary sorting hopper is sorting the wrong item: {}.'.format(alltheitems.item.Item.from_slot(slot, items_data=items_data).link_text())
                else:
                    if not filler_item.matches_slot(slot):
                        return 'Preliminary sorting hopper has wrong filler item in slot {}: {} (should be {}).'.format(slot['Slot'], alltheitems.item.Item.from_slot(slot, items_data=items_data).link_text(), filler_item.link_text())
                    if slot['Count'] > 1:
                        return 'Preliminary sorting hopper: too much {} in slot {}.'.format(filler_item.link_text(), slot['Slot'])
            if len(empty_slots) > 0:
                if len(empty_slots) == 5:
                    return 'Preliminary sorting hopper is empty.'
                elif len(empty_slots) == 1:
                    return 'Slot {} of the preliminary sorting hopper is empty.'.format(next(iter(empty_slots)))
                else:
                    return 'Some slots in the preliminary sorting hopper are empty: {}.'.format(alltheitems.util.join(empty_slots))
    if has_sorter:
        # error check: sorting hopper
        if sorting_hopper['damage'] != 2:
            return 'Sorting hopper ({} {} {}) should be pointing north, but is facing {}.'.format(base_x - 2 if z % 2 == 0 else base_x + 2, base_y - 3, base_z, HOPPER_FACINGS[sorting_hopper['damage']])
        empty_slots = set(range(5))
        for slot in sorting_hopper['tileEntity']['Items']:
            empty_slots.remove(slot['Slot'])
            if slot['Slot'] == 0 and stackable:
                if not item.matches_slot(slot) and not filler_item.matches_slot(slot):
                    return 'Sorting hopper is sorting the wrong item: {}.'.format(alltheitems.item.Item.from_slot(slot, items_data=items_data).link_text())
            else:
                if not filler_item.matches_slot(slot):
                    return 'Sorting hopper has wrong filler item in slot {}: {} (should be {}).'.format(slot['Slot'], alltheitems.item.Item.from_slot(slot, items_data=items_data).link_text(), filler_item.link_text())
                if slot['Count'] > 1:
                    return 'Sorting hopper: too much {} in slot {}.'.format(filler_item.link_text(), slot['Slot'])
        if len(empty_slots) > 0:
            if len(empty_slots) == 5:
                return 'Sorting hopper is empty.'
            elif len(empty_slots) == 1:
                return 'Slot {} of the sorting hopper is empty.'.format(next(iter(empty_slots)))
            else:
                return 'Some slots in the sorting hopper are empty: {}.'.format(alltheitems.util.join(empty_slots))
    if exists:
        # error check: wrong items in access chest
        for slot in itertools.chain(north_half['tileEntity']['Items'], south_half['tileEntity']['Items']):
            if not item.matches_slot(slot):
                return 'Access chest contains items of the wrong kind: {}.'.format(alltheitems.item.Item.from_slot(slot, items_data=items_data).link_text())
        # error check: wrong name on sign
        sign = block_at(base_x - 1 if z % 2 == 0 else base_x + 1, base_y + 1, base_z + 1, chunk_cache=chunk_cache)
        if sign['id'] != 'minecraft:wall_sign':
            return 'Sign is missing.'
        text = []
        for line in range(1, 5):
            line_text = json.loads(sign['tileEntity']['Text{}'.format(line)])['text'].translate(dict.fromkeys(range(0xf700, 0xf704), None))
            if len(line_text) > 0:
                text.append(line_text)
        text = ' '.join(text)
        if text != item_name.translate({0x2161: 'II'}):
            return 'Sign has wrong text: should be {!r}, is {!r}.'.format(xml.sax.saxutils.escape(item_name), xml.sax.saxutils.escape(text))
    if has_overflow:
        # error check: overflow hopper chain
        start = base_x + 5 if z % 2 == 0 else base_x - 5, base_y - 7, base_z - 1
        end = -35, 6, 38 # position of the dropper leading into the Smelting Center's item elevator
        is_connected, message = hopper_chain_connected(start, end, chunk_cache=chunk_cache, block_at=block_at)
        if not is_connected:
            return 'Overflow hopper chain at {} is not connected to the Smelting Center item elevator at {}: {}.'.format(start, end, message)
    if exists and has_smart_chest:
        # error check: all blocks
        for layer_y, layer in smart_chest_schematic(document_root=document_root):
            for layer_x, row in enumerate(layer):
                for layer_z, block_symbol in enumerate(row):
                    # determine the coordinate of the current block
                    exact_x, exact_y, exact_z = layer_coords(layer_x, layer_y, layer_z)
                    # determine current block
                    block = block_at(exact_x, exact_y, exact_z, chunk_cache=chunk_cache)
                    # check against schematic
                    if block_symbol == ' ':
                        # air
                        if block['id'] != 'minecraft:air':
                            return 'Block at {} {} {} should be air, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                    elif block_symbol == '!':
                        # sign
                        if block['id'] != 'minecraft:wall_sign':
                            return 'Block at {} {} {} should be a sign, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        if block['damage'] != (4 if z % 2 == 0 else 5):
                            return 'Sign at {} {} {} is facing the wrong way.'.format(exact_x, exact_y, exact_z)
                    elif block_symbol == '#':
                        # chest
                        if block['id'] != 'minecraft:chest':
                            return 'Block at {} {} {} should be a chest, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        for slot in block['tileEntity']['Items']:
                            if not item.matches_slot(slot):
                                return 'Storage chest at {} {} {} contains items of the wrong kind: {}.'.format(exact_x, exact_y, exact_z, alltheitems.item.Item.from_slot(slot, items_data=items_data).link_text())
                    elif block_symbol == '<':
                        # hopper facing south
                        if block['id'] != 'minecraft:hopper':
                            return 'Block at {} {} {} should be a hopper, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        if block['damage'] & 0x7 != 3: # south
                            return 'Hopper at {} {} {} should be pointing south, is {}.'.format(exact_x, exact_y, exact_z, HOPPER_FACINGS[block['damage']])
                        storage_hoppers = {
                            (5, -7, 4),
                            (6, -5, 4)
                        }
                        if (layer_x, layer_y, layer_z) in storage_hoppers:
                            for slot in block['tileEntity']['Items']:
                                if not item.matches_slot(slot):
                                    return 'Storage hopper at {} {} {} contains items of the wrong kind: {}.'.format(exact_x, exact_y, exact_z, alltheitems.item.Item.from_slot(slot, items_data=items_data).link_text())
                    elif block_symbol == '>':
                        # hopper facing north
                        if layer_y == -7 and layer_x == 0 and z < 8:
                            # the first few chests get ignored because their overflow points in the opposite direction
                            pass #TODO introduce special checks for them
                        else:
                            if block['id'] != 'minecraft:hopper':
                                return 'Block at {} {} {} should be a hopper, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                            if block['damage'] & 0x7 != 2: # north
                                return 'Hopper at {} {} {} should be pointing north, is {}.'.format(exact_x, exact_y, exact_z, HOPPER_FACINGS[block['damage']])
                            storage_hoppers = {
                                (3, -7, 3),
                                (3, -4, 2)
                            }
                            if (layer_x, layer_y, layer_z) in storage_hoppers:
                                for slot in block['tileEntity']['Items']:
                                    if not item.matches_slot(slot):
                                        return 'Storage hopper at {} {} {} contains items of the wrong kind: {}.'.format(exact_x, exact_y, exact_z, alltheitems.item.Item.from_slot(slot, items_data=items_data).link_text())
                    elif block_symbol == '?':
                        # any block
                        pass
                    elif block_symbol == 'C':
                        # comparator
                        if block['id'] != 'minecraft:unpowered_comparator':
                            return 'Block at {} {} {} should be a comparator, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        known_facings = {
                            (5, -7, 2): 0x2, # south
                            (5, -5, 2): 0x2, # south
                            (7, -3, 4): 0x0, # north
                            (0, -1, 1): 0x0, # north
                            (1, -1, 2): 0x0, # north
                            (2, 0, 2): 0x1 if z % 2 == 0 else 0x3, # east / west
                            (2, 0, 3): 0x2, # south
                            (4, 0, 2): 0x1 if z % 2 == 0 else 0x3, # east / west
                            (4, 0, 3): 0x2 # south
                        }
                        facing = block['damage'] & 0x3
                        if (layer_x, layer_y, layer_z) in known_facings:
                            if known_facings[layer_x, layer_y, layer_z] != facing:
                                return 'Comparator at {} {} {} is facing the wrong way.'.format(exact_x, exact_y, exact_z)
                        else:
                            return 'Direction check for comparator at {} {} {} (relative coords: {} {} {}) not yet implemented.'.format(exact_x, exact_y, exact_z, layer_x, layer_y, layer_z)
                        known_modes = {
                            (5, -7, 2): False, # compare
                            (5, -5, 2): False, # compare
                            (7, -3, 4): False, # compare
                            (0, -1, 1): False, # compare
                            (1, -1, 2): True, # subtract
                            (2, 0, 2): True, # subtract
                            (2, 0, 3): False, # compare
                            (4, 0, 2): True, #subtract
                            (4, 0, 3): False # compare
                        }
                        mode = (block['damage'] & 0x4) == 0x4
                        if (layer_x, layer_y, layer_z) in known_modes:
                            if known_modes[layer_x, layer_y, layer_z] != mode:
                                return 'Comparator at {} {} {} is in {} mode, should be in {} mode.'.format(exact_x, exact_y, exact_z, 'subtraction' if mode else 'comparison', 'subtraction' if known_modes[layer_x, layer_y, layer_z] else 'comparison')
                        else:
                            return 'Mode check for comparator at {} {} {} (relative coords: {} {} {}) not yet implemented.'.format(exact_x, exact_y, exact_z, layer_x, layer_y, layer_z)
                    elif block_symbol == 'D':
                        # dropper facing up
                        if block['id'] != 'minecraft:dropper':
                            return 'Block at {} {} {} should be a dropper, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        if block['damage'] & 0x7 != 1: # up
                            return 'Dropper at {} {} {} should be facing up, is {}.'.format(exact_x, exact_y, exact_z, HOPPER_FACINGS[block['damage']])
                        for slot in block['tileEntity']['Items']:
                            if not item.matches_slot(slot):
                                return 'Dropper at {} {} {} contains items of the wrong kind: {}.'.format(exact_x, exact_y, exact_z, alltheitems.item.Item.from_slot(slot, items_data=items_data).link_text())
                    elif block_symbol == 'F':
                        # furnace
                        if layer_y == -6 and layer_x == 0 and z < 2:
                            # the first few chests get ignored because their overflow points in the opposite direction
                            pass #TODO introduce special checks for them
                        elif layer_y == -1 and layer_x == 7 and layer_z == 1 and (z == corridor_length - 1 or z == corridor_length - 2 and z % 2 == 0):
                            # the floor ends with a quartz slab instead of a furnace here
                            if block['id'] != 'minecraft:stone_slab':
                                return 'Block at {} {} {} should be a quartz slab, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                            if block['damage'] & 0x7 != 0x7:
                                slab_variant = {
                                    0: 'stone',
                                    1: 'sandstone',
                                    2: 'fake wood',
                                    3: 'cobblestone',
                                    4: 'brick',
                                    5: 'stone brick',
                                    6: 'Nether brick',
                                    7: 'quartz'
                                }[block['damage'] & 0x7]
                                return 'Block at {} {} {} should be a <a href="/block/minecraft/stone_slab/7">quartz slab</a>, is a <a href="/block/minecraft/stone_slab/{}">{} slab</a>.'.format(exact_x, exact_y, exact_z, block['damage'] & 0x7, slab_variant)
                            if block['damage'] & 0x8 != 0x8:
                                return 'Quartz slab at {} {} {} should be a top slab, is a bottom slab.'.format(exact_x, exact_y, exact_z)
                        elif x == 0 and y == 6 and layer_y == -1 and layer_x == 7:
                            # the central corridor on the 6th floor uses stone bricks instead of furnaces for the floor
                            if block['id'] != 'minecraft:stonebrick':
                                return 'Block at {} {} {} should be stone bricks, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                            if block['damage'] != 0:
                                stonebrick_variant = {
                                    0: 'regular',
                                    1: 'mossy',
                                    2: 'cracked',
                                    3: 'chiseled'
                                }[block['damage']]
                                return 'Block at {} {} {} should be <a href="/block/minecraft/stonebrick/0">regular stone bricks</a>, is <a href="/block/minecraft/stonebrick/{}">{} stone bricks</a>.'.format(exact_x, exact_y, exact_z, block['damage'], stonebrick_variant)
                        else:
                            if block['id'] != 'minecraft:furnace':
                                return 'Block at {} {} {} should be a furnace, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                            known_signals = {
                                (0, -6, 4): 0,
                                (0, -6, 5): 0,
                                (0, -6, 6): 0,
                                (0, -6, 7): 0,
                                (0, -1, 0): 8,
                                (7, -1, 1): 0,
                                (7, -1, 2): 0,
                                (7, -1, 3): 0,
                                (7, -1, 4): 0,
                                (2, 0, 4): 1,
                                (4, 0, 4): 5
                            }
                            signal = alltheitems.item.comparator_signal(block, items_data=items_data)
                            if (layer_x, layer_y, layer_z) in known_signals:
                                if known_signals[layer_x, layer_y, layer_z] != signal:
                                    return 'Furnace at {} {} {} has a fill level of {}, should be {}.'.format(exact_x, exact_y, exact_z, signal, known_signals[layer_x, layer_y, layer_z])
                            else:
                                return 'Fill level check for furnace at {} {} {} (relative coords: {} {} {}) not yet implemented.'.format(exact_x, exact_y, exact_z, layer_x, layer_y, layer_z)
                    elif block_symbol == 'G':
                        # glowstone
                        if block['id'] != 'minecraft:glowstone':
                            return 'Block at {} {} {} should be glowstone, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                    elif block_symbol == 'H':
                        # hopper, any facing
                        if block['id'] != 'minecraft:hopper':
                            return 'Block at {} {} {} should be a hopper, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                    elif block_symbol == 'N':
                        # overflow hopper chain pointing north
                        if y > 1 and (z == 0 or z == 1):
                            if block['id'] == 'minecraft:hopper':
                                if block['damage'] != 2: # north
                                    return 'Overflow hopper at {} {} {} should be pointing north, is {}.'.format(exact_x, exact_y, exact_z, HOPPER_FACINGS[block['damage']])
                            elif block['id'] == 'minecraft:air':
                                pass # also allow air because some overflow hopper chains don't start on the first floor
                            else:
                                return 'Block at {} {} {} should be a hopper, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        else:
                            if block['id'] != 'minecraft:air':
                                return 'Block at {} {} {} should be air, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                    elif block_symbol == 'P':
                        # upside-down oak stairs
                        if block['id'] != 'minecraft:oak_stairs':
                            return 'Block at {} {} {} should be oak stairs, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        if block['damage'] & 0x3 != (0x1 if z % 2 == 0 else 0x0):
                            stairs_facings = {
                                0: 'west',
                                1: 'east',
                                2: 'south',
                                3: 'north'
                            }
                            return 'Stairs at {} {} {} should be facing {}, is {}.'.format(exact_x, exact_y, exact_z, stairs_facings[0x1 if z % 2 == 0 else 0x0], stairs_facings[block['damage'] & 0x3])
                        if block['damage'] & 0x4 != 0x4:
                            return 'Stairs at {} {} {} should be upside-down.'.format(exact_x, exact_y, exact_z)
                    elif block_symbol == 'Q':
                        # quartz top slab
                        if block['id'] != 'minecraft:stone_slab':
                            return 'Block at {} {} {} should be a quartz slab, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        if block['damage'] & 0x7 != 0x7:
                            slab_variant = {
                                0: 'stone',
                                1: 'sandstone',
                                2: 'fake wood',
                                3: 'cobblestone',
                                4: 'brick',
                                5: 'stone brick',
                                6: 'Nether brick',
                                7: 'quartz'
                            }[block['damage'] & 0x7]
                            return 'Block at {} {} {} should be a <a href="/block/minecraft/stone_slab/7">quartz slab</a>, is a <a href="/block/minecraft/stone_slab/{}">{} slab</a>.'.format(exact_x, exact_y, exact_z, block['damage'] & 0x7, slab_variant)
                        if block['damage'] & 0x8 != 0x8:
                            return 'Quartz slab at {} {} {} should be a top slab, is a bottom slab.'.format(exact_x, exact_y, exact_z)
                    elif block_symbol == 'R':
                        # repeater
                        if block['id'] not in ('minecraft:unpowered_repeater', 'minecraft:powered_repeater'):
                            return 'Block at {} {} {} should be a repeater, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        known_facings = {
                            (1, -8, 2): 0x0, # north
                            (3, -8, 3): 0x3 if z % 2 == 0 else 0x1, # west / east
                            (6, -6, 2): 0x0, # north
                            (7, -5, 5): 0x2, # south
                            (3, -3, 1): 0x1 if z % 2 == 0 else 0x3 # east / west
                        }
                        facing = block['damage'] & 0x3
                        if (layer_x, layer_y, layer_z) in known_facings:
                            if known_facings[layer_x, layer_y, layer_z] != facing:
                                return 'Repeater at {} {} {} is facing the wrong way.'.format(exact_x, exact_y, exact_z)
                        else:
                            return 'Direction check for repeater at {} {} {} (relative coords: {} {} {}) not yet implemented.'.format(exact_x, exact_y, exact_z, layer_x, layer_y, layer_z)
                        known_delays = { # in game ticks
                            (1, -8, 2): 4,
                            (3, -8, 3): 2,
                            (6, -6, 2): 2,
                            (7, -5, 5): 2,
                            (3, -3, 1): 2
                        }
                        delay_ticks = 2 * (block['damage'] >> 2) + 2
                        if (layer_x, layer_y, layer_z) in known_delays:
                            if known_delays[layer_x, layer_y, layer_z] != delay_ticks:
                                return 'Repeater at {} {} {} has a delay of {} game tick{}, should be {}.'.format(exact_x, exact_y, exact_z, delay_ticks, '' if delay_ticks == 1 else 's', known_delays[layer_x, layer_y, layer_z])
                        else:
                            return 'Delay check for repeater at {} {} {} (relative coords: {} {} {}) not yet implemented.'.format(exact_x, exact_y, exact_z, layer_x, layer_y, layer_z)
                    elif block_symbol == 'S':
                        # stone top slab
                        if block['id'] != 'minecraft:stone_slab':
                            return 'Block at {} {} {} should be a stone slab, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        if block['damage'] & 0x7 != 0x0:
                            slab_variant = {
                                0: 'stone',
                                1: 'sandstone',
                                2: 'fake wood',
                                3: 'cobblestone',
                                4: 'brick',
                                5: 'stone brick',
                                6: 'Nether brick',
                                7: 'quartz'
                            }[block['damage'] & 0x7]
                            return 'Block at {} {} {} should be a <a href="/block/minecraft/stone_slab/0">stone slab</a>, is a <a href="/block/minecraft/stone_slab/{}">{} slab</a>.'.format(exact_x, exact_y, exact_z, block['damage'] & 0x7, slab_variant)
                        if block['damage'] & 0x8 != 0x8:
                            return 'Quartz slab at {} {} {} should be a top slab.'.format(exact_x, exact_y, exact_z)
                    elif block_symbol == 'T':
                        # redstone torch attached to the side of a block
                        if block['id'] not in ('minecraft:unlit_redstone_torch', 'minecraft:redstone_torch'):
                            return 'Block at {} {} {} should be a redstone torch, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        known_facings = {
                            (3, -8, 1): 1 if z % 2 == 0 else 2, # west / east
                            (2, -7, 1): 3, # north
                            (4, -6, 1): 2 if z % 2 == 0 else 1, # east / west
                            (4, -6, 2): 3, # north
                            (4, -5, 1): 1 if z % 2 == 0 else 2, # west / east
                            (4, -5, 3): 4, # south
                            (7, -5, 3): 3, # north
                            (1, -4, 2): 4, # south
                            (1, -3, 3): 3, # north
                            (1, -1, 4): 4, # south
                            (5, -1, 1): 2 if z % 2 == 0 else 1, # east / west
                            (3, 0, 3): 4 # south
                        }
                        if (layer_x, layer_y, layer_z) in known_facings:
                            if known_facings[layer_x, layer_y, layer_z] != block['damage']:
                                return 'Redstone torch at {} {} {} attached to the block {}, should be attached to the block {}.'.format(exact_x, exact_y, exact_z, TORCH_FACINGS[block['damage']], TORCH_FACINGS[known_facings[layer_x, layer_y, layer_z]])
                        else:
                            return 'Facing check for redstone torch at {} {} {} (relative coords: {} {} {}) not yet implemented.'.format(exact_x, exact_y, exact_z, layer_x, layer_y, layer_z)
                    elif block_symbol == 'W':
                        # back wall
                        if z == corridor_length - 1 or z == corridor_length - 2 and z % 2 == 0:
                            if block['id'] != 'minecraft:stone':
                                return 'Block at {} {} {} should be stone, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                            if block['damage'] != 0:
                                stone_variant = {
                                    0: 'stone',
                                    1: 'granite',
                                    2: 'polished granite',
                                    3: 'diorite',
                                    4: 'polished diorite',
                                    5: 'andesite',
                                    6: 'polished andesite'
                                }[block['damage']]
                                return 'Block at {} {} {} should be <a href="/block/minecraft/stone/0">regular stone</a>, is <a href="/block/minecraft/stone/{}">{}</a>.'.format(exact_x, exact_y, exact_z, block['damage'], stone_variant)
                    elif block_symbol == 'X':
                        # overflow hopper chain pointing down
                        if layer_y < -7 and y < 6 and (z == 4 or z == 5) or layer_y > -7 and y > 1 and (z == 0 or z == 1):
                            if block['id'] == 'minecraft:hopper':
                                if block['damage'] != 0: # down
                                    return 'Overflow hopper at {} {} {} should be pointing down, is {}.'.format(exact_x, exact_y, exact_z, HOPPER_FACINGS[block['damage']])
                            elif block['id'] == 'minecraft:air':
                                pass # also allow air because some overflow hopper chains don't start on the first floor
                            else:
                                return 'Block at {} {} {} should be air or a hopper, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        else:
                            if block['id'] != 'minecraft:air':
                                return 'Block at {} {} {} should be air, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                    elif block_symbol == '^':
                        # hopper facing outward
                        if block['id'] != 'minecraft:hopper':
                            return 'Block at {} {} {} should be a hopper, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        if block['damage'] & 0x7 != (5 if z % 2 == 0 else 4): # east / west
                            return 'Hopper at {} {} {} should be pointing {}, is {}.'.format(exact_x, exact_y, exact_z, 'east' if z % 2 == 0 else 'west', HOPPER_FACINGS[block['damage']])
                        storage_hoppers = {
                            (3, -5, 3),
                            (6, -5, 3),
                            (7, -4, 3),
                            (5, -3, 2),
                            (6, -3, 2)
                        }
                        if (layer_x, layer_y, layer_z) in storage_hoppers:
                            for slot in block['tileEntity']['Items']:
                                if not item.matches_slot(slot):
                                    return 'Storage hopper at {} {} {} contains items of the wrong kind: {}.'.format(exact_x, exact_y, exact_z, alltheitems.item.Item.from_slot(slot, items_data=items_data).link_text())
                    elif block_symbol == 'c':
                        # crafting table
                        if layer_y == -7 and (y == 6 or z < 4 or z < 6 and layer_z > 1):
                            if block['id'] != 'minecraft:stone':
                                return 'Block at {} {} {} should be stone, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                            if block['damage'] != 0:
                                stone_variant = STONE_VARIANTS[block['damage']]
                                return 'Block at {} {} {} should be <a href="/block/minecraft/stone/0">regular stone</a>, is <a href="/block/minecraft/stone/{}">{}</a>.'.format(exact_x, exact_y, exact_z, block['damage'], stone_variant)
                        else:
                            if block['id'] != 'minecraft:crafting_table':
                                return 'Block at {} {} {} should be a crafting table, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                    elif block_symbol == 'i':
                        # torch attached to the top of a block
                        if block['id'] != 'minecraft:torch':
                            return 'Block at {} {} {} should be a torch, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        if block['damage'] != 5: # attached to the block below
                            return 'Torch at {} {} {} should be attached to the block below, is attached to the block {}'.format(exact_x, exact_y, exact_z, TORCH_FACINGS[block['damage']])
                    elif block_symbol == 'p':
                        # oak planks
                        if layer_y == -8 and (y == 6 or z < 4 or z < 6 and layer_z > 1):
                            if block['id'] != 'minecraft:stone':
                                return 'Block at {} {} {} should be stone, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                            if block['damage'] != 0:
                                stone_variant = STONE_VARIANTS[block['damage']]
                                return 'Block at {} {} {} should be <a href="/block/minecraft/stone/0">regular stone</a>, is <a href="/block/minecraft/stone/{}">{}</a>.'.format(exact_x, exact_y, exact_z, block['damage'], stone_variant)
                        else:
                            if block['id'] != 'minecraft:planks':
                                return 'Block at {} {} {} should be oak planks, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                            pass #TODO check material
                    elif block_symbol == 'r':
                        # redstone dust
                        if block['id'] != 'minecraft:redstone_wire':
                            return 'Block at {} {} {} should be redstone, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                    elif block_symbol == 's':
                        # stone
                        if block['id'] != 'minecraft:stone':
                            if exact_y < 5:
                                if block['id'] != 'minecraft:bedrock':
                                    return 'Block at {} {} {} should be stone or bedrock, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                            else:
                                return 'Block at {} {} {} should be stone, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        if block['damage'] != 0:
                            stone_variant = STONE_VARIANTS[block['damage']]
                            return 'Block at {} {} {} should be <a href="/block/minecraft/stone/0">regular stone</a>, is <a href="/block/minecraft/stone/{}">{}</a>.'.format(exact_x, exact_y, exact_z, block['damage'], stone_variant)
                    elif block_symbol == 't':
                        # redstone torch attached to the top of a block
                        if block['id'] not in ('minecraft:unlit_redstone_torch', 'minecraft:redstone_torch'):
                            return 'Block at {} {} {} should be a redstone torch, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        if block['damage'] != 5: # attached to the block below
                            return 'Redstone torch at {} {} {} should be attached to the block below, is attached to the block {}'.format(exact_x, exact_y, exact_z, TORCH_FACINGS[block['damage']])
                    elif block_symbol == 'v':
                        # hopper facing inwards
                        if block['id'] != 'minecraft:hopper':
                            return 'Block at {} {} {} should be a hopper, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        if block['damage'] & 0x7 != (4 if z % 2 == 0 else 5): # west / east
                            return 'Hopper at {} {} {} should be pointing {}, is {}.'.format(exact_x, exact_y, exact_z, 'west' if z % 2 == 0 else 'east', HOPPER_FACINGS[block['damage']])
                        storage_hoppers = {
                            (3, -7, 4),
                            (4, -7, 4),
                            (2, -6, 3)
                        }
                        if (layer_x, layer_y, layer_z) in storage_hoppers:
                            for slot in block['tileEntity']['Items']:
                                if not item.matches_slot(slot):
                                    return 'Storage hopper at {} {} {} contains items of the wrong kind: {}.'.format(exact_x, exact_y, exact_z, alltheitems.item.Item.from_slot(slot, items_data=items_data).link_text())
                    elif block_symbol == 'x':
                        # hopper facing down
                        if block['id'] != 'minecraft:hopper':
                            return 'Block at {} {} {} should be a hopper, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        if block['damage'] & 0x7 != 0: # down
                            return 'Hopper at {} {} {} should be pointing down, is {}.'.format(exact_x, exact_y, exact_z, HOPPER_FACINGS[block['damage']])
                        storage_hoppers = {
                            (5, -1, 2)
                        }
                        if (layer_x, layer_y, layer_z) in storage_hoppers:
                            for slot in block['tileEntity']['Items']:
                                if not item.matches_slot(slot):
                                    return 'Storage hopper at {} {} {} contains items of the wrong kind: {}.'.format(exact_x, exact_y, exact_z, alltheitems.item.Item.from_slot(slot, items_data=items_data).link_text())
                    elif block_symbol == '~':
                        # hopper chain
                        if block['id'] == 'minecraft:hopper':
                            pass #TODO check facing
                            pass #TODO check alignment
                        elif block['id'] == 'minecraft:air':
                            pass #TODO check alignment
                        else:
                            return 'Block at {} {} {} should be a hopper or air, is {}.'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check hopper chain integrity
                    else:
                        return 'Not yet implemented: block at {} {} {} should be {}.'.format(exact_x, exact_y, exact_z, block_symbol)
        # error check: items in storage chests but not in access chest
        access_chest_fill_level = alltheitems.item.comparator_signal(north_half, south_half)
        bottom_dropper_fill_level = alltheitems.item.comparator_signal(block_at(*layer_coords(5, -7, 3), chunk_cache=chunk_cache))
        if access_chest_fill_level < 2 and bottom_dropper_fill_level > 2:
            return 'Access chest is {}empty but there are items stuck in the storage dropper at {} {} {}.'.format('' if access_chest_fill_level == 0 else 'almost ', *layer_coords(5, -7, 3))
    if durability and has_smart_chest:
        # error check: damaged or enchanted tools in storage chests
        storage_containers = set(CONTAINERS) - {(5, 0, 2), (5, 0, 3)}
        for container in storage_containers:
            for slot in block_at(*layer_coords(*container), chunk_cache=chunk_cache)['tileEntity']['Items']:
                if slot.get('Damage', 0) > 0:
                    return 'Item in storage container at {} {} {} is damaged.'.format(*layer_coords(*container))
                if len(slot.get('tag', {}).get('ench', [])) > 0:
                    return 'Item in storage container at {} {} {} is enchanted.'.format(*layer_coords(*container))

def chest_state(coords, item_stub, corridor_length, item_name=None, pre_sorter=None, *, items_data=None, block_at=alltheitems.world.World().block_at, document_root=ati.document_root, chunk_cache=None, cache=None, allow_cache=True):
    if items_data is None:
        with (ati.assets_root / 'json' / 'items.json').open() as items_file:
            items_data = json.load(items_file)
    if chunk_cache is None:
        chunk_cache = {}
    if isinstance(item_stub, str):
        item_stub = {'id': item_stub}
    item = alltheitems.item.Item(item_stub, items_data=items_data)
    if item_name is None:
        item_name = item.info()['name']
    state = None, 'This SmartChest is in perfect state.', None
    x, y, z = coords
    # determine the base coordinate, i.e. the position of the north half of the access chest
    if z % 2 == 0:
        # left wall
        base_x = 15 * x + 2
    else:
        # right wall
        base_x = 15 * x - 3
    base_y = 73 - 10 * y
    base_z = 28 + 10 * y + 4 * (z // 2)

    def layer_coords(layer_x, layer_y, layer_z):
        if z % 2 == 0:
            # left wall
            exact_x = base_x + 5 - layer_x
        else:
            # right wall
            exact_x = base_x - 5 + layer_x
        exact_y = base_y + layer_y
        exact_z = base_z + 3 - layer_z
        return exact_x, exact_y, exact_z

    # does the access chest exist?
    exists = False
    north_half = block_at(base_x, base_y, base_z, chunk_cache=chunk_cache)
    south_half = block_at(base_x, base_y, base_z + 1, chunk_cache=chunk_cache)
    if north_half['id'] != 'minecraft:chest' and south_half['id'] != 'minecraft:chest':
        state = 'gray', 'Access chest does not exist.', None
    elif north_half['id'] != 'minecraft:chest':
        state = 'gray', 'North half of access chest does not exist.', None
    elif south_half['id'] != 'minecraft:chest':
        state = 'gray', 'South half of access chest does not exist.', None
    else:
        exists = True
    # does it have a SmartChest?
    has_smart_chest = False
    missing_droppers = set()
    for dropper_y in range(base_y - 7, base_y):
        dropper = block_at(base_x, dropper_y, base_z, chunk_cache=chunk_cache)
        if dropper['id'] != 'minecraft:dropper':
            missing_droppers.add(dropper_y)
    if len(missing_droppers) == 7:
        if state[0] is None:
            state = 'orange', 'SmartChest droppers do not exist.', None
    elif len(missing_droppers) > 1:
        if state[0] is None:
            state = 'orange', 'SmartChest droppers at y={} do not exist.'.format(', y='.join(str(dropper) for dropper in missing_droppers)), None
    elif len(missing_droppers) == 1:
        if state[0] is None:
            state = 'orange', 'SmartChest dropper at y={} does not exist, is {}.'.format(next(iter(missing_droppers)), block_at(base_x, dropper_y, base_z)['id']), None
    else:
        has_smart_chest = True
    # is it stackable?
    stackable = item.info().get('stackable', True)
    if not stackable and state[0] is None:
        state = 'cyan', "This SmartChest is in perfect state (but the item is not stackable, so it can't be sorted).", None
    # does it have a durability bar?
    durability = 'durability' in item.info()
    # does it have a sorter?
    has_sorter = False
    if item == 'minecraft:crafting_table' or stackable and item.max_stack_size < 64:
        filler_item = alltheitems.item.Item('minecraft:crafting_table', items_data=items_data)
    else:
        filler_item = alltheitems.item.Item('minecraft:ender_pearl', items_data=items_data)
    sorting_hopper = block_at(base_x - 2 if z % 2 == 0 else base_x + 2, base_y - 3, base_z, chunk_cache=chunk_cache)
    if sorting_hopper['id'] != 'minecraft:hopper':
        if state[0] is None:
            state = 'yellow', 'Sorting hopper does not exist, is {}.'.format(sorting_hopper['id']), None
    else:
        for slot in sorting_hopper['tileEntity']['Items']:
            if slot['Slot'] == 0 and stackable and not item.matches_slot(slot) and filler_item.matches_slot(slot):
                if state[0] is None or state[0] == 'cyan':
                    state = 'yellow', 'Sorting hopper is full of {}, but the sorted item is stackable, so the first slot should contain the item.'.format(filler_item.link_text()), None
                break
        else:
            has_sorter = True
    # does it have an overflow?
    has_overflow = False
    missing_overflow_hoppers = set()
    for overflow_x in range(base_x + 3 if z % 2 == 0 else base_x - 3, base_x + 6 if z % 2 == 0 else base_x - 6, 1 if z % 2 == 0 else -1):
        overflow_hopper = block_at(overflow_x, base_y - 7, base_z - 1, chunk_cache=chunk_cache)
        if overflow_hopper['id'] != 'minecraft:hopper':
            missing_overflow_hoppers.add(overflow_x)
    if len(missing_overflow_hoppers) == 0:
        has_overflow = True
    # state determined, check for errors
    if coords == (1, 1, 0): # Ender pearls
        message = global_error_checks(chunk_cache=chunk_cache, block_at=block_at)
        if message is not None:
            return 'red', message, None
    cache_path = ati.cache_root / 'cloud-chests.json'
    if cache is None:
        if cache_path.exists():
            with cache_path.open() as cache_f:
                cache = json.load(cache_f)
        else:
            cache = {}
    max_age = datetime.timedelta(hours=1, minutes=random.randrange(0, 60)) # use a random value between 1 and 2 hours for the cache expiration
    if allow_cache and str(y) in cache and str(x) in cache[str(y)] and str(z) in cache[str(y)][str(x)] and cache[str(y)][str(x)][str(z)]['errorMessage'] is None and datetime.datetime.strptime(cache[str(y)][str(x)][str(z)]['timestamp'], '%Y-%m-%d %H:%M:%S') > datetime.datetime.utcnow() - max_age:
        message = cache[str(y)][str(x)][str(z)]['errorMessage']
        pass # cached check results are recent enough
    else:
        # cached check results are too old, recheck
        message = chest_error_checks(x, y, z, base_x, base_y, base_z, item, item_name, exists, stackable, durability, has_smart_chest, has_sorter, has_overflow, filler_item, sorting_hopper, missing_overflow_hoppers, north_half, south_half, corridor_length, pre_sorter, layer_coords, block_at, items_data, chunk_cache, document_root)
        if ati.cache_root.exists():
            if str(y) not in cache:
                cache[str(y)] = {}
            if str(x) not in cache[str(y)]:
                cache[str(y)][str(x)] = {}
            cache[str(y)][str(x)][str(z)] = {
                'errorMessage': message,
                'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }
            with cache_path.open('w') as cache_f:
                json.dump(cache, cache_f, sort_keys=True, indent=4)
    if message is not None:
        return 'red', message, None
    # no errors, determine fill level
    if state[0] in (None, 'cyan', 'orange', 'yellow'):
        try:
            containers = CONTAINERS if state[0] in (None, 'cyan') else [ # layer coords of the access chest
                (5, 0, 2),
                (5, 0, 3)
            ]
            total_items = sum(max(0, sum(slot['Count'] for slot in block_at(*layer_coords(*container), chunk_cache=chunk_cache)['tileEntity']['Items'] if slot.get('Damage', 0) == 0 or not durability) - (4 * item.max_stack_size if container == (5, -7, 3) else 0)) for container in containers) # Don't count the 4 stacks of items that are stuck in the bottom dropper. Don't count damaged tools.
            max_slots = sum(alltheitems.item.NUM_SLOTS[block_at(*layer_coords(*container), chunk_cache=chunk_cache)['id']] for container in containers) - (0 if state[0] == 'orange' else 4)
            return state[0], state[1], FillLevel(item.max_stack_size, total_items, max_slots, is_smart_chest=state[0] in (None, 'cyan'))
        except:
            # something went wrong determining fill level, re-check errors
            message = chest_error_checks(x, y, z, base_x, base_y, base_z, item, item_name, exists, stackable, durability, has_smart_chest, has_sorter, has_overflow, filler_item, sorting_hopper, missing_overflow_hoppers, north_half, south_half, corridor_length, g, layer_coords, block_at, items_data, chunk_cache, document_root)
            if ati.cache_root.exists():
                if str(y) not in cache:
                    cache[str(y)] = {}
                if str(x) not in cache[str(y)]:
                    cache[str(y)][str(x)] = {}
                cache[str(y)][str(x)][str(z)] = {
                    'errorMessage': message,
                    'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                }
                with cache_path.open('w') as cache_f:
                    json.dump(cache, cache_f, sort_keys=True, indent=4)
            if message is None:
                raise
            else:
                return 'red', message, None
    return state

def cell_from_chest(coords, item_stub, corridor_length, item_name=None, pre_sorter=None, *, chunk_cache=None, items_data=None, colors_to_explain=None, cache=None, allow_cache=True):
    color, state_message, fill_level = chest_state(coords, item_stub, corridor_length, item_name, pre_sorter, items_data=items_data, chunk_cache=chunk_cache, cache=cache, allow_cache=allow_cache)
    if colors_to_explain is not None:
        colors_to_explain.add(color)
    if fill_level is None or fill_level.is_full():
        return '<td style="background-color: {};">{}</td>'.format(HTML_COLORS[color], alltheitems.item.Item(item_stub, items_data=items_data).image())
    else:
        return '<td style="background-color: {};">{}<div class="durability"><div style="background-color: #f0f; width: {}px;"></div></div></td>'.format(HTML_COLORS[color], alltheitems.item.Item(item_stub, items_data=items_data).image(), 0 if fill_level.is_empty() else 2 + int(fill_level.fraction * 13) * 2)

def index(allow_cache=True):
    yield ati.header(title='Cloud')
    def body():
        yield '<p>The <a href="//wiki.{host}/Cloud">Cloud</a> is the public item storage on <a href="//{host}/">Wurstmineberg</a>, consisting of 6 underground floors with <a href="//wiki.{host}/SmartChest">SmartChests</a> in them.</p>'.format(host=ati.host)
        yield """<style type="text/css">
            .item-table td {
                box-sizing: content-box;
                height: 32px;
                width: 32px;
                position: relative;
            }

            .item-table .left-sep {
                border-left: 1px solid gray;
            }

            .durability {
                z-index: 1;
            }
        </style>"""
        chunk_cache = {}
        with (ati.assets_root / 'json' / 'items.json').open() as items_file:
            items_data = json.load(items_file)
        cache_path = ati.cache_root / 'cloud-chests.json'
        if cache_path.exists():
            try:
                with cache_path.open() as cache_f:
                    cache = json.load(cache_f)
            except ValueError:
                # cache JSON is corrupted, probably because of a full disk, try without cache
                cache_path.unlink()
                cache = None
        else:
            cache = None
        colors_to_explain = set()
        floors = {}
        for x, corridor, y, floor, z, chest in chest_iter():
            if y not in floors:
                floors[y] = floor
        for y, floor in sorted(floors.items(), key=lambda tup: tup[0]):
            def cell(coords, item_stub, corridor):
                if isinstance(item_stub, str):
                    item_stub = {'id': item_stub}
                    item_name = None
                    pre_sorter = None
                else:
                    item_stub = item_stub.copy()
                    if 'name' in item_stub:
                        item_name = item_stub['name']
                        del item_stub['name']
                    else:
                        item_name = None
                    if 'sorter' in item_stub:
                        pre_sorter = item_stub['sorter']
                        del item_stub['sorter']
                    else:
                        pre_sorter = None
                return cell_from_chest(coords, item_stub, len(corridor), item_name, pre_sorter, chunk_cache=chunk_cache, colors_to_explain=colors_to_explain, items_data=items_data, cache=cache, allow_cache=allow_cache)

            yield bottle.template("""
                %import itertools
                <h2 id="floor{{y}}">{{y}}{{ordinal(y)}} floor (y={{73 - 10 * y}})</h2>
                <table class="item-table" style="margin-left: auto; margin-right: auto;">
                    %for x in range(-3, 4):
                        %if x > -3:
                            <colgroup class="left-sep">
                                <col />
                                <col />
                            </colgroup>
                        %else:
                            <colgroup>
                                <col />
                                <col />
                            </colgroup>
                        %end
                    %end
                    <tbody>
                        %for z_left, z_right in zip(itertools.count(step=2), itertools.count(start=1, step=2)):
                            %found = False
                            <tr>
                                %for x in range(-3, 4):
                                    %if str(x) not in floor:
                                        <td></td>
                                        <td></td>
                                        %continue
                                    %end
                                    %corridor = floor[str(x)]
                                    %if len(corridor) > z_right:
                                        {{!cell((x, y, z_right), corridor[z_right], corridor)}}
                                    %else:
                                        <td></td>
                                    %end
                                    %if len(corridor) > z_left:
                                        {{!cell((x, y, z_left), corridor[z_left], corridor)}}
                                        %found = True
                                    %else:
                                        <td></td>
                                    %end
                                %end
                            </tr>
                            %if not found:
                                %break
                            %end
                        %end
                    </tbody>
                </table>
            """, ordinal=alltheitems.util.ordinal, cell=cell, floor=floor, y=y)
        color_explanations = collections.OrderedDict([
            ('red', '<p>A red background means that there is something wrong with the chest. See the item info page for details.</p>'),
            ('gray', "<p>A gray background means that the chest hasn't been built yet or is still located somewhere else.</p>"),
            ('orange', "<p>An orange background means that the chest doesn't have a SmartChest yet. It can only store 54 stacks.</p>"),
            ('yellow', "<p>A yellow background means that the chest doesn't have a sorter yet.</p>"),
            ('cyan', '<p>A cyan background means that the chest has no sorter because it stores an unstackable item. These items should not be automatically <a href="//wiki.wurstmineberg.de/Soup#Cloud">sent</a> to the Cloud.</p>'),
            (None, '<p>A white background means that everything is okay: the chest has a SmartChest, a sorter, and overflow protection.</p>')
        ])
        for chest_color in sorted(colors_to_explain, key=list(color_explanations.keys()).index):
            if chest_color is not None or len(colors_to_explain) > 1:
                yield color_explanations[chest_color]
    yield from ati.html_exceptions(body())
    yield ati.footer(linkify_headers=True)

def todo():
    yield ati.header(title='Cloud by priority')
    def body():
        yield """<style type="text/css">
            .todo-table td {
                text-align: left;
                vertical-align: middle !important;
            }

            .todo-table .coord {
                width: 3em;
                text-align: right;
            }

            .todo-table .item-image {
                box-sizing: content-box;
                width: 32px;
            }

            .todo-table .item-name {
                width: 24em;
            }
        </style>"""

        headers = collections.OrderedDict([
            ('red', 'Build errors'),
            ('gray', 'Missing chests'),
            ('orange', 'Missing SmartChests'),
            ('yellow', 'Missing sorters'),
            ('cyan', 'Empty SmartChests (unstackable)'),
            ('white', 'Empty SmartChests (stackable)'),
            ('cyan2', 'Missing items (unstackable)'),
            ('white2', 'Missing items (stackable)')
        ])
        header_indexes = {color: i for i, color in enumerate(headers.keys())}

        def priority(pair):
            coords, state = pair
            x, y, z = coords
            color, _, fill_level, _ = state
            return header_indexes[color], None if fill_level is None else fill_level.fraction * (-1 if color == 'orange' else 1), y * (-1 if color == 'orange' else 1), x if y % 2 == 0 else -x, z

        chunk_cache = {}
        with (ati.assets_root / 'json' / 'items.json').open() as items_file:
            items_data = json.load(items_file)
        cache_path = ati.cache_root / 'cloud-chests.json'
        if cache_path.exists():
            try:
                with cache_path.open() as cache_f:
                    cache = json.load(cache_f)
            except ValueError:
                # cache JSON is corrupted, probably because of a full disk, try without cache
                cache_path.unlink()
                cache = None
        else:
            cache = None
        states = {}
        current_color = None
        for x, corridor, y, _, z, item_stub in chest_iter():
            if isinstance(item_stub, str):
                item_stub = {'id': item_stub}
                item_name = None
                pre_sorter = None
            else:
                item_stub = item_stub.copy()
                if 'name' in item_stub:
                    item_name = item_stub['name']
                    del item_stub['name']
                else:
                    item_name = None
                if 'sorter' in item_stub:
                    pre_sorter = item_stub['sorter']
                    del item_stub['sorter']
                else:
                    pre_sorter = None
            color, state_message, fill_level = chest_state((x, y, z), item_stub, len(corridor), item_name, pre_sorter, items_data=items_data, chunk_cache=chunk_cache, cache=cache)
            if color is None:
                color = 'white'
            if color in ('cyan', 'white') and not fill_level.is_empty():
                color += '2'
            if fill_level is None or not fill_level.is_full() or color not in ('cyan', 'white', 'cyan2', 'white2'):
                states[x, y, z] = color, state_message, fill_level, alltheitems.item.Item(item_stub, items_data=items_data)
        for coords, state in sorted(states.items(), key=priority):
            x, y, z = coords
            color, state_message, fill_level, item = state
            if color != current_color:
                if current_color is not None:
                    yield '</tbody></table>'
                yield bottle.template('<h2 id="{{color}}">{{header}}</h2>', color=color, header=headers[color])
                yield '<table class="todo-table table table-responsive"><thead><tr><th class="coord">X</th><th class="coord">Y</th><th class="coord">Z</th><th class="item-image">&nbsp;</th><th class="item-name">Item</th><th>{}</th></tr></thead><tbody>'.format('Fill Level' if color in ('cyan', 'white', 'cyan2', 'white2') else 'Info')
                current_color = color
            yield bottle.template("""
                <tr>
                    <td class="coord">{{x}}</td>
                    <td class="coord">{{y}}</td>
                    <td class="coord">{{z}}</td>
                    <td class="item-image">{{!item.image()}}</td>
                    <td class="item-name">{{!item.link_text()}}</td>
                    <td style="background-color: {{color}}">{{!fill_level if color in ('#0ff', '#fff') else state_message}}</td>
                </tr>
            """, x=x, y=y, z=z, item=item, color=HTML_COLORS[color], fill_level=fill_level, state_message=state_message)
        yield '</tbody></table>'
    yield from ati.html_exceptions(body())
    yield ati.footer(linkify_headers=True)
