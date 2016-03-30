#!/usr/bin/env python3

import sys

sys.path.append('/opt/py')

import alltheitems.__main__ as ati

import bottle
import json
import pathlib

import alltheitems.item

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

        chunk_cache = {}
        with (ati.assets_root / 'json' / 'items.json').open() as items_file:
            items_data = json.load(items_file)
        with (ati.cache_root / 'item-counts.json').open() as cache_f:
            cache = json.load(cache_f)
        counts = {}
        for entry in cache:
            item = alltheitems.item.Item(entry['itemStub'])
            key = (Block(item) if 'blockID' in item.info() else None, item if 'itemID' in item.info() else None)
            counts[key] = (entry['blocks'], entry['inventories'], entry['containers'], entry['dropped'], entry['other'])
        yield """<table class="stats-table table table-responsive">
            <thead>
                <tr>
                    <th class="item-image">&nbsp;</th>
                    <th class="item-name">Item</th>
                    <th class="count">Blocks</th>
                    <th class="count"><abbr title="Player inventories only. Mob inventories are counted as “other”.">Inventories</abbr></th>
                    <th class="count">Containers</th>
                    <th class="count">Dropped</th>
                    <th class="count">Other</th>
                    <th class="count">Total</th>
                </tr>
            </thead>
            <tbody>"""
        for (block, item), (blocks, inventories, containers, dropped, other) in sorted(counts.items(), key=sort_key):
            yield bottle.template("""
                <tr>
                    <td class="item-image">{{!item.image()}}</td>
                    <td class="item-name">{{!item.link_text()}}</td>
                    <td class="count{{' muted' if blocks == 0 else ''}}">{{blocks}}</td>
                    <td class="count{{' muted' if inventories == 0 else ''}}">{{inventories}}</td>
                    <td class="count{{' muted' if containers == 0 else ''}}">{{containers}}</td>
                    <td class="count{{' muted' if dropped == 0 else ''}}">{{dropped}}</td>
                    <td class="count{{' muted' if other == 0 else ''}}">{{other}}</td>
                    <td class="count{{' muted' if total == 0 else ''}}">{{total}}</td>
                </tr>
            """, item=block if item is None else item, blocks=blocks, inventories=inventories, containers=containers, dropped=dropped, other=other, total=blocks + inventories + containers + dropped + other)
        yield '</tbody></table>'
    yield from ati.html_exceptions(body())
    yield ati.footer()

if __name__ == '__main__':
    out_file = pathlib.Path(sys.argv[1])
    counts = []
    for block, item in alltheitems.item.all():
        blocks = 0 #TODO
        inventories = 0 #TODO
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
        json.dump(counts, f) #TODO
