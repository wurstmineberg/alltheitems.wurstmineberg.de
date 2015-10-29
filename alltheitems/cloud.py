import alltheitems.__main__ as ati

import bottle
import contextlib
import itertools
import json
import pathlib
import re

import alltheitems.item
import alltheitems.world

def hopper_chain_connected(start_coords, end_coords, *, world=None, chunk_cache=None):
    if world is None:
        world = alltheitems.world.World()
    if chunk_cache is None:
        chunk_cache = {}
    visited_coords = set()
    x, y, z = start_coords
    while (x, y, z) != end_coords:
        if (x, y, z) in visited_coords:
            return False, 'hopper chain points into itself at {} {} {}'.format(x, y, z)
        visited_coords.add((x, y, z))
        block = world.block_at(x, y, z, chunk_cache=chunk_cache)
        if block['id'] != 'minecraft:hopper':
            return False, 'block at {} {} {} is not a hopper'.format(x, y, z)
        if block['damage'] == 0:
            y -= 1 # down
        elif block['damage'] == 2:
            z -= 1 # north
        elif block['damage'] == 3:
            z += 1 # south
        elif block['damage'] == 4:
            x -= 1 # west
        elif block['damage'] == 5:
            x += 1 # east
        else:
            raise ValueError('Unknown hopper facing {} at {}'.format(block['damage'], (x, y, z)))
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

def chest_coords(item):
    if not isinstance(item, alltheitems.item.Item):
        item = alltheitems.item.Item(item)
    for x, _, y, _, z, chest in chest_iter():
        if item == chest:
            return x, y, z

