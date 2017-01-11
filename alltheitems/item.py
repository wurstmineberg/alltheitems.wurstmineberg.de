import alltheitems.__main__ as ati

import enum
import functools
import json
import re
import xml.sax.saxutils

import alltheitems.util

NUM_SLOTS = {
    'minecraft:furnace': 3,
    'minecraft:lit_furnace': 3,
    'minecraft:hopper': 5,
    'minecraft:brewing_stand': 5,
    'minecraft:dispenser': 9,
    'minecraft:dropper': 9,
    'minecraft:chest': 27,
    'minecraft:trapped_chest': 27
}

@enum.unique
class Renewability(alltheitems.util.OrderedEnum):
    unobtainable = 0
    obtainable = 1
    infinite = 2
    renewable = 3
    automatic = 4
    fully_automatic = 5

@functools.total_ordering
class Item:
    def __init__(self, item_stub, *, items_data=None):
        if isinstance(item_stub, Item):
            self.stub = item_stub.stub
        elif isinstance(item_stub, str):
            self.stub = {'id': item_stub}
        elif isinstance(item_stub, dict):
            if 'id' not in item_stub:
                raise ValueError('Missing item ID')
            self.stub = item_stub
        else:
            raise TypeError('Cannot create an item from {}'.format(type(item_stub)))
        allowed_keys = {
            'id',
            'damage',
            'effect',
            'tagValue',
            'consumed',
            'amount'
        }
        self.stub = {key: value for key, value in self.stub.items() if key in allowed_keys}
        if 'tagValue' in self.stub and self.stub['tagValue'] is not None:
            self.stub['tagValue'] = str(self.stub['tagValue'])
        if items_data is None and isinstance(item_stub, Item) and item_stub.items_data is not None:
            self.items_data = item_stub.items_data
        elif items_data is None:
            with (ati.assets_root / 'json' / 'items.json').open() as items_file:
                self.items_data = json.load(items_file)
        else:
            self.items_data = items_data

    def __eq__(self, other):
        if not isinstance(other, Item):
            try:
                other = Item(other)
            except TypeError:
                return False
        if self.stub['id'] != other.stub['id']:
            return False
        for attr in ('damage', 'effect', 'tagValue'):
            if attr in self.stub:
                if attr not in other.stub:
                    return False
                if self.stub[attr] != other.stub[attr]:
                    return False
            else:
                if attr in other.stub:
                    return False
        return True

    def __hash__(self):
        return hash(self.stub['id'])

    def __lt__(self, other):
        if not isinstance(other, Item):
            try:
                other = Item(other)
            except TypeError:
                return NotImplemented
        if self.stub['id'] < other.stub['id']:
            return True
        if self.stub['id'] > other.stub['id']:
            return False
        for attr in ('damage', 'effect', 'tagValue'):
            if attr in self.stub:
                if attr not in other.stub:
                    return False
                if self.stub[attr] < other.stub[attr]:
                    return True
                if self.stub[attr] > other.stub[attr]:
                    return False
            else:
                if attr in other.stub:
                    return True
        return False

    def __str__(self):
        info = self.info()
        if 'name' in info:
            return info['name']
        if self.stub['id'].startswith('minecraft:'):
            item_id = self.stub['id'][len('minecraft:'):]
        else:
            item_id = self.stub['id']
        if len(self.stub) == 1:
            return item_id
        if len(self.stub) == 2:
            if 'damage' in self.stub:
                return '{}/{}'.format(item_id, self.stub['damage'])
            if 'effect' in self.stub:
                if self.stub['effect'].startswith('minecraft:'):
                    return '{} of {}'.format(item_id, self.stub['effect'][len('minecraft:'):])
                else:
                    return '{} with effect {}'.format(item_id, self.stub['effect'])
            if 'tagValue' in self.stub:
                if self.stub['tagValue'] is None:
                    return '{} without tag'.format(item_id)
                else:
                    return '{} with tag {}'.format(item_id, self.stub['tagValue'])
        return str(self.stub)

    @classmethod
    def from_slot(cls, slot, *, items_data=None):
        if items_data is None:
            with (ati.assets_root / 'json' / 'items.json').open() as items_file:
                items_data = json.load(items_file)
        item_stub = {
            'id': slot['id'],
            'count': slot['Count']
        }
        plugin, string_id = slot['id'].split(':', 1)
        data_type = stub_data_type(plugin, string_id, items_data=items_data)
        if data_type is None:
            pass
        elif data_type == 'damage':
            item_stub['damage'] = slot['Damage']
        elif data_type == 'effect':
            item_stub['effect'] = slot.get('tag', {}).get('Potion', 'minecraft:water')
        elif data_type == 'tagValue':
            tag_path = items_data[plugin][string_id]['tagPath']
            try:
                tag = slot['tag']
                for tag_path_elt in tag_path:
                    tag = tag[tag_path_elt]
                item_stub['tagValue'] = tag
            except (IndexError, KeyError):
                item_stub['tagValue'] = None
        else:
            raise NotImplementedError('Unknown data type: {!r}'.format(data_type))
        return cls(item_stub, items_data=items_data)

    def image(self, link=True, tooltip=True, slot=False):
        """Generates an image of this item.

        Optional arguments:
        link -- A link to add to the image, or False for no link. The default, True, generates a link to the item info page.
        tooltip -- If true, a tooltip with the item name will be included. Defaults to True.
        slot -- If true, the image will be rendered within an inventory slot box, displaying the count specified by the item stub in the bottom right corner (unless it is 1). Defaults to False.

        Returns:
        HTML code for displaying the specified image.
        """
        return image_from_info(self.stub['id'].split(':', 1)[0], self.stub['id'].split(':', 1)[1], self.info(), block=self.is_block, link=self.link(link), tooltip=tooltip, count=self.stub.get('count', 1) if slot else None)

    def info(self):
        plugin_id, item_name = self.stub['id'].split(':', 1)
        item_info = self.items_data[plugin_id][item_name].copy()
        if self.is_block and 'blockID' not in item_info:
            raise ValueError('There is no block with the ID {}. There is however an item with that ID.'.format(self.stub['id']))
        if not self.is_block and 'itemID' not in item_info:
            raise ValueError('There is no item with the ID {}. There is however a block with that ID.'.format(self.stub['id']))
        if 'damage' in self.stub:
            if 'effect' in self.stub:
                raise ValueError('Tried to make an info page for {} with both damage and effect.'.format('a block' if self.is_block else 'an item'))
            elif 'tagValue' in self.stub:
                raise ValueError('Tried to make an info page for {} with both damage and tag.'.format('a block' if self.is_block else 'an item'))
            elif 'damageValues' in item_info:
                if str(self.stub['damage']) in item_info['damageValues']:
                    item_info.update(item_info['damageValues'][str(self.stub['damage'])])
                    del item_info['damageValues']
                else:
                    raise ValueError('The {} {} does not occur with the damage value {!r}.'.format('block' if self.is_block else 'item', self.stub['id'], self.stub['damage']))
            else:
                raise ValueError('The {} {} has no damage values.'.format('block' if self.is_block else 'item', self.stub['id']))
        elif 'effect' in self.stub:
            effect_plugin, effect_id = self.stub['effect'].split(':')
            if 'tagValue' in self.stub:
                raise ValueError('Tried to make an info page for {} with both effect and tag.'.format('a block' if self.is_block else 'an item'))
            elif 'effects' in item_info:
                if effect_plugin in item_info['effects'] and effect_id in item_info['effects'][effect_plugin]:
                    item_info.update(item_info['effects'][effect_plugin][effect_id])
                    del item_info['effects']
                else:
                    raise ValueError('The {} {} does not occur with the effect {!r}.'.format('block' if self.is_block else 'item', self.stub['id'], self.stub['effect']))
            else:
                raise ValueError('The {} {} has no effect values.'.format('block' if self.is_block else 'item', self.stub['id']))
        elif 'tagValue' in self.stub:
            if 'tagPath' in item_info:
                if self.stub['tagValue'] is None:
                    if '' in item_info['tagVariants']:
                        item_info.update(item_info['tagVariants'][''])
                        del item_info['tagPath']
                        del item_info['tagVariants']
                    else:
                        raise ValueError('The {} {} does not occur with the empty tag variant.'.format('block' if self.is_block else 'item', self.stub['id']))
                else:
                    if str(self.stub['tagValue']) in item_info['tagVariants']:
                        item_info.update(item_info['tagVariants'][str(self.stub['tagValue'])])
                        del item_info['tagPath']
                        del item_info['tagVariants']
                    else:
                        raise ValueError('The {} {} does not occur with the tag variant {!r}.'.format('block' if self.is_block else 'item', self.stub['id'], self.stub['tagValue']))
            else:
                raise ValueError('The {} {} has no tag variants.'.format('block' if self.is_block else 'item', self.stub['id']))
        elif 'damageValues' in item_info:
            raise ValueError('Must specify damage')
        elif 'effects' in item_info:
            raise ValueError('Must specify effect')
        elif 'tagPath' in item_info:
            raise ValueError('Must specify tag value')
        return item_info

    @property
    def is_block(self):
        return False

    def link(self, link=True):
        if link is True:
            # derive link from item stub
            if 'damage' in self.stub:
                link = self.stub['damage']
            elif 'effect' in self.stub:
                link = self.stub['effect']
            elif 'tagValue' in self.stub:
                link = {'tagValue': self.stub['tagValue']}
            else:
                link = None # base item
        return link

    def link_text(self, text=None, *, link=True, raw_html=False):
        link = self.link(link)
        if text is None:
            text = str(self)
        plugin, string_id = self.stub['id'].split(':', 1)
        return linkify(plugin, string_id, text if raw_html else xml.sax.saxutils.escape(text), link, block=self.is_block)

    def matches_slot(self, slot):
        if slot['id'] != self.stub['id']:
            return False
        if 'damage' in self.stub:
            if slot['Damage'] != self.stub['damage']:
                return False
        if 'effect' in self.stub:
            if slot.get('tag', {}).get('Potion', 'minecraft:water') != self.stub['effect']:
                return False
        if 'tagValue' in self.stub:
            if 'tag' in slot:
                plugin, item_id = self.stub['id'].split(':', 1)
                tag = slot['tag']
                for tag_path_elt in self.items_data[plugin][item_id]['tagPath']:
                    try:
                        tag = tag[tag_path_elt]
                    except (KeyError, IndexError):
                        return False
                if tag != self.stub['tagValue']:
                    return False
            else:
                if self.stub['tagValue'] is not None:
                    return False
        return True

    @property
    def max_stack_size(self):
        result = self.info().get('stackable', True)
        if isinstance(result, bool):
            result = 64 if result else 1
        return result

    def renewability(self, *, lag=None):
        """Calculates renewability level (https://wiki.wurstmineberg.de/Renewability) for this type of block or item.

        Keyword-only arguments:
        lag -- A boolean or None, indicating whether to include latency-induced atomic genesis (https://wiki.wurstmineberg.de/Latency-induced_Atomic_Genesis) in the calculation. If None (the default), only include legal dupes.

        Returns:
        An instance of the Renewability enum.
        """
        raise NotImplementedError() #TODO

