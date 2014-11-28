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

def footer():
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
                //linkify_headers();
                //configure_navigation();
                set_anchor_height();
                $(".use-tooltip").tooltip();
                $("abbr").tooltip();
            </script>
        </body>
    </html>
    """

def item_image(item_info, *, classes=None, tint=None, style='width: 32px;', link=False, tooltip=False):
    if classes is None:
        classes = []
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
            return '<a href="/item/{}/{}">{}</a>'.format(plugin, string_id, ret)
        else:
            return '<a href="/item/{}/{}/{}">{}</a>'.format(plugin, string_id, link, ret)
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
def cloud_index():
    """A page listing all Cloud corridors."""
    yield header()
    yield '<p>The <a href="http://wiki.wurstmineberg.de/Cloud">Cloud</a> is the public item storage on <a href="http://wurstmineberg.de/">Wurstmineberg</a>, consisting of 6 underground floors with <a href="http://wiki.wurstmineberg.de/SmartChest">SmartChests</a> in them:</p>'
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
    with open(os.path.join(assets_root, 'json/cloud.json')) as cloud_json:
        cloud = json.load(cloud_json)
    floors = {}
    for x, corridor, y, floor, z, chest in wurstminebot.commands.Cloud.cloud_iter(cloud):
        if y not in floors:
            floors[y] = floor
    for y, floor in sorted(floors.items(), key=lambda tup: tup[0]):
        yield bottle.template("""
            %import itertools
            <h2>{{y}}{{Cloud.ordinal(y)}} floor (y={{73 - 10 * y}})</h2>
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
                                    <td>{{!image(corridor[z_right])}}</td>
                                %else:
                                    <td></td>
                                %end
                                %if len(corridor) > z_left:
                                    <td>{{!image(corridor[z_left])}}</td>
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
        """, Cloud=wurstminebot.commands.Cloud, image=(lambda cloud_chest: item_image(item_in_cloud_chest(cloud_chest), link=cloud_chest['damage'], tooltip=True)), floor=floor, y=y)
    yield footer()

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

@application.route('/item/<plugin>/<item_id>/<damage:int>')
def show_item_by_damage(plugin, item_id, damage):
    item = api.api_item_by_damage(item_id, damage)
    yield header()
    yield bottle.template("""
        <h1 style="font-size: 44px;">{{!image}}&thinsp;{{item['name']}}</h1>
        <p class="muted">{{item['stringID']}}{{'' if damage is None else '/{}'.format(damage)}}</p>
    """, image=item_image(item, style='vertical-align: baseline;'), item=item, damage=damage)
    yield footer()

@application.route('/item/<plugin>/<item_id>')
def show_item_by_id(plugin, item_id):
    return show_item_by_damage(plugin, item_id, None)

if __name__ == '__main__':
    bottle.run(app=application, host='0.0.0.0', port=8081)