def chest_state(coords, item_stub, *, items_data=None, block_at=alltheitems.world.World().block_at, document_root=ati.document_root, chunk_cache=None):
    if items_data is None:
        with (ati.assets_root / 'json' / 'items.json').open() as items_file:
            items_data = json.load(items_file)
    if chunk_cache is None:
        chunk_cache = {}
    if isinstance(item_stub, str):
        item_stub = {'id': item_stub}
    if 'name' in item_stub:
        item_name = item_stub['name']
        del item_stub['name']
    else:
        item_name = alltheitems.item.Item(item_stub).info()['name']
    item = alltheitems.item.Item(item_stub)
    state = None, 'Fill level info coming <a href="http://wiki.{{host}}/Soon™">soon™</a>.'
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
    # does the access chest exist?
    exists = False
    north_half = block_at(base_x, base_y, base_z, chunk_cache=chunk_cache)
    south_half = block_at(base_x, base_y, base_z + 1, chunk_cache=chunk_cache)
    if north_half['id'] != 'minecraft:chest' and south_half['id'] != 'minecraft:chest':
        state = 'gray', 'Access chest does not exist'
    elif north_half['id'] != 'minecraft:chest':
        state = 'gray', 'North half of access chest does not exist'
    elif south_half['id'] != 'minecraft:chest':
        state = 'gray', 'South half of access chest does not exist'
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
            state = 'orange', 'SmartChest droppers do not exist'
    elif len(missing_droppers) > 1:
        if state[0] is None:
            state = 'orange', 'SmartChest droppers at y={} do not exist'.format(missing_droppers)
    elif len(missing_droppers) == 1:
        if state[0] is None:
            state = 'orange', 'SmartChest dropper at y={} does not exist'.format(next(iter(missing_droppers)))
    else:
        has_smart_chest = True
    # is it stackable?
    stackable = item.info().get('stackable', True)
    if not stackable and state[0] is None:
        state = 'cyan', state[1]
    # does it have a sorter?
    has_sorter = False
    sorting_hopper = block_at(base_x - 2 if z % 2 == 0 else base_x + 2, base_y - 3, base_z, chunk_cache=chunk_cache)
    if sorting_hopper['id'] != 'minecraft:hopper':
        if state[0] is None:
            state = 'yellow', 'Sorting hopper does not exist'
    else:
        for slot in sorting_hopper['tileEntity']['Items']:
            if slot['Slot'] == 0 and stackable and not item.matches_slot(slot) and alltheitems.item.Item('minecraft:ender_pearl').matches_slot(slot):
                if state[0] is None or state[0] == 'cyan':
                    state = 'yellow', 'Sorting hopper is full of Ender pearls, but the item is stackable'
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
    if stackable and has_sorter:
        # error check: overflow exists
        if not has_overflow:
            if len(missing_overflow_hoppers) == 3:
                return 'red', 'Missing overflow'
            elif len(missing_overflow_hoppers) > 1:
                return 'red', 'Overflow hoppers at x={} do not exist'.format(missing_overflow_hoppers)
            elif len(missing_overflow_hoppers) == 1:
                return 'red', 'Overflow hoppers at y={} does not exist'.format(next(iter(missing_overflow_hoppers)))
            else:
                return 'red', 'Missing overflow'
    if exists:
        # error check: wrong items in access chest
        found_matching = False
        found_non_matching = False
        for slot in itertools.chain(north_half['tileEntity']['Items'], south_half['tileEntity']['Items']):
            if not item.matches_slot(slot):
                return 'red', 'Access chest contains items of the wrong kind'
        # error check: wrong name on sign
        sign = block_at(base_x - 1 if z % 2 == 0 else base_x + 1, base_y + 1, base_z + 1, chunk_cache=chunk_cache)
        if sign['id'] != 'minecraft:wall_sign':
            return 'red', 'Sign is missing'
        text = []
        for line in range(1, 5):
            line_text = json.loads(sign['tileEntity']['Text{}'.format(line)])['text'].translate(dict.fromkeys(range(0xf700, 0xf704), None))
            if len(line_text) > 0:
                text.append(line_text)
        text = ' '.join(text)
        if text != item_name:
            return 'red', 'Sign has wrong text: should be {!r}, is {!r}'.format(item_name, text)
    if has_sorter:
        # error check: sorting hopper
        if sorting_hopper['damage'] != 2:
            facings = {
                0: 'down',
                2: 'north',
                3: 'south',
                4: 'west',
                5: 'east'
            }
            return 'red', 'Sorting hopper ({} {} {}) should be facing north (2), but is facing {} ({})'.format(base_x - 2 if z % 2 == 0 else base_x + 2, base_y - 3, base_z, facings[sorting_hopper['damage']], sorting_hopper['damage'])
        empty_slots = set(range(5))
        for slot in sorting_hopper['tileEntity']['Items']:
            empty_slots.remove(slot['Slot'])
            if slot['Slot'] == 0 and stackable:
                if not item.matches_slot(slot) and not alltheitems.item.Item('minecraft:ender_pearl').matches_slot(slot):
                    return 'red', 'Sorting hopper is sorting the wrong item: {}'.format(slot)
            else:
                if not alltheitems.item.Item('minecraft:ender_pearl').matches_slot(slot):
                    return 'red', 'Sorting hopper has wrong filler item in slot {}: {} (should be an Ender pearl)'.format(slot['Slot'], slot)
            if alltheitems.item.Item('minecraft:ender_pearl').matches_slot(slot) and slot['Count'] > 1:
                return 'red', 'Too many Ender pearls in slot {}'.format(slot['Slot'])
        if len(empty_slots) > 0:
            if len(empty_slots) == 5:
                return 'red', 'Sorting hopper is empty'
            elif len(empty_slots) == 1:
                return 'red', 'Slot {} of the sorting hopper is empty'.format(next(iter(empty_slots)))
            else:
                return 'red', 'Some slots in the sorting hopper are empty: {}'.format(empty_slots)
    if has_overflow:
        # error check: overflow hopper chain
        is_connected, message = hopper_chain_connected((base_x + 5 if z % 2 == 0 else base_x - 5, base_y - 7, base_z - 1), (-35, 6, 38), chunk_cache=chunk_cache)
        if not is_connected:
            return 'red', 'Overflow hopper chain is not connected to the Smelting Center item elevator: {}'.format(message)
    if exists and has_smart_chest and has_sorter and has_overflow:
        # error check: all blocks
        for layer_y, layer in smart_chest_schematic(document_root=document_root):
            for layer_x, row in enumerate(layer):
                for layer_z, block_symbol in enumerate(row):
                    # determine the coordinate of the current block
                    if z % 2 == 0:
                        # left wall
                        exact_x = base_x + 5 - layer_x
                    else:
                        # right wall
                        exact_x = base_x - 5 + layer_x
                    exact_y = base_y + layer_y
                    exact_z = base_z + 3 - layer_z
                    # determine current block
                    block = block_at(exact_x, exact_y, exact_z, chunk_cache=chunk_cache)
                    # check against schematic
                    if block_symbol == ' ':
                        # air
                        if (z == 4 or z == 5) and layer_x == 0 and layer_y == -8 and layer_z == 2:
                            # overflow hopper chain pointing down
                            if block['id'] != 'minecraft:hopper':
                                return 'red', 'Block at {} {} {} should be a hopper, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                            pass #TODO check facing
                        else:
                            if block['id'] != 'minecraft:air':
                                return 'red', 'Block at {} {} {} should be air, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                    elif block_symbol == '!':
                        # sign
                        if block['id'] != 'minecraft:wall_sign':
                            return 'red', 'Block at {} {} {} should be a sign, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check facing
                        pass #TODO check contents
                    elif block_symbol == '#':
                        # chest
                        if block['id'] != 'minecraft:chest':
                            return 'red', 'Block at {} {} {} should be a chest, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check contents
                    elif block_symbol == '<':
                        # hopper facing south
                        if block['id'] != 'minecraft:hopper':
                            return 'red', 'Block at {} {} {} should be a hopper, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check facing
                        pass #TODO check contents
                    elif block_symbol == '>':
                        # hopper facing north
                        if layer_y == -7 and layer_x == 0 and z < 8:
                            # the first few chests get ignored because their overflow points in the opposite direction
                            pass #TODO introduce special checks for them
                        else:
                            if block['id'] != 'minecraft:hopper':
                                return 'red', 'Block at {} {} {} should be a hopper, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                            pass #TODO check facing
                            pass #TODO check contents
                    elif block_symbol == '?':
                        # any block
                        pass
                    elif block_symbol == 'C':
                        # comparator
                        if block['id'] != 'minecraft:unpowered_comparator':
                            return 'red', 'Block at {} {} {} should be a comparator, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check direction and mode
                    elif block_symbol == 'D':
                        # dropper facing up
                        if block['id'] != 'minecraft:dropper':
                            return 'red', 'Block at {} {} {} should be a dropper, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check facing
                        pass #TODO check contents
                    elif block_symbol == 'F':
                        # furnace
                        if layer_y == -6 and layer_x == 0 and z < 2:
                            # the first few chests get ignored because their overflow points in the opposite direction
                            pass #TODO introduce special checks for them
                        else:
                            if block['id'] != 'minecraft:furnace':
                                return 'red', 'Block at {} {} {} should be a furnace, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                            pass #TODO check signal
                    elif block_symbol == 'G':
                        # glowstone
                        if block['id'] != 'minecraft:glowstone':
                            return 'red', 'Block at {} {} {} should be glowstone, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                    elif block_symbol == 'P':
                        # upside-down oak stairs
                        if block['id'] != 'minecraft:oak_stairs':
                            return 'red', 'Block at {} {} {} should be oak stairs, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check facing
                    elif block_symbol == 'Q':
                        # quartz top slab
                        if block['id'] != 'minecraft:stone_slab':
                            return 'red', 'Block at {} {} {} should be a quartz slab, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check facing
                        pass #TODO check material
                    elif block_symbol == 'R':
                        # repeater
                        if block['id'] not in ('minecraft:unpowered_repeater', 'minecraft:powered_repeater'):
                            return 'red', 'Block at {} {} {} should be a repeater, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check facing
                        pass #TODO check delay
                    elif block_symbol == 'S':
                        # stone top slab
                        if block['id'] != 'minecraft:stone_slab':
                            return 'red', 'Block at {} {} {} should be a stone slab, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check facing
                        pass #TODO check material
                    elif block_symbol == 'T':
                        # redstone torch attached to the side of a block
                        if block['id'] not in ('minecraft:unlit_redstone_torch', 'minecraft:redstone_torch'):
                            return 'red', 'Block at {} {} {} should be a redstone torch, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check facing
                    elif block_symbol == '^':
                        # hopper facing outward
                        if block['id'] != 'minecraft:hopper':
                            return 'red', 'Block at {} {} {} should be a hopper, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check facing
                        pass #TODO check contents
                    elif block_symbol == 'c':
                        # crafting table
                        if layer_y == -7 and (z < 4 or z < 6 and layer_z > 1):
                            if block['id'] != 'minecraft:stone':
                                return 'red', 'Block at {} {} {} should be stone, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                            pass #TODO check damage
                        else:
                            if block['id'] != 'minecraft:crafting_table':
                                return 'red', 'Block at {} {} {} should be a crafting table, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                    elif block_symbol == 'i':
                        # torch attached to the top of a block
                        if block['id'] != 'minecraft:torch':
                            return 'red', 'Block at {} {} {} should be a torch, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check facing
                    elif block_symbol == 'p':
                        # oak planks
                        if layer_y == -8 and (z < 4 or z < 6 and layer_z > 1):
                            if block['id'] != 'minecraft:stone':
                                return 'red', 'Block at {} {} {} should be stone, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                            pass #TODO check damage
                        else:
                            if block['id'] != 'minecraft:planks':
                                return 'red', 'Block at {} {} {} should be oak planks, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                            pass #TODO check material
                    elif block_symbol == 'r':
                        # redstone dust
                        if block['id'] != 'minecraft:redstone_wire':
                            return 'red', 'Block at {} {} {} should be redstone, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                    elif block_symbol == 's':
                        # stone
                        if block['id'] != 'minecraft:stone':
                            return 'red', 'Block at {} {} {} should be stone, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check damage
                    elif block_symbol == 't':
                        # redstone torch attached to the top of a block
                        if block['id'] not in ('minecraft:unlit_redstone_torch', 'minecraft:redstone_torch'):
                            return 'red', 'Block at {} {} {} should be a redstone torch, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check facing
                    elif block_symbol == 'v':
                        # hopper facing inwards
                        if block['id'] != 'minecraft:hopper':
                            return 'red', 'Block at {} {} {} should be a hopper, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check facing
                        pass #TODO check contents
                    elif block_symbol == 'x':
                        # hopper facing down
                        if block['id'] != 'minecraft:hopper':
                            return 'red', 'Block at {} {} {} should be a hopper, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check facing
                        pass #TODO check contents
                    elif block_symbol == '~':
                        # hopper chain
                        if block['id'] == 'minecraft:hopper':
                            pass #TODO check facing
                            pass #TODO check alignment
                        elif block['id'] == 'minecraft:air':
                            pass #TODO check alignment
                        else:
                            return 'red', 'Block at {} {} {} should be a hopper or air, is {}'.format(exact_x, exact_y, exact_z, block['id'])
                        pass #TODO check hopper chain integrity
                    else:
                        return 'red', 'Not yet implemented: block at {} {} {} should be {}'.format(exact_x, exact_y, exact_z, block_symbol)
    return state

