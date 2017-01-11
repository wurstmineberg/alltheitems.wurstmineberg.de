import bottle
import more_itertools

import alltheitems.util

METHODS = {}

def method(name):
    def wrapper(f):
        METHODS[name] = f
        return f

    return wrapper

@method('craftingShaped')
def crafting_shaped(i, item_info, method, **kwargs):
    return bottle.template("""
        <p>{{item_info['name']}} can {{'' if i == 0 else 'also '}}be crafted using the following recipe:</p>
        {{!inventory_table(chunked(method['recipe'], 3), style={'margin-left': 'auto', 'margin-right': 'auto'})}}
        %if method.get('outputAmount', 1) > 1:
            <p>This will create {{method['outputAmount']}} items per crafting process.</p>
        %end
    """, chunked=more_itertools.chunked, i=i, inventory_table=alltheitems.util.inventory_table, item_info=item_info, method=method)

@method('craftingShapeless')
def crafting_shapeless(i, item_info, method, **kwargs):
    if len(method['recipe']) == 9 and all(l == r for l, r in more_itertools.stagger(method['recipe'], offsets=(0, 1))):
        return crafting_shaped(i, item_info, method, **kwargs)
    return bottle.template("""
        <p>{{item_info['name']}} can {{'' if i == 0 else 'also '}}be crafted using the following shapeless recipe:</p>
        {{!inventory_table([method['recipe']], style={'margin-left': 'auto', 'margin-right': 'auto'})}}
        %if method.get('outputAmount', 1) > 1:
            <p>This will create {{method['outputAmount']}} items per crafting process.</p>
        %end
    """, i=i, inventory_table=alltheitems.util.inventory_table, item_info=item_info, method=method)

def render(**kwargs):
    method_type = kwargs['method']['type']
    if method_type in METHODS:
        return METHODS[method_type](**kwargs)
    else:
        return bottle.template("""
            %import json
            <p>{{item_info['name']}} can {{'' if i == 0 else 'also '}}be obtained via a method called <code>{{method['type']}}</code> in the database. It looks like this:</p>
            <pre style="text-align: left;">{{json.dumps(method, indent=4, sort_keys=True)}}</pre>
        """, **kwargs)