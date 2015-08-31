#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wurstmineberg: All The Items
"""

import sys

sys.path.append('/opt/py')

import bottle
import contextlib
import json
import pathlib
import re
import sys

bottle.debug()

try:
    import uwsgi
    is_dev = uwsgi.opt['is_dev'] == 'true' or uwsgi.opt['is_dev'] == b'true'
except:
    is_dev = False

if is_dev:
    assets_root = pathlib.Path('/opt/git/github.com/wurstmineberg/assets.wurstmineberg.de/branch/dev')
    document_root = pathlib.Path('/opt/git/github.com/wurstmineberg/alltheitems.wurstmineberg.de/branch/dev')
    host = 'dev.wurstmineberg.de'
    sys.path.insert(1, '/opt/git/github.com/wurstmineberg/api.wurstmineberg.de/branch/dev')
    import api
    api.CONFIG_PATH = '/opt/wurstmineberg/config/devapi.json'
else:
    assets_root = pathlib.Path('/opt/git/github.com/wurstmineberg/assets.wurstmineberg.de/master')
    document_root = pathlib.Path('/opt/git/github.com/wurstmineberg/alltheitems.wurstmineberg.de/master')
    host = 'wurstmineberg.de'
    import api

def header(*, title='All The Items'):
    if is_dev:
        title = '[DEV] ' + title
    return bottle.template("""<!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8" />
            <title>{{title}}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <meta name="description" content="Searchable Minecraft blocks and items database" />
            <meta name="author" content="Wurstmineberg" />
            <link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.0.0/css/bootstrap.min.css" />
            <link rel="stylesheet" href="//netdna.bootstrapcdn.com/font-awesome/4.1.0/css/font-awesome.min.css" />
            <link rel="stylesheet" href="http://assets.{{host}}/css/common.css" />
            <link rel="stylesheet" href="http://assets.{{host}}/css/responsive.css" />
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
                    <a class="navbar-brand" href="http://{{host}}/">Wurstmineberg</a>
                </div>
                <div class="collapse navbar-collapse navbar-ex1-collapse">
                    <ul id="navbar-list" class="nav navbar-nav">
                        <li><a href="http://{{host}}/"><i class="fa fa-home"></i> Home</a></li>
                        <li><a href="http://{{host}}/about"><i class="fa fa-info-circle"></i> About</a></li>
                        <li><a href="http://{{host}}/people"><i class="fa fa-users"></i> People</a></li>
                        <li><a href="http://{{host}}/stats"><i class="fa fa-table"></i> Statistics</a></li>
                        <li class="dropdown">
                            <a href="#" class="dropdown-toggle" data-toggle="dropdown" aria-expanded="true"><i class="fa fa-book"></i> Wiki<b class="caret"></b></a>
                            <ul class="dropdown-menu p-navigation" id="p-navigation">
                                <li id="n-mainpage-description"><a href="http://wiki.{{host}}/" title="Visit the main page [ctrl-alt-z]" accesskey="z">Main page</a></li>
                                <li id="n-currentevents"><a href="http://wiki.{{host}}/Wurstmineberg_Wiki:Current_events" title="Find background information on current events">Current events</a></li>
                                <li id="n-recentchanges"><a href="http://wiki.{{host}}/Special:RecentChanges" title="A list of recent changes in the wiki [ctrl-alt-r]" accesskey="r">Recent changes</a></li>
                                <li id="n-randompage"><a href="http://wiki.{{host}}/Special:Random" title="Load a random page [ctrl-alt-x]" accesskey="x">Random page</a></li>
                                <li id="n-help"><a href="https://www.mediawiki.org/wiki/Special:MyLanguage/Help:Contents" title="The place to find out">Help</a></li>
                            </ul>
                        </li>
                        <li class="dropdown active">
                            <a href="#" class="dropdown-toggle" data-toggle="dropdown" aria-expanded="true"><i class="fa fa-ellipsis-h"></i> More<b class="caret"></b></a>
                            <ul class="dropdown-menu">
                                <li><a href="/">All The Items</a></li>
                            </ul>
                        </li>
                    </ul>
                    <!-- insert search bar here
                        <div class="navbar-right ati-search-bar">
                            <p class="navbar-text">Search:</p>
                        </div>
                    -->
                </div>
            </nav>
            <div class="container" style="text-align: center;">
    """, title=title, host=host)

def footer(*, linkify_headers=False, additional_js=''):
    return """
            </div>
            <hr />
            <p class="muted text-center">The People of wurstmineberg.de 2012–2015</p>
            <script src="//code.jquery.com/jquery-1.10.1.min.js"></script>
            <script src="http://assets.{host}/js/underscore-min.js"></script>
            <script src="//netdna.bootstrapcdn.com/bootstrap/3.0.0/js/bootstrap.min.js"></script>
            <script src="//jquerymy.com/js/md5.js"></script>
            <script src="http://assets.{host}/js/common.js"></script>
            <script type="text/javascript">
                // run by default
    """.format(host=host) + ('linkify_headers();' if linkify_headers else '') + """
                set_anchor_height();
                $(".use-tooltip").tooltip();
                $("abbr").tooltip();
    """ + ("""
                $('.navbar-brand').after($('<span>').css({
                    color: 'red',
                    left: 100,
                    position: 'absolute',
                    top: 30,
                    transform: 'rotate(-10deg) scale(2)',
                    'z-index': 10
                }).text('[DEV]'));
    """ if is_dev else '') + additional_js + """
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
            ret = '<img src="http://assets.{host}/img/grid/{}" class="{}" style="{}" />'.format(item_info['image'], ' '.join(classes), style, host=host)
        else:
            ret = '<img style="background: url(http://api.{host}/minecraft/items/render/dyed-by-id/{}/{:06x}/png.png)" src="http://assets.{host}/img/grid-overlay/{}" class="{}" style="{}" />'.format(item_info['stringID'], tint, item_info['image'], ' '.join(classes), style, host=host)
    else:
        ret = '<img src="http://assets.{host}/img/grid-unknown.png" class="{}" style="{}" />'.format(' '.join(classes), style, host=host)
    if tooltip:
        ret = '<span class="use-tooltip" title="{}">{}</span>'.format(item_info['name'], ret)
    if link is False:
        return ret
    elif link is None or isinstance(link, int):
        string_id = item_info['stringID'].split(':')
        plugin = string_id[0]
        string_id = ':'.join(string_id[1:])
        if link is None:
            # base item
            return '<a href="/{}/{}/{}">{}</a>'.format('block' if block else 'item', plugin, string_id, ret)
        else:
            # damage value
            return '<a href="/{}/{}/{}/{}">{}</a>'.format('block' if block else 'item', plugin, string_id, link, ret)
    elif isinstance(link, str) and re.match('[0-9a-z_]+:[0-9a-z_]+', link):
        # effect
        string_id = item_info['stringID'].split(':')
        plugin = string_id[0]
        string_id = ':'.join(string_id[1:])
        effect_id = link.split(':')
        effect_plugin = effect_id[0]
        effect_id = ':'.join(effect_id[1:])
        return '<a href="/{}/{}/{}/effect/{}/{}">{}</a>'.format('block' if block else 'item', plugin, string_id, effect_plugin, effect_id, ret)
    else:
        return '<a href="{}">{}</a>'.format(link, ret)

