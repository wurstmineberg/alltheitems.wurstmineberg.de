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
    cache_root = pathlib.Path('/opt/wurstmineberg/dev-alltheitems-cache')
    document_root = pathlib.Path('/opt/git/github.com/wurstmineberg/alltheitems.wurstmineberg.de/branch/dev')
    host = 'dev.wurstmineberg.de'
    sys.path.insert(1, '/opt/git/github.com/wurstmineberg/api.wurstmineberg.de/branch/dev')
    import api.util
    api.util.CONFIG_PATH = pathlib.Path('/opt/wurstmineberg/config/devapi.json')
    api.util.CONFIG = api.util.config()
    import api.v2
else:
    assets_root = pathlib.Path('/opt/git/github.com/wurstmineberg/assets.wurstmineberg.de/master')
    cache_root = pathlib.Path('/opt/wurstmineberg/alltheitems-cache')
    document_root = pathlib.Path('/opt/git/github.com/wurstmineberg/alltheitems.wurstmineberg.de/master')
    host = 'wurstmineberg.de'
    import api.v2

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
            <link rel="shortcut icon" href="//assets.{{host}}/img/favicon.ico" />
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/3.3.5/css/bootstrap.min.css" />
            <link rel="stylesheet" href="https://netdna.bootstrapcdn.com/font-awesome/4.1.0/css/font-awesome.min.css" />
            <link rel="stylesheet" href="//assets.{{host}}/css/common.css" />
            <link rel="stylesheet" href="//assets.{{host}}/css/responsive.css" />
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
                    <a class="navbar-brand" href="//{{host}}/">Wurstmineberg</a>
                </div>
                <div class="collapse navbar-collapse navbar-ex1-collapse">
                    <ul id="navbar-list" class="nav navbar-nav">
                        <li><a href="//{{host}}/"><i class="fa fa-home"></i> Home</a></li>
                        <li><a href="//{{host}}/about"><i class="fa fa-info-circle"></i> About</a></li>
                        <li><a href="//{{host}}/people"><i class="fa fa-users"></i> People</a></li>
                        <li><a href="//{{host}}/stats"><i class="fa fa-table"></i> Statistics</a></li>
                        <li class="dropdown">
                            <a href="#" class="dropdown-toggle" data-toggle="dropdown" aria-expanded="true"><i class="fa fa-book"></i> Wiki<b class="caret"></b></a>
                            <ul class="dropdown-menu p-navigation" id="p-navigation">
                                <li id="n-mainpage-description"><a href="//wiki.{{host}}/" title="Visit the main page [ctrl-alt-z]" accesskey="z">Main page</a></li>
                                <li id="n-currentevents"><a href="//wiki.{{host}}/Wurstmineberg_Wiki:Current_events" title="Find background information on current events">Current events</a></li>
                                <li id="n-recentchanges"><a href="//wiki.{{host}}/Special:RecentChanges" title="A list of recent changes in the wiki [ctrl-alt-r]" accesskey="r">Recent changes</a></li>
                                <li id="n-randompage"><a href="//wiki.{{host}}/Special:Random" title="Load a random page [ctrl-alt-x]" accesskey="x">Random page</a></li>
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
            <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/1.11.3/jquery.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/3.3.5/js/bootstrap.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/underscore.js/1.8.3/underscore-min.js"></script>
            <script src="//assets.{host}/js/common.js"></script>
            <script type="text/javascript">
                // run by default
    """.format(host=host) + ('linkifyHeaders();' if linkify_headers else '') + """
                setAnchorHeight();
                initializeTooltips();
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

def join(sequence, *, word='and', default=None):
    sequence = list(sequence)
    if len(sequence) == 0:
        if default is None:
            raise IndexError('Tried to join empty sequence with no default')
        else:
            return str(default)
    elif len(sequence) == 1:
        return str(sequence[0])
    elif len(sequence) == 2:
        return '{} {} {}'.format(sequence[0], word, sequence[1])
    else:
        return ', '.join(sequence[:-1]) + ', {} {}'.format(word, sequence[-1])

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

@application.route('/cloud/todo')
def cloud_todo():
    """A page listing Cloud chests which are incomplete or not full, by priority."""
    import alltheitems.cloud
    return alltheitems.cloud.todo()

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

@application.route('/block/<plugin>/<block_id>/tag/<tag_value>')
def show_block_by_tag(plugin, block_id, tag_value):
    """A page with detailed information about the block with the given ID and tag variant."""
    import alltheitems.item_page
    return alltheitems.item_page.item_page({
        'id': plugin + ':' + block_id,
        'tagValue': None if tag_value == 'null' else tag_value
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

@application.route('/item/<plugin>/<item_id>/tag/<tag_value>')
def show_item_by_tag(plugin, item_id, tag_value):
    """A page with detailed information about the item with the given ID and tag variant."""
    import alltheitems.item_page
    return alltheitems.item_page.item_page({
        'id': plugin + ':' + item_id,
        'tagValue': None if tag_value == 'null' else tag_value
    })

if __name__ == '__main__':
    bottle.run(app=application, host='0.0.0.0', port=8081)
