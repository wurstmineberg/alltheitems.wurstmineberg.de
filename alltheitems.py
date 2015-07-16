#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wurstmineberg: All The Items
"""

import sys

sys.path.append('/opt/py')

import api
import bottle
import json
import os.path
import wurstminebot.commands

bottle.debug()

assets_root = '/opt/git/github.com/wurstmineberg/assets.wurstmineberg.de/master'
document_root = '/opt/git/github.com/wurstmineberg/alltheitems.wurstmineberg.de/master'

def header(*, title='Wurstmineberg: All The Items'):
    return """<!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8" />
            <title>{title}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <meta name="description" content="Searchable Minecraft blocks and items database" />
            <meta name="author" content="Wurstmineberg" />
            <link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.0.0/css/bootstrap.min.css" />
            <link rel="stylesheet" href="//netdna.bootstrapcdn.com/font-awesome/4.1.0/css/font-awesome.min.css" />
            <link rel="stylesheet" href="http://assets.wurstmineberg.de/css/common.css" />
            <link rel="stylesheet" href="http://assets.wurstmineberg.de/css/responsive.css" />
        </head>
        <body>
            <nav class="navbar navbar-inverse navbar-fixed-top" role="navigation">
                <div class="navbar-header">
                    <button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-ex1-collapse">
                        <span class="sr-only">Toggle navigation</span>
                        <span class="icon-bar"></span>
                        <span class="icon-bar"></span>
                        <span class="icon-bar"></span>
                    </button>
                    <a class="navbar-brand" href="/">All The Items</a>
                </div>
                <!-- insert search bar here
                    <div class="collapse navbar-collapse navbar-ex1-collapse">
                        <div class="navbar-right funding-progress-container">
                            <p class="navbar-text">Search:</p>
                        </div>
                    </div>
                -->
            </nav>
            <div class="container" style="text-align: center;">
    """.format(title=title)

def footer(*, linkify_headers=False, additional_js=''):
    return """
            </div>
            <hr />
            <p class="muted text-center">The People of wurstmineberg.de 2012–2014</p>
            <script src="//code.jquery.com/jquery-1.10.1.min.js"></script>
            <script src="http://assets.wurstmineberg.de/js/underscore-min.js"></script>
            <script src="//netdna.bootstrapcdn.com/bootstrap/3.0.0/js/bootstrap.min.js"></script>
            <script src="//jquerymy.com/js/md5.js"></script>
            <script src="http://assets.wurstmineberg.de/js/common.js"></script>
            <script type="text/javascript">
                // run by default
    """ + ('linkify_headers();' if linkify_headers else '') + """
                //configure_navigation();
                set_anchor_height();
                $(".use-tooltip").tooltip();
                $("abbr").tooltip();
    """ + additional_js + """
            </script>
        </body>
    </html>
    """

def item_image(item_info, *, classes=None, tint=None, style='width: 32px;', block=False, link=False, tooltip=False):
    if classes is None:
        classes = []
    if block and 'blockInfo' in item_info:
        item_info = item_info.copy()
        item_info.update(item_info['blockInfo'])
        del item_info['blockInfo']
    if 'image' in item_info:
        if item_info['image'].startswith('http://') or item_info['image'].startswith('https://'):
            ret = '<img src="{}" class="{}" style="{}" />'.format(item_info['image'], ' '.join(classes), style)
        elif tint is None:
            ret = '<img src="http://assets.wurstmineberg.de/img/grid/{}" class="{}" style="{}" />'.format(item_info['image'], ' '.join(classes), style)
        else:
            ret = '<img style="background: url(http://api.wurstmineberg.de/minecraft/items/render/dyed-by-id/{}/{:06x}/png.png)" src="http://assets.wurstmineberg.de/img/grid-overlay/{}" class="{}" style="{}" />'.format(item_info['stringID'], tint, item_info['image'], ' '.join(classes), style)
    else:
        ret = '<img src="http://assets.wurstmineberg.de/img/grid-unknown.png" class="{}" style="{}" />'.format(' '.join(classes), style)
    if tooltip:
        ret = '<span class="use-tooltip" title="{}">{}</span>'.format(item_info['name'], ret)
    if link is False:
        return ret
    elif link is None or isinstance(link, int):
        string_id = item_info['stringID'].split(':')
        plugin = string_id[0]
        string_id = ':'.join(string_id[1:])
        if link is None:
            return '<a href="/{}/{}/{}">{}</a>'.format('block' if block else 'item', plugin, string_id, ret)
        else:
            return '<a href="/{}/{}/{}/{}">{}</a>'.format('block' if block else 'item', plugin, string_id, link, ret)
    else:
        return '<a href="{}">{}</a>'.format(link, ret)

def item_in_cloud_chest(cloud_chest):
    return api.api_item_by_damage(cloud_chest['id'], cloud_chest['damage'])

ERROR_PAGE_TEMPLATE = """
%try:
    %from bottle import HTTP_CODES, request