def chest_background_color(coords, item_stub, *, items_data=None, chunk_cache=None, colors_to_explain=colors_to_explain):
    color = {
        'cyan': '#0ff',
        'gray': '#777',
        'red': '#f00',
        'orange': '#f70',
        'yellow': '#ff0',
        None: 'transparent'
    }[chest_state(coords, item_stub, items_data=items_data, chunk_cache=chunk_cache)[0]]
    if colors_to_explain is not None:
        colors_to_explain.add(color)
    return color

def image_from_chest(coords, cloud_chest, *, chunk_cache=None, colors_to_explain=colors_to_explain):
    return '<td style="background-color: {};">{}</td>'.format(chest_background_color(coords, cloud_chest, chunk_cache=chunk_cache, colors_to_explain=colors_to_explain), alltheitems.item.Item(cloud_chest).image())

def index():
    yield ati.header(title='Cloud')
    def body():
        chunk_cache = {}
        yield '<p>The <a href="http://wiki.{host}/Cloud">Cloud</a> is the public item storage on <a href="http://{host}/">Wurstmineberg</a>, consisting of 6 underground floors with <a href="http://wiki.{host}/SmartChest">SmartChests</a> in them.</p>'.format(host=ati.host)
        yield """<style type="text/css">
            .item-table td {
                box-sizing: content-box;
                height: 32px;
                width: 32px;
            }

            .item-table .left-sep {
                border-left: 1px solid gray;
            }
        </style>"""
        colors_to_explain = set()
        floors = {}
        for x, corridor, y, floor, z, chest in chest_iter():
            if y not in floors:
                floors[y] = floor
        for y, floor in sorted(floors.items(), key=lambda tup: tup[0]):
            yield bottle.template("""
                %import itertools
                <h2 id="floor{{y}}">{{y}}{{ati.ordinal(y)}} floor (y={{73 - 10 * y}})</h2>
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
                                        {{!image((x, y, z_right), corridor[z_right], chunk_cache=chunk_cache, colors_to_explain=colors_to_explain)}}
                                    %else:
                                        <td></td>
                                    %end
                                    %if len(corridor) > z_left:
                                        {{!image((x, y, z_left), corridor[z_left], chunk_cache=chunk_cache, colors_to_explain=colors_to_explain)}}
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
            """, ati=ati, image=image_from_chest, floor=floor, y=y, chunk_cache=chunk_cache, colors_to_explain=colors_to_explain)
        color_explanations = {
            '#f00': '<p>A red background means that there is something wrong with the chest. See the item info page for details.</p>',
            '#777': "<p>A gray background means that the chest hasn't been built yet or is still located somewhere else.</p>",
            '#f70': "<p>An orange background means that the chest doesn't have a SmartChest yet. It can only store 54 stacks.</p>",
            '#0ff': '<p>A cyan background means that the chest has no sorter because it stores an unstackable item. These items should not be automatically <a href="http://wiki.wurstmineberg.de/Soup#Cloud">sent</a> to the Cloud.</p>',
            '#ff0': "<p>A yellow background means that the chest doesn't have a sorter yet.</p>",
            'transparent': '<p>A white background means that everything is okay: the chest has a SmartChest, a sorter, and overflow protection.</p>'
        }
        for color in colors_to_explain:
            if chest_color != 'transparent':
                yield color_explanations[chest_color]
        if 'transparent' in colors_to_explain and len(colors_to_explain) > 1:
            yield color_explanations['transparent']
    yield from ati.html_exceptions(body())
    yield ati.footer(linkify_headers=True)
