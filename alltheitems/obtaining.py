import bottle

METHODS = {}

def method(name):
    def wrapper(f):
        METHODS[name] = f
        return f

    return wrapper

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