class Block(Item):
    @classmethod
    def from_chunk(cls, chunk_block, *, items_data=None):
        """Parses block info as returned by the api.v2.api_chunk_info_<dimension> endpoints"""
        try:
            item_stub = {'id': chunk_block['id']}
        except:
            return cls('minecraft:air', items_data=items_data)
        plugin, string_id = chunk_block['id'].split(':', 1)
        data_type = stub_data_type(plugin, string_id, items_data=items_data)
        if data_type is None:
            pass
        elif data_type == 'damage':
            item_stub['damage'] = chunk_block['damage']
        elif data_type == 'effect':
            raise NotImplementedError('Parsing block info with effect data not implemented')
        elif data_type == 'tagValue':
            raise NotImplementedError('Parsing block info with tag variants not implemented')
        else:
            raise NotImplementedError('Unknown data type: {!r}'.format(data_type))
        return cls(item_stub, items_data=items_data)

    @classmethod
    def from_slot(cls, slot):
        raise NotImplementedError('Cannot create a block from a slot')

    @property
    def is_block(self):
        return True

def comparator_signal(block, other_block=None, *, items_data=None):
    """Calculates the redstone signal strength a comparator attached to this block would produce.

    Required arguments:
    block -- A dict containing info about a block, in the format returned by api.v2.api_chunk_info_overworld etc.

    Optional arguments:
    other_block -- A dict in the same format as block, used to measure double chests and double trapped chests.

    Keyword-only arguments:
    items_data -- The JSON-decoded contents of assets.wurstmineberg.de/json/items.json — will be decoded from disk if omitted.

    Returns:
    An integer in range(16). 0 is no redstone signal, and 15 is the strongest possible signal.

    Raises:
    AssertionError -- if other_block is not a chest, or if block and other_block differ in block ID.
    KeyError -- if the jukebox contains an unknown music disc, or the block data is formatted incorrectly.
    NotImplementedError -- if the block is not a known container block.
    """
    if items_data is None:
        with (ati.assets_root / 'json' / 'items.json').open() as items_file:
            items_data = json.load(items_file)
    if other_block is not None:
        assert block['id'] == other_block['id']
        assert other_block['id'] in ('minecraft:chest', 'minecraft:trapped_chest')
        def fullness(slot):
            item = Item.from_slot(slot, items_data=items_data)
            return slot['Count'] / item.max_stack_size

        inventory = block['tileEntity']['Items'] + other_block['tileEntity']['Items']
        if sum(item['Count'] for item in inventory) == 0:
            return 0
        return int(1 + 14 * sum(map(fullness, inventory)) / 54)
    elif block['id'] in NUM_SLOTS:
        def fullness(slot):
            item = Item.from_slot(slot, items_data=items_data)
            return slot['Count'] / item.max_stack_size

        inventory = block['tileEntity']['Items']
        if sum(item['Count'] for item in inventory) == 0:
            return 0
        return int(1 + 14 * sum(map(fullness, inventory)) / NUM_SLOTS[block['id']])
    elif block['id'] == 'minecraft:cake':
        return 14 - 2 * block['damage']
    elif block['id'] == 'minecraft:cauldron':
        return block['damage']
    elif block['id'] in ('minecraft:command_block', 'minecraft:repeating_command_block', 'minecraft:chain_command_block'):
        return block['tileEntity']['SuccessCount']
    elif block['id'] == 'minecraft:end_portal_frame':
        return 15 if block['damage'] & 0x4 == 0x4 else 0
    elif block['id'] == 'minecraft:jukebox':
        if block['damage'] == 0:
            return 0
        record_signals = {
            'minecraft:record_13': 1,
            'minecraft:record_cat': 2,
            'minecraft:record_blocks': 3,
            'minecraft:record_chirp': 4,
            'minecraft:record_far': 5,
            'minecraft:record_mall': 6,
            'minecraft:record_mellohi': 7,
            'minecraft:record_stal': 8,
            'minecraft:record_strad': 9,
            'minecraft:record_ward': 10,
            'minecraft:record_11': 11,
            'minecraft:record_wait': 12
        }
        return record_signals[block['tileEntity']['RecordItem']['id']]
    else:
        raise NotImplementedError('Comparator signal for {} NYI'.format(block['id'])) #TODO detector rail, item frame

