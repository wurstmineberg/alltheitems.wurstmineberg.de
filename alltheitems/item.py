import alltheitems.__main__ as ati

import api.v2
import enum
import json
import numbers
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

class Item:
    def __init__(self, item_stub, *, items_data=None):
        if isinstance(item_stub, str):
            self.stub = {'id': item_stub}
        elif isinstance(item_stub, dict):
            if 'id' not in item_stub:
                raise ValueError('Missing item ID')
            self.stub = item_stub
        elif isinstance(item_stub, Item):
            self.stub = item_stub.stub
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
        if self.is_block != other.is_block:
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
        return hash((self.is_block, self.stub['id']))

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

    @property
    def is_lag_legal(self):
        raise NotImplementedError() #TODO

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
            if 'tag' not in slot:
                return False
            if 'Potion' not in slot['tag']:
                return False
            if slot['tag']['Potion'] != self.stub['effect']:
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

    def max_stack_size(self):
        result = self.info().get('stackable', True)
        if isinstance(result, bool):
            result = 64 if result else 1
        return result

    def renewability(self, *, lag=None, visited=None):
        """Calculates renewability level (https://wiki.wurstmineberg.de/Renewability) for this type of block or item.

        Keyword-only arguments:
        lag -- A boolean or None, indicating whether to include latency-induced atomic genesis (https://wiki.wurstmineberg.de/Latency-induced_Atomic_Genesis) in the calculation. If None (the default), only include legal dupes.
        visited -- Used internally for recursion.

        Returns:
        An instance of the Renewability enum.
        """
        if visited is None:
            visited = {self: None}
        else:
            visited = visited.copy()
            visited[self] = None

        def recurse(stub, block=False):
            item = (Block if block else Item)(stub)
            if item in visited:
                return visited[item]
            visited[item] = item.renewability(lag=lag, visited=visited)
            return visited[item]

        info = self.info()
        if info.get('itemID') is None:
            return Renewability.unobtainable
        result = Renewability.unobtainable
        for method in info.get('obtaining', []):
            if method['type'] == 'craftingShaped' or method['type'] == 'craftingShapeless':
                recipe_renewability = Renewability.renewable # crafting is manual
                for ingredient in method['recipe']:
                    if ingredient is None:
                        continue # empty slot
                    ingredient_renewability = recurse(ingredient)
                    if ingredient_renewability is None:
                        # a circle in the recipe graph, assume unobtainable
                        recipe_renewability = Renewability.unobtainable
                    else:
                        recipe_renewability = min(recipe_renewability, ingredient_renewability)
                result = max(result, recipe_renewability)
            elif method['type'] == 'smelting':
                # assume fully_automatic fuel exists
                ingredient_renewability = recurse(method['input'])
                if ingredient_renewability is not None:
                    result = max(result, ingredient_renewability)
            elif method['type'] == 'entityDeath':
                # assumes all entities can be spawned fully automatically
                #TODO remove this assumption, requires additional data in entities.json
                if method.get('requires') in ('player', 'chargedCreeper', 'whileUsing', 'noCrash', 'whileWearing', 'halloween'):
                    # these require manual player interaction
                    result = max(result, Renewability.renewable)
                else:
                    result = max(result, Renewability.fully_automatic)
            elif method['type'] == 'mining':
                raise NotImplementedError('mining renewability not implemented') #TODO
            elif method['type'] == 'structure':
                continue # structure is for blocks
            elif method['type'] == 'trading':
                raise NotImplementedError('trading renewability not implemented') #TODO
            elif method['type'] == 'fishing':
                raise NotImplementedError('fishing renewability not implemented') #TODO
            elif method['type'] == 'brewing':
                raise NotImplementedError('brewing renewability not implemented') #TODO
            elif method['type'] == 'bonusChest':
                raise NotImplementedError('bonusChest renewability not implemented') #TODO
            elif method['type'] == 'chest':
                raise NotImplementedError('chest renewability not implemented') #TODO
            elif method['type'] == 'natural':
                continue # natural is for blocks
            elif method['type'] == 'plantGrowth':
                continue # plantGrowth is for blocks
            elif method['type'] == 'modifyBlock':
                continue # modifyBlock is for blocks
            elif method['type'] == 'useItem':
                if method.get('createsBlock', False):
                    continue
                source_renewability = recurse(method['item'])
                if source_renewability is None:
                    continue
                if 'onBlock' in method:
                    block_renewability = recurse(method['onBlock'])
                    if block_renewability is None:
                        continue
                    if isinstance(method['onBlock'], dict) and method['onBlock'].get('consumed', False):
                        source_renewability = min(source_renewability, block_renewability)
                result = max(result, min(source_renewability, Renewability.manual))
            elif method['type'] == 'liquids':
                continue # liquids is for blocks
            elif method['type'] == 'special':
                if method.get('block', False):
                    continue
                raise NotImplementedError('special renewability not implemented') #TODO
            else:
                raise NotImplementedError('Method of obtaining not implemented: {!r}'.format(method['type']))
        drops_self = info.get('dropsSelf', 1)
        if isinstance(drops_self, numbers.Number):
            if drops_self > 0:
                visited[Block(self)] = Block(self).renewability(lag=lag, visited=visited)
                if visited[Block(self)] is not None:
                    result = max(result, visited[Block(self)])
        else:
            if isinstance(drops_self, dict):
                drops_self = [drops_self]
            for mining_info in drops_self:
                if isinstance(mining_info, dict) and 'id' in mining_info:
                    # tool item stub
                    raise NotImplementedError('Tool item stub not implemented for dropsSelf') #TODO
                elif isinstance(mining_info, dict):
                    # mining info
                    raise NotImplementedError('Mining info not implemented for dropsSelf') #TODO
                else:
                    # default tool, assume renewable
                    visited[Block(self)] = Block(self).renewability(lag=lag, visited=visited)
                    if visited[Block(self)] is not None:
                        result = max(result, min(Renewability.renewable, visited[Block(self)]))
        raise NotImplementedError('dropsSelf renewability not implemented') #TODO
        if lag is True:
            if result >= Renewability.obtainable:
                result = Renewability.fully_automatic
        elif lag is None:
            if result >= Renewability.obtainable and self.is_lag_legal:
                result = Renewability.fully_automatic
        return result

