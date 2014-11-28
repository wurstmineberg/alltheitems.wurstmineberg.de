#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wurstmineberg: All The Items
"""

import sys

sys.path.append('/opt/py')

import api
import bottle

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

ERROR_PAGE_TEMPLATE = """
%try:
    %from bottle import HTTP_CODES, request
""" + header(title='Error: {{e.status}}') + """
                <h2>Error {{e.status}}: {{HTTP_CODES.get(e.status, '(unknown error)')}}</h2>
                <p><img src="/assets/alltheitems2.png" alt="Craft ALL the items?" title="original image by Allie Brosh of Hyperbole and a Half" /></p>
                <p>Sorry, the requested URL <tt>{{repr(request.url)}}</tt>
                   caused an error:</p>
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

@application.route('/item/<plugin>/<item_id>/<damage>')
def show_item_by_damage(plugin, item_id, damage):
    item = api.api_item_by_damage(item_id, damage)
    yield header()
    yield '<h1>{}</h1>'.format(item['name'])
    yield footer()

@application.route('/item/<plugin>/<item_id>')
def show_item_by_id(plugin, item_id):
    return show_item_by_damage(plugin, item_id, None)

if __name__ == '__main__':
    bottle.run(app=application, host='0.0.0.0', port=8081)
