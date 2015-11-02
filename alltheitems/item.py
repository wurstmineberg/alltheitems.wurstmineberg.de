import alltheitems.__main__ as ati

import api.v2
import json
import re
import xml.sax.saxutils

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

def comparator_signal(block, *, items_data=None):
    if items_data is None:
        with (ati.assets_root / 'json' / 'items.json').open() as items_file:
            items_data = json.load(items_file)
    if block['id'] in NUM_SLOTS:
        def fullness(slot):
            item = Item.from_slot(slot, items_data=items_data)
            return slot['Count'] / item.max_stack_size()

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
        raise NotImplementedError('Comparator signal for {} NYI'.format(block['id'])) #TODO double chest, detector rail, item frame

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
    elif link is None or isinstance(link, int):
        if link is None:
            # base item
            return '<a href="/{}/{}/{}">{}</a>'.format('block' if block else 'item', plugin, string_id, html)
        else:
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


def image_from_info(plugin, string_id, item_info, *, classes=None, tint=None, style='width: 32px;', block=False, link=False, tooltip=False):
    if classes is None:
        classes = []
    if block and 'blockInfo' in item_info:
        item_info = item_info.copy()
        item_info.update(item_info['blockInfo'])
        del item_info['blockInfo']
    if 'image' in item_info:
        if tint is None:
            ret = '<img src="http://assets.{host}/img/grid/{}" class="{}" style="{}" />'.format(item_info['image'], ' '.join(classes), style, host=ati.host)
        else:
            ret = '<img style="background: url(http://api.{host}/v2/minecraft/items/render/dyed-by-id/{}/{}/{:06x}.png)" src="http://assets.{host}/img/grid-overlay/{}" class="{}" style="{}" />'.format(plugin, item_id, tint, item_info['image'], ' '.join(classes), style, host=ati.host)
    else:
        ret = '<img src="http://assets.{host}/img/grid-unknown.png" class="{}" style="{}" />'.format(' '.join(classes), style, host=ati.host)
    if tooltip:
        ret = '<span class="use-tooltip" title="{}">{}</span>'.format(item_info['name'], ret)
    return linkify(plugin, string_id, ret, link, block=block)

def info_from_stub(item_stub, block=False):
    item_info = api.v2.api_item_by_id(*item_stub['id'].split(':', 1))
    if block and 'blockID' not in item_info:
        raise ValueError('There is no block with the ID {}. There is however an item with that ID.'.format(item_stub['id']))
    if not block and 'itemID' not in item_info:
        raise ValueError('There is no item with the ID {}. There is however a block with that ID.'.format(item_stub['id']))
    if 'damage' in item_stub:
        if 'effect' in item_stub:
            raise ValueError('Tried to make an info page for {} with both damage and effect.'.format('a block' if block else 'an item'))
        elif 'tagValue' in item_stub:
            raise ValueError('Tried to make an info page for {} with both damage and tag.'.format('a block' if block else 'an item'))
        elif 'damageValues' in item_info:
            if str(item_stub['damage']) in item_info['damageValues']:
                item_info.update(item_info['damageValues'][str(item_stub['damage'])])
                del item_info['damageValues']
            else:
                raise ValueError('The {} {} does not occur with the damage value {}.'.format('block' if block else 'item', item_stub['id'], item_stub['damage']))
        else:
            raise ValueError('The {} {} has no damage values.'.format('block' if block else 'item', item_stub['id']))
    elif 'effect' in item_stub:
        effect_plugin, effect_id = item_stub['effect'].split(':')
        if 'tagValue' in item_stub:
            raise ValueError('Tried to make an info page for {} with both effect and tag.'.format('a block' if block else 'an item'))
        elif 'effects' in item_info:
            if effect_plugin in item_info['effects'] and effect_id in item_info['effects'][effect_plugin]:
                item_info.update(item_info['effects'][effect_plugin][effect_id])
                del item_info['effects']
            else:
                raise ValueError('The {} {} does not occur with the effect {}.'.format('block' if block else 'item', item_stub['id'], item_stub['effect']))
        else:
            raise ValueError('The {} {} has no effect values.'.format('block' if block else 'item', item_stub['id']))
    elif 'tagValue' in item_stub:
        if 'tagPath' in item_info:
            if item_stub['tagValue'] is None:
                if '' in item_info['tagVariants']:
                    item_info.update(item_info['tagVariants'][''])
                    del item_info['tagPath']
                    del item_info['tagVariants']
                else:
                    raise ValueError('The {} {} does not occur with the empty tag variant.'.format('block' if block else 'item', item_stub['id']))
            else:
                if str(item_stub['tagValue']) in item_info['tagVariants']:
                    item_info.update(item_info['tagVariants'][str(item_stub['tagValue'])])
                    del item_info['tagPath']
                    del item_info['tagVariants']
                else:
                    raise ValueError('The {} {} does not occur with the tag variant {}.'.format('block' if block else 'item', item_stub['id'], item_stub['tagValue']))
        else:
            raise ValueError('The {} {} has no tag variants.'.format('block' if block else 'item', item_stub['id']))
    elif 'damageValues' in item_info:
        raise ValueError('Must specify damage')
    elif 'effects' in item_info:
        raise ValueError('Must specify effect')
    elif 'tagPath' in item_info:
        raise ValueError('Must specify tag value')
    return item_info

class Item:
    def __init__(self, item_stub, *, items_data=None):
        if isinstance(item_stub, str):
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
        if items_data is None:
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
        item_stub = {'id': slot['id']}
        plugin, string_id = slot['id'].split(':', 1)
        data_type = stub_data_type(plugin, string_id, items_data=items_data)
        if data_type is None:
            pass
        elif data_type == 'damage':
            item_stub['damage'] = slot['Damage']
        elif data_type == 'effect':
            item_stub['effect'] = slot['tag']['Potion']
        elif data_type == 'tagValue':
            tag_path = self.items_data[plugin][string_id]['tagPath']
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

    def image(self, link=True, tooltip=True):
        return image_from_info(self.stub['id'].split(':', 1)[0], self.stub['id'].split(':', 1)[1], self.info(), block=self.is_block, link=self.link(link), tooltip=tooltip)

    def info(self):
        return info_from_stub(self.stub, block=self.is_block)

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
            raise NotImplementedError('match_slot with effect NYI')
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

    def max_stack_size(self):
        result = self.info().get('stackable', True)
        if isinstance(result, bool):
            result = 64 if result else 1
        return result

class Block(Item):
    @classmethod
    def from_slot(cls, slot):
        raise NotImplementedError('Cannot create a block from a slot')

    @property
    def is_block(self):
        return True