def stub_data_type(plugin, string_id, *, items_data=None):
    if items_data is None:
        with (ati.assets_root / 'json' / 'items.json').open() as items_file:
            items_data = json.load(items_file)
    item_info = items_data[plugin][string_id]
    if 'damageValues' in item_info:
        return 'damage'
    if 'effects' in item_info:
        return 'effect'
    if 'tagPath' in item_info:
        return 'tagValue'

def linkify(plugin, string_id, html, link, *, block=False):
    if link is False:
        return html
    elif link is None:
        # base item
        return '<a href="/{}/{}/{}">{}</a>'.format('block' if block else 'item', plugin, string_id, html)
    elif isinstance(link, int):
        # damage value
        return '<a href="/{}/{}/{}/{}">{}</a>'.format('block' if block else 'item', plugin, string_id, link, html)
    elif isinstance(link, dict):
        if 'tagValue' in link:
            # tag variant
            return '<a href="/{}/{}/{}/tag/{}">{}</a>'.format('block' if block else 'item', plugin, string_id, 'null' if link['tagValue'] is None else link['tagValue'], html)
        else:
            raise ValueError('Invalid link field')
    elif isinstance(link, str) and re.match('[0-9a-z_]+:[0-9a-z_]+', link):
        # effect
        effect_plugin, effect_id = link.split(':', 1)
        return '<a href="/{}/{}/{}/effect/{}/{}">{}</a>'.format('block' if block else 'item', plugin, string_id, effect_plugin, effect_id, html)
    else:
        return '<a href="{}">{}</a>'.format(link, html)

