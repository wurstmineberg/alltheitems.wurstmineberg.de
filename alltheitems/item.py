import alltheitems.__main__ as ati

import api.v2
import re

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
    if link is False:
        return ret
    elif link is None or isinstance(link, int):
        if link is None:
            # base item
            return '<a href="/{}/{}/{}">{}</a>'.format('block' if block else 'item', plugin, string_id, ret)
        else:
            # damage value
            return '<a href="/{}/{}/{}/{}">{}</a>'.format('block' if block else 'item', plugin, string_id, link, ret)
    elif isinstance(link, dict):
        if 'tagValue' in link:
            # tag variant
            return '<a href="/{}/{}/{}/tag/{}">{}</a>'.format('block' if block else 'item', plugin, string_id, 'null' if link['tagValue'] is None else link['tagValue'], ret)
        else:
            raise ValueError('Invalid link field')
    elif isinstance(link, str) and re.match('[0-9a-z_]+:[0-9a-z_]+', link):
        # effect
        effect_plugin, effect_id = link.split(':', 1)
        return '<a href="/{}/{}/{}/effect/{}/{}">{}</a>'.format('block' if block else 'item', plugin, string_id, effect_plugin, effect_id, ret)
    else:
        return '<a href="{}">{}</a>'.format(link, ret)

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
    def __init__(self, item_stub):
        if isinstance(item_stub, str):
            self.stub = {'id': item_stub}
        elif isinstance(item_stub, dict):
            self.stub = item_stub
        else:
            raise TypeError('Cannot create an item from {}'.format(type(item_stub)))

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

    def image(self, link=True, tooltip=True):
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
        return image_from_info(self.stub['id'].split(':', 1)[0], self.stub['id'].split(':', 1)[1], self.info(), link=link, tooltip=tooltip)

    def info(self):
        return info_from_stub(self.stub)

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
                with (ati.assets_root / 'json' / 'items.json').open() as items_file:
                    items_data = json.load(items_file)
                plugin, item_id = self.stub['id'].split(':', 1)
                tag = slot['tag']
                for tag_path_elt in items_data[plugin][item_id]['tagPath']:
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

class Block(Item):
    def image(self, link=True, tooltip=True):
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
        return image_from_info(self.stub['id'].split(':', 1)[0], self.stub['id'].split(':', 1)[1], self.info(), block=True, link=link, tooltip=tooltip)

    def info(self):
        return info_from_stub(self.stub, block=True)