""" + header(title='Error {{e.status_code}}') + """
                <h2>Error {{e.status_code}}: {{HTTP_CODES.get(e.status_code, '(unknown error)')}}</h2>
                <p><img src="/assets/alltheitems2.png" alt="Craft ALL the items?" title="original image by Allie Brosh of Hyperbole and a Half" /></p>
                <p>Sorry, the requested URL <tt>{{repr(request.url)}}</tt> caused an error:</p>
                <pre>{{e.body}}</pre>
                %if e.exception:
                  <h2>Exception:</h2>
                  <pre>{{repr(e.exception)}}</pre>
                %end
                %if e.traceback:
                  <h2>Traceback:</h2>
                  <pre>{{e.traceback}}</pre>
                %end
""" + footer() + """
%except ImportError:
    <b>ImportError:</b> Could not generate the error page. Please add bottle to
    the import path.
%end
"""

class Bottle(bottle.Bottle):
    def default_error_handler(self, res):
        return bottle.tob(bottle.template(ERROR_PAGE_TEMPLATE, e=res))

application = Bottle()

@application.route('/cloud')
@application.route('/cloud/progress')
def cloud_index():
    """A page listing all Cloud corridors."""
    def image_from_cloud_chest(cloud_chest):
        if not cloud_chest.get('exists', True):
            background_color = '#777'
        elif cloud_chest['hasSorter']:
            if cloud_chest['hasOverflow'] and cloud_chest['hasSmartChest']:
                background_color = 'transparent'
            else:
                background_color = '#f00'
        elif cloud_chest['hasSmartChest']:
            stackable = item_in_cloud_chest(cloud_chest).get('stackable', True)
            if stackable is True or stackable > 1:
                background_color = '#ff0'
            else:
                background_color = '#0ff'
        else:
            background_color = '#f70'
        return '<td style="background-color: {};">{}</td>'.format(background_color, item_image(item_in_cloud_chest(cloud_chest), link=cloud_chest['damage'], tooltip=True))

    yield header()
    yield '<p>The <a href="http://wiki.wurstmineberg.de/Cloud">Cloud</a> is the public item storage on <a href="http://wurstmineberg.de/">Wurstmineberg</a>, consisting of 6 underground floors with <a href="http://wiki.wurstmineberg.de/SmartChest">SmartChests</a> in them.</p>'
    with open(os.path.join(assets_root, 'json/cloud.json')) as cloud_json:
        cloud = json.load(cloud_json)
    explained_colors = set()
    for _, _, _, _, _, chest in wurstminebot.commands.Cloud.cloud_iter(cloud):
        if not hest.get('exists', True):
            if 'gray' not in explained_colors:
                yield "<p>A gray background means that the chest hasn't been built yet or is still located somewhere else.</p>"
                explained_colors.add('gray')
        elif chest['hasSorter']:
            if chest['hasOverflow'] and chest['hasSmartChest']:
                explained_colors.add('white')
            else:
                if 'red' not in explained_colors:
                    yield '<p>A red background means that the chest has a sorter but the SmartChest and/or the overflow is missing. This can break other SmartChests, so it should be fixed as soon as possible!</p>'
                    explained_colors.add('red')
        elif chest['hasSmartChest']:
            stackable = item_in_cloud_chest(chest).get('stackable', True)
            if stackable is True or stackable > 1:
                if 'yellow' not in explained_colors:
                    yield "<p>A yellow background means that the chest doesn't have a sorter yet.</p>"
                    explained_colors.add('yellow')
            else:
                if 'cyan' not in explained_colors:
                    yield '<p>A cyan background means that the chest has no sorter because it stores an unstackable item. These items should not be automatically <a href="http://wiki.wurstmineberg.de/Soup#Cloud">sent</a> to the Cloud.</p>'
                    explained_colors.add('cyan')
        else:
            if 'orange' not in explained_colors:
                yield "<p>An orange background means that the chest doesn't have a SmartChest yet. It can only store 54 stacks.</p>"
                explained_colors.add('orange')
    if 'white' in explained_colors and len(explained_colors) > 1:
        yield '<p>A white background means that everything is okay: the chest has a SmartChest, a sorter, and overflow protection.</p>'
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
    floors = {}
    for x, corridor, y, floor, z, chest in wurstminebot.commands.Cloud.cloud_iter(cloud):
        if y not in floors:
            floors[y] = floor
    for y, floor in sorted(floors.items(), key=lambda tup: tup[0]):
        yield bottle.template("""
            %import itertools
            <h2 id="floor{{y}}">{{y}}{{Cloud.ordinal(y)}} floor (y={{73 - 10 * y}})</h2>
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
                                    {{!image(corridor[z_right])}}
                                %else:
                                    <td></td>
                                %end
                                %if len(corridor) > z_left:
                                    {{!image(corridor[z_left])}}
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
        """, Cloud=wurstminebot.commands.Cloud, image=image_from_cloud_chest, floor=floor, y=y)
    yield footer(linkify_headers=True)

@application.route('/assets/alltheitems.png')
def image_alltheitems():
    """The “Craft ALL the items!” image."""
    return bottle.static_file('static/img/alltheitems.png', root=document_root)

@application.route('/assets/alltheitems2.png')
def image_alltheitems2():
    """The “Craft ALL the items?” image."""
    return bottle.static_file('static/img/alltheitems2.png', root=document_root)

@application.route('/favicon.ico')
def show_favicon():
    """The favicon, a small version of the Wurstpick image. Original Wurstpick image by katethie, icon version by someone (maybe bl1nk)."""
    return bottle.static_file('img/favicon.ico', root=assets_root)

@application.route('/')
def show_index():
    """The index page."""
    return bottle.static_file('static/index.html', root=document_root)

@application.route('/block/<plugin>/<block_id>/<damage:int>')
def show_block_by_damage(plugin, block_id, damage):
    block = api.api_item_by_damage(plugin + ':' + block_id, damage)
    if 'blockID' not in block:
        bottle.abort(404, 'There is no block with the ID {}:{}. There is however an item with that ID.'.format(plugin, block_id))
    if 'blockInfo' in block:
        block.update(block['blockInfo'])
        del block['blockInfo']
    yield header()
    yield bottle.template("""
        <h1 style="font-size: 44px;">{{!item_image(block, style='vertical-align: baseline;', block=True)}}&thinsp;{{block['name']}}</h1>
        <p class="muted">
            {{block['stringID'].split(':')[0]}}:{{!'' if damage is None else '<a href="/block/{}/{}">'.format(plugin, block_id)}}{{':'.join(block['stringID'].split(':')[1:])}}{{!'' if damage is None else '</a>/{}'.format(damage)}}
        </p>
        %if damage is None:
            <%
                damage_values = sorted(int(damage) for damage in block.get('damageValues', {}))
                if 0 not in damage_values:
                    damage_values[:0] = [0]
                end
            %>
            <p>
                Damage values: {{!' '.join(item_image(api.api_item_by_damage(plugin + ':' + block_id, damage), link=damage, block=True, tooltip=True) for damage in damage_values)}}
            </p>
        %end
    """, api=api, item_image=item_image, plugin=plugin, block_id=block_id, block=block, damage=damage)
    yield """
        <ul id="pagination" class="nav nav-tabs">
            <li><a id="tab-obtaining" class="tab-item" href="#obtaining">Obtaining</a></li>
            <li><a id="tab-usage" class="tab-item" href="#usage">Usage</a></li>
        </ul>
    """
    yield """<style type="text/css">
        .section p:first-child {
            margin-top: 20px;
        }
    </style>"""
    yield bottle.template("""
        %import json
        <div id="obtaining" class="section">
            %i = 0
            %if 'itemID' in block:
                %item = api.api_item_by_damage(plugin + ':' + block_id, damage)
                <p>{{block['name']}} can be obtained by placing <a href="{{'/item/{}/{}'.format(plugin, block_id) if damage is None else '/item/{}/{}/{}'.format(plugin, block_id, damage)}}">{{item['name'] if item['name'] != block['name'] else 'its item form'}}</a>.</p>
                %i += 1
            %end
            %if len(block.get('obtaining', [])) > 0:
                %for method in block['obtaining']:
                    <%
                        if method['type'] in ('bonusChest', 'chest', 'craftingShaped', 'craftingShapeless', 'entityDeath', 'mining', 'smelting', 'trading'):
                            continue # this is a method of obtaining the item, not the block
                        end
                    %>
                    %if i > 0:
                        <hr />
                    %end
                    <p>{{block['name']}} can {{'' if i == 0 else 'also '}}be obtained via a method called <code>{{method['type']}}</code> in the database. It looks like this:</p>
                    <pre style="text-align: left;">{{json.dumps(method, indent=4)}}</pre>
                    %i += 1
                %end
            %end
            %if i == 0:
                %if damage is None:
                    <p>{{block['name']}} is unobtainable in Survival or has no method of obtaining common to all damage values. Click on one of the icons above to view them.</p>
                %else:
                    <p>{{block['name']}} is unobtainable in Survival. You can obtain it in Creative using the command <code>/<a href="//minecraft.gamepedia.com/Commands#setblock">setblock</a> &lt;x&gt; &lt;y&gt; &lt;x&gt; {{block['stringID']}}{{'' if damage == 0 else ' {}'.format(damage)}}</code>.</p>
                %end
            %end
        </div>
        <div id="usage" class="section hidden">
            <h2>Coming <a href="http://wiki.wurstmineberg.de/Soon™">soon™</a></h2>
        </div>
    """, api=api, plugin=plugin, block_id=block_id, block=block, damage=damage)
    yield footer(additional_js="""
        selectTabWithID("tab-obtaining");
        bindTabEvents();
    """)

@application.route('/block/<plugin>/<block_id>')
def show_block_by_id(plugin, block_id):
    return show_block_by_damage(plugin, block_id, None)

@application.route('/item/<plugin>/<item_id>/<damage:int>')
def show_item_by_damage(plugin, item_id, damage):
    item = api.api_item_by_damage(plugin + ':' + item_id, damage)
    if 'itemID' not in item:
        bottle.abort(404, 'There is no item with the ID {}:{}. There is however a block with that ID.'.format(plugin, item_id))
    yield header()
    yield bottle.template("""
        <h1 style="font-size: 44px;">{{!item_image(item, style='vertical-align: baseline;')}}&thinsp;{{item['name']}}</h1>
        <p class="muted">
            {{item['stringID'].split(':')[0]}}:{{!'' if damage is None else '<a href="/item/{}/{}">'.format(plugin, item_id)}}{{':'.join(item['stringID'].split(':')[1:])}}{{!'' if damage is None else '</a>/{}'.format(damage)}}
        </p>
        %if damage is None:
            <%
                damage_values = sorted(int(damage) for damage in item.get('damageValues', {}))
                if 0 not in damage_values:
                    damage_values[:0] = [0]
                end
            %>
            <p>
                Damage values: {{!' '.join(item_image(api.api_item_by_damage(plugin + ':' + item_id, damage), link=damage, tooltip=True) for damage in damage_values)}}
            </p>
        %end
    """, api=api, item_image=item_image, plugin=plugin, item_id=item_id, item=item, damage=damage)
    yield """
        <ul id="pagination" class="nav nav-tabs">
            <li><a id="tab-obtaining" class="tab-item" href="#obtaining">Obtaining</a></li>
            <li><a id="tab-usage" class="tab-item" href="#usage">Usage</a></li>
        </ul>
    """
    yield """<style type="text/css">
        .section p:first-child {
            margin-top: 20px;
        }
    </style>"""
    yield bottle.template("""
        %import json
        <div id="obtaining" class="section">
            %i = 0
            %if 'blockID' in item and item.get('dropsSelf', True):
                <p>{{item['name']}} can be obtained by mining <a href="{{'/block/{}/{}'.format(plugin, item_id) if damage is None else '/block/{}/{}/{}'.format(plugin, item_id, damage)}}">{{item['blockInfo']['name'] if 'blockInfo' in item and 'name' in item['blockInfo'] and item['blockInfo']['name'] != item['name'] else 'its block form'}}</a>{{'.' if item.get('dropsSelf', True) is True else ' with the following properties:'}}</p>
                %if item.get('dropsSelf', True) is not True:
                    <pre style="text-align: left;">{{json.dumps(item['dropsSelf'], indent=4)}}</pre>
                %end
                %i += 1
            %end
            %if len(item.get('obtaining', [])) > 0:
                %for method in item['obtaining']:
                    <%
                        if method['type'] in ('structure',):
                            continue # this is a method of obtaining the block, not the item
                        end
                    %>
                    %if i > 0:
                        <hr />
                    %end
                    <p>{{item['name']}} can {{'' if i == 0 else 'also '}}be obtained via a method called <code>{{method['type']}}</code> in the database. It looks like this:</p>
                    <pre style="text-align: left;">{{json.dumps(method, indent=4)}}</pre>
                    %i += 1
                %end
            %end
            %if i == 0:
                %if damage is None:
                    <p>{{item['name']}} is unobtainable in Survival or has no method of obtaining common to all damage values. Click on one of the icons above to view them.</p>
                %else:
                    <p>{{item['name']}} is unobtainable in Survival. You can obtain it in Creative using the command <code>/<a href="//minecraft.gamepedia.com/Commands#give">give</a> @p {{item['stringID']}} {{'[amount]' if damage == 0 else '<amount> {}'.format(damage)}}</code>.</p>
                %end
            %end
        </div>
        <div id="usage" class="section hidden">
            <h2>Coming <a href="http://wiki.wurstmineberg.de/Soon™">soon™</a></h2>
        </div>
    """, plugin=plugin, item_id=item_id, item=item, damage=damage)
    yield footer(additional_js="""
        selectTabWithID("tab-obtaining");
        bindTabEvents();
    """)

@application.route('/item/<plugin>/<item_id>')
def show_item_by_id(plugin, item_id):
    return show_item_by_damage(plugin, item_id, None)

if __name__ == '__main__':
    bottle.run(app=application, host='0.0.0.0', port=8081)