def image_from_info(plugin, string_id, item_info, *, classes=None, tint=None, style='width: 32px;', block=False, link=False, tooltip=False, count=None, damage=0):
    if classes is None:
        classes = []
    else:
        classes = classes.copy()
    if block and 'blockInfo' in item_info:
        item_info = item_info.copy()
        item_info.update(item_info['blockInfo'])
        del item_info['blockInfo']
    if 'image' in item_info:
        image_info = item_info['image']
        if isinstance(image_info, str):
            image_info = {'prerendered': image_info}
        if image_info.get('nearestNeighbor', False):
            classes.append('nearest-neighbor')
        if tint is None:
            ret = '<img src="//assets.{host}/img/grid/{}" class="{}" style="{}" />'.format(image_info['prerendered'], ' '.join(classes), style, host=ati.host)
        else:
            ret = '<img style="background: url(//api.{host}/v2/minecraft/items/render/dyed-by-id/{}/{}/{:06x}.png)" src="//assets.{host}/img/grid-overlay/{}" class="{}" style="{}" />'.format(plugin, item_id, tint, image_info['prerendered'], ' '.join(classes), style, host=ati.host)
    else:
        ret = '<img src="//assets.{host}/img/grid-unknown.png" class="{}" style="{}" />'.format(' '.join(classes), style, host=ati.host)
    if count is not None:
        if damage > 0 and item_info.get('durability', 0) > 0:
            durability_fraction = (item_info['durability'] - damage) / item_info['durability']
            damage_html = '<div class="durability"><div style="background-color: hsl({}, 100%, 50%); width: {}px;"></div></div>'.format(int(durability * 120), int(durability * 14) * 2)
        else:
            damage_html = ''
        if count == 1:
            count_html = ''
        else:
            count_html = '<span class="count">{}</span>'.format(count)
        if tooltip:
            ret = '<div class="inv-cell-style use-tooltip" title="{}"><div class="inv-cell-image">{}</div>{}{}</div>'.format(item_info['name'], ret, damage_html, count_html)
        else:
            ret = '<div class="inv-cell-style"><div class="inv-cell-image">{}</div>{}{}</div>'.format(ret, damage_html, count_html)
    elif tooltip:
        ret = '<span class="use-tooltip" title="{}">{}</span>'.format(item_info['name'], ret)
    return linkify(plugin, string_id, ret, link, block=block)