def item_info_from_stub(item_stub, block=False):
    if isinstance(item_stub, str):
        item_stub = {'id': item_stub}
    item_info = api.api_item_by_id(item_stub['id'])
    if block and 'blockID' not in item_info:
        raise ValueError('There is no block with the ID {}. There is however an item with that ID.'.format(item_stub['id']))
    if not block and 'itemID' not in item_info:
        raise ValueError('There is no item with the ID {}. There is however a block with that ID.'.format(item_stub['id']))
    if 'blockInfo' in item_info:
        if block:
            item_info.update(item_info['blockInfo'])
        del item_info['blockInfo']
    if 'damage' in item_stub:
        if 'effect' in item_stub:
            raise ValueError('Tried to make an info page for {} with both damage and effect.'.format('a block' if block else 'an item'))
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
        if 'effects' in item_info:
            if effect_plugin in item_info['effects'] and effect_id in item_info['effects'][effect_plugin]:
                item_info.update(item_info['effects'][effect_plugin][effect_id])
                del item_info['effects']
            else:
                raise ValueError('The {} {} does not occur with the effect {}.'.format('block' if block else 'item', item_stub['id'], item_stub['effect']))
        else:
            raise ValueError('The {} {} has no effect values.'.format('block' if block else 'item', item_stub['id']))
    elif 'damageValues' in item_info:
        raise ValueError('Must specify damage')
    elif 'effects' in item_info:
        raise ValueError('Must specify effect')
    return item_info

