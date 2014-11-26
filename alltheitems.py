#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wurstmineberg: All The Items
"""

import bottle

application = bottle.Bottle()
document_root = '/var/www/alltheitems.wurstmineberg.de'

@application.route('/')
def show_index():
    """The index page."""
    return bottle.static_file('index.html', root=document_root)

@application.route('/alltheitems.png')
def image_alltheitems():
    """The “Craft ALL the items!” image."""
    return bottle.static_file('alltheitems.png', root=document_root)

if __name__ == '__main__':
    bottle.run(app=application, host='0.0.0.0', port=8081)