def all(items_data=None):
    """Yields (Block, Item) tuples for each distinct type of block and item. Yields (NoneType, Item) for non-block items, and (Block, NoneType) for non-item blocks."""
    if items_data is None:
        with (ati.assets_root / 'json' / 'items.json').open() as items_file:
            items_data = json.load(items_file)
    for plugin_name, plugin in items_data.items():
        for item_id, item_info in plugin.items():
            if 'damageValues' in item_info:
                for damage_str in item_info['damageValues']:
                    stub = {'id': '{}:{}'.format(plugin_name, item_id), 'damage': int(damage_str)}
                    yield (Block(stub, items_data=items_data) if 'blockID' in item_info else None, Item(stub, items_data=items_data) if 'itemID' in item_info else None)
            elif 'effects' in item_info:
                for effect_plugin_name, effect_plugin in item_info['effects'].items():
                    for effect_id in effect_plugin:
                        stub = {'id': '{}:{}'.format(plugin_name, item_id), 'effect': '{}:{}'.format(effect_plugin_name, effect_id)}
                        yield (Block(stub, items_data=items_data) if 'blockID' in item_info else None, Item(stub, items_data=items_data) if 'itemID' in item_info else None)
            elif 'tagPath' in item_info:
                for tag_value in item_info['tagVariants']:
                    stub = {'id': '{}:{}'.format(plugin_name, item_id), 'tagValue': tag_value}
                    yield (Block(stub, items_data=items_data) if 'blockID' in item_info else None, Item(stub, items_data=items_data) if 'itemID' in item_info else None)
            else:
                stub = {'id': '{}:{}'.format(plugin_name, item_id)}
                yield (Block(stub, items_data=items_data) if 'blockID' in item_info else None, Item(stub, items_data=items_data) if 'itemID' in item_info else None)