class Block(Item):
    @classmethod
    def from_slot(cls, slot):
        raise NotImplementedError('Cannot create a block from a slot')

    @property
    def is_block(self):
        return True

    @property
    def is_lag_legal(self):
        raise NotImplementedError('Cannot dupe blocks with latency-induced atomic genesis')

    def renewability(self, *, lag=None, visited=None):
        info = self.info()
        if info.get('blockID') is None:
            return Renewability.unobtainable
        result = Renewability.unobtainable
        for method in info.get('obtaining', []):
            if method['type'] == 'craftingShaped':
                continue # craftingShaped is for items
            elif method['type'] == 'craftingShapeless':
                continue # craftingShapeless is for items
            elif method['type'] == 'smelting':
                continue # smelting is for items
            elif method['type'] == 'entityDeath':
                continue # entityDeath is for items
            elif method['type'] == 'mining':
                continue # mining is for items
            elif method['type'] == 'structure':
                raise NotImplementedError('structure renewability not implemented') #TODO
            elif method['type'] == 'trading':
                continue # trading is for items
            elif method['type'] == 'fishing':
                continue # fishing is for items
            elif method['type'] == 'brewing':
                continue # brewing is for items
            elif method['type'] == 'bonusChest':
                continue # bonusChest is for items
            elif method['type'] == 'chest':
                continue # chest is for items
            elif method['type'] == 'natural':
                raise NotImplementedError('natural renewability not implemented') #TODO
            elif method['type'] == 'plantGrowth':
                raise NotImplementedError('plantGrowth renewability not implemented') #TODO
            elif method['type'] == 'modifyBlock':
                raise NotImplementedError('modifyBlock renewability not implemented') #TODO
            elif method['type'] == 'useItem':
                if not method['createsBlock']:
                    continue
                raise NotImplementedError('useItem renewability not implemented') #TODO
            elif method['type'] == 'liquids':
                raise NotImplementedError('liquids renewability not implemented') #TODO
            elif method['type'] == 'special':
                if not method['block']:
                    continue
                raise NotImplementedError('special renewability not implemented') #TODO
            else:
                raise NotImplementedError('Method of obtaining not implemented: {!r}'.format(method['type']))
        raise NotImplementedError('whenPlaced renewability not implemented') #TODO
        return result

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
            return slot['Count'] / item.max_stack_size()

        inventory = block['tileEntity']['Items'] + other_block['tileEntity']['Items']
        if sum(item['Count'] for item in inventory) == 0:
            return 0
        return int(1 + 14 * sum(map(fullness, inventory)) / 54)
    elif block['id'] in NUM_SLOTS:
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
            ret = '<img src="//assets.{host}/img/grid/{}" class="{}" style="{}" />'.format(item_info['image'], ' '.join(classes), style, host=ati.host)
        else:
            ret = '<img style="background: url(//api.{host}/v2/minecraft/items/render/dyed-by-id/{}/{}/{:06x}.png)" src="//assets.{host}/img/grid-overlay/{}" class="{}" style="{}" />'.format(plugin, item_id, tint, item_info['image'], ' '.join(classes), style, host=ati.host)
    else:
        ret = '<img src="//assets.{host}/img/grid-unknown.png" class="{}" style="{}" />'.format(' '.join(classes), style, host=ati.host)
    if tooltip:
        ret = '<span class="use-tooltip" title="{}">{}</span>'.format(item_info['name'], ret)
    return linkify(plugin, string_id, ret, link, block=block)

def info_from_stub(item_stub, block=False): #TODO take an optional items_data argument and remove API dependency
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
        raise ValueError('Must specify damage for {}'.format(item_stub['id']))
    elif 'effects' in item_info:
        raise ValueError('Must specify effect for {}'.format(item_stub['id']))
    elif 'tagPath' in item_info:
        raise ValueError('Must specify tag value for {}'.format(item_stub['id']))
    return item_info
