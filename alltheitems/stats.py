#!/usr/bin/env python3

import sys

sys.path.append('/opt/py')

import alltheitems.__main__ as ati

import bottle
import datetime
import json

import alltheitems.item
import alltheitems.util

def index():
    yield ati.header(title='Item stats')
    def body():
        yield """<style type="text/css">
            .stats-table td {
                text-align: left;
                vertical-align: middle !important;
            }

            .stats-table .item-image {
                box-sizing: content-box;
                width: 32px;
            }

            .stats-table .count {
                width: 9em;
                text-align: right;
            }
        </style>"""

        def sort_key(pair):
            (block, item), counts = pair
            return -sum(counts), block if item is None else item

        yield """<table class="stats-table table table-responsive">
            <thead>
                <tr>
                    <th class="item-image">&nbsp;</th>
                    <th class="item-name">Item</th>
                    <th class="count"><abbr title="Blocks placed or generated in the world.">Blocks</abbr></th>
                    <th class="count"><abbr title="Player inventories and Ender chests.">Inventories</abbr></th>
                    <th class="count"><abbr title="Chests, droppers, furnaces, hopper minecarts, item frames…">Containers</abbr></th>
                    <th class="count"><abbr title="Item stack entities lying around on the ground somewhere, waiting to despawn.">Dropped</abbr></th>
                    <th class="count"><abbr title="Mob inventories, as well as item frames, boats, and minecarts (but not their inventories).">Other</abbr></th>
                    <th class="count">Total</th>
                </tr>
            </thead>
            <tbody>"""
        with (ati.assets_root / 'json' / 'items.json').open() as items_file:
            items_data = json.load(items_file)
        cache_path = ati.cache_root / 'item-counts.json'
        yield '<p>Block and item counts on the main world as of {:%Y-%m-%d %H:%M:%S} UTC:</p>'.format(datetime.datetime.utcfromtimestamp(cache_path.stat().st_mtime))
        with cache_path.open() as cache_f:
            cache = json.load(cache_f)
        counts = {}
        for entry in cache:
            try:
                item = alltheitems.item.Item(entry['itemStub'], items_data=items_data)
                item.info()
            except ValueError:
                item = None
            try:
                block = alltheitems.item.Block(entry['itemStub'], items_data=items_data)
                block.info()
            except ValueError:
                block = None
            key = (block, item)
            counts[key] = (entry['blocks'], entry['inventories'], entry['containers'], entry['dropped'], entry['other'])
        for (block, item), (blocks, inventories, containers, dropped, other) in sorted(counts.items(), key=sort_key):
            yield bottle.template("""
                <tr>
                    <td class="item-image">{{!item.image()}}</td>
                    <td class="item-name">{{!item.link_text()}}</td>
                    <td class="count{{' muted' if blocks == 0 else ''}}">{{format_num(blocks)}}</td>
                    <td class="count{{' muted' if inventories == 0 else ''}}">{{format_num(inventories)}}</td>
                    <td class="count{{' muted' if containers == 0 else ''}}">{{format_num(containers)}}</td>
                    <td class="count{{' muted' if dropped == 0 else ''}}">{{format_num(dropped)}}</td>
                    <td class="count{{' muted' if other == 0 else ''}}">{{format_num(other)}}</td>
                    <td class="count{{' muted' if total == 0 else ''}}">{{format_num(total)}}</td>
                </tr>
            """, format_num=alltheitems.util.format_num, item=block if item is None else item, blocks=blocks, inventories=inventories, containers=containers, dropped=dropped, other=other, total=blocks + inventories + containers + dropped + other)
        yield '</tbody></table>'
    yield from ati.html_exceptions(body())
    yield ati.footer()

if __name__ == '__main__':
    import api.util2
    import api.v2
    import collections
    import minecraft
    import pathlib

    out_file = pathlib.Path(sys.argv[1])
    with (ati.assets_root / 'json' / 'items.json').open() as items_file:
        items_data = json.load(items_file)
    block_counts = collections.defaultdict(lambda: 0)
    for dimension, columns in api.v2.api_chunk_overview(minecraft.World()).items():
        for i, column in enumerate(columns):
            print('counting blocks: {} column {} of {}'.format(dimension, i + 1, len(columns)), end='\r', flush=True)
            chunk_x = column['x']
            chunk_z = column['z']
            for chunk_y in range(16):
                section = api.v2.api_chunk_info(minecraft.World(), dimension, chunk_x, chunk_y, chunk_z)
                for layer in section:
                    for row in layer:
                        for block_info in row:
                            block = alltheitems.item.Block.from_chunk(block_info, items_data=items_data)
                            block_counts[block] += 1
        print(flush=True)
    print('counting player inventories', end='\r', flush=True)
    inv_counts = collections.defaultdict(lambda: 0)
    for player_data_file in (minecraft.World().world_path / 'playerdata').iterdir():
        player_data = api.util2.nbtfile_to_dict(player_data_file)
        for inventory_type in ('Inventory', 'EnderItems'):
            for slot in player_data[inventory_type]:
                try:
                    item = alltheitems.item.Item.from_slot(slot, items_data=items_data)
                except:
                    continue
                inv_counts[item] += slot['Count']
    print(flush=True)
    counts = []
    for block, item in alltheitems.item.all():
        blocks = block_counts[block]
        inventories = inv_counts[item]
        containers = 0 #TODO
        dropped = 0 #TODO
        other = 0 #TODO
        counts.append({
            'itemStub': (block if item is None else item).stub,
            'blocks': blocks,
            'inventories': inventories,
            'containers': containers,
            'dropped': dropped,
            'other': other
        })
    with out_file.open('w') as f:
        json.dump(counts, f, sort_keys=True, indent=4)
