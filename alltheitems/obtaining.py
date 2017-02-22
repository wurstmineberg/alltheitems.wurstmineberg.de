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

@method('special')
def special(method, **kwargs):
    return '<p>{}</p>'.format(method['description'])

def render(**kwargs):
    method_type = kwargs['method']['type']
    if method_type in METHODS:
        try:
            return METHODS[method_type](**kwargs)
        except Exception as e:
            return bottle.template("""
                %import io, json, traceback
                <p>There was an error rendering this obtaining method:</p>
                <pre>{{e.__class__.__name__}}: {{e}}</pre>
                <p>Traceback:</p>
                %buf = io.StringIO()
                %traceback.print_exc(file=buf)
                <pre style="text-align: left;">{{buf.getvalue()}}</pre>
                <p>Sorry about that. Here's the raw method data:</p>
                <pre style="text-align: left;">{{json.dumps(method, indent=4, sort_keys=True)}}</pre>
            """, e=e, **kwargs)
    else:
        return bottle.template("""
            %import json
            <p>{{item_info['name']}} can {{'' if i == 0 else 'also '}}be obtained via a method called <code>{{method['type']}}</code> in the database. All The Items does not currently support rendering it, so here's the raw data:</p>
            <pre style="text-align: left;">{{json.dumps(method, indent=4, sort_keys=True)}}</pre>
        """, **kwargs)