def item_stub_image(item_stub, *, block=False, link=True, tooltip=True):
    if link is True:
        # derive link from item stub
        if 'damage' in item_stub:
            link = item_stub['damage']
        elif 'effect' in item_stub:
            link = item_stub['effect']
        else:
            link = None # base item
    return item_image(item_info_from_stub(item_stub, block=block), block=block, link=link, tooltip=tooltip)

def ordinal(number):
    decimal = str(number)
    if decimal[-1] == '1' and number % 100 != 11:
        return 'st'
    elif decimal[-1] == '2' and number % 100 != 12:
        return 'nd'
    elif decimal[-1] == '3' and number % 100 != 13:
        return 'rd'
    return 'th'

def html_exceptions(content_iter):
    try:
        yield from content_iter
    except Exception as e:
        yield bottle.template("""
            %import io, traceback
            <p>Sorry, the requested page caused an error:</p>
            <pre>{{e.__class__.__name__}}: {{e}}</pre>
            <h2>Traceback:</h2>
            %buf = io.StringIO()
            %traceback.print_exc(file=buf)
            <pre>{{buf.getvalue()}}</pre>
        """, e=e)

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
    <b>ImportError:</b> Could not generate the error page. Please add bottle to the import path.
%end
"""

class Bottle(bottle.Bottle):
    def default_error_handler(self, res):
        return bottle.tob(bottle.template(ERROR_PAGE_TEMPLATE, e=res))

application = Bottle()

@application.route('/assets/alltheitems.png')
def image_alltheitems():
    """The “Craft ALL the items!” image."""
    return bottle.static_file('static/img/alltheitems.png', root=str(document_root))

@application.route('/assets/alltheitems2.png')
def image_alltheitems2():
    """The “Craft ALL the items?” image."""
    return bottle.static_file('static/img/alltheitems2.png', root=str(document_root))

@application.route('/favicon.ico')
def show_favicon():
    """The favicon, a small version of the Wurstpick image. Original Wurstpick image by katethie, icon version by someone (maybe bl1nk)."""
    return bottle.static_file('img/favicon.ico', root=str(assets_root))

@application.route('/')
def show_index():
    """The index page."""
    return bottle.static_file('static/index.html', root=str(document_root))

@application.route('/cloud')
def cloud_index():
    """A page listing all Cloud corridors."""
    import alltheitems.cloud
    return alltheitems.cloud.index()

@application.route('/block/<plugin>/<block_id>')
def show_block_by_id(plugin, block_id):
    """A page with detailed information about the block with the given ID."""
    import alltheitems.item_page
    return alltheitems.item_page.item_page(plugin + ':' + block_id, block=True)

@application.route('/block/<plugin>/<block_id>/<damage:int>')
def show_block_by_damage(plugin, block_id, damage):
    """A page with detailed information about the block with the given ID and damage value."""
    import alltheitems.item_page
    return alltheitems.item_page.item_page({
        'damage': damage,
        'id': plugin + ':' + block_id
    }, block=True)

@application.route('/block/<plugin>/<block_id>/effect/<effect_plugin>/<effect_id>')
def show_block_by_effect(plugin, block_id, effect_plugin, effect_id):
    """A page with detailed information about the block with the given ID and effect."""
    import alltheitems.item_page
    return alltheitems.item_page.item_page({
        'effect': effect_plugin + ':' + effect_id,
        'id': plugin + ':' + block_id
    }, block=True)

@application.route('/item/<plugin>/<item_id>')
def show_item_by_id(plugin, item_id):
    """A page with detailed information about the item with the given ID."""
    import alltheitems.item_page
    return alltheitems.item_page.item_page(plugin + ':' + item_id)

@application.route('/item/<plugin>/<item_id>/<damage:int>')
def show_item_by_damage(plugin, item_id, damage):
    """A page with detailed information about the item with the given ID and damage value."""
    import alltheitems.item_page
    return alltheitems.item_page.item_page({
        'damage': damage,
        'id': plugin + ':' + item_id
    })

@application.route('/item/<plugin>/<item_id>/effect/<effect_plugin>/<effect_id>')
def show_item_by_effect(plugin, item_id, effect_plugin, effect_id):
    """A page with detailed information about the item with the given ID and effect."""
    import alltheitems.item_page
    return alltheitems.item_page.item_page({
        'effect': effect_plugin + ':' + effect_id,
        'id': plugin + ':' + item_id
    })

if __name__ == '__main__':
    bottle.run(app=application, host='0.0.0.0', port=8081)
