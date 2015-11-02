import alltheitems.__main__ as ati

import api.v2
import bottle

import alltheitems.cloud
import alltheitems.item

def is_int_str(s):
    try:
        int(s)
    except ValueError:
        return False
    return True

def normalize_item_info(item_info, item_stub, block=False, *, tag_values_are_ints=False):
    if block:
        item_stub_image = lambda item_stub: alltheitems.item.Block(item_stub).image()
    else:
        item_stub_image = lambda item_stub: alltheitems.item.Item(item_stub).image()
    if block and 'blockID' not in item_info:
        bottle.abort(404, 'There is no block with the ID {}. There is however an item with that ID.'.format(item_stub['id']))
    if not block and 'itemID' not in item_info:
        bottle.abort(404, 'There is no item with the ID {}. There is however a block with that ID.'.format(item_stub['id']))
    if 'blockInfo' in item_info:
        if block:
            item_info.update(item_info['blockInfo'])
        del item_info['blockInfo']
    if 'damage' in item_stub:
        if 'effect' in item_stub:
            bottle.abort(500, 'Tried to make an info page for {} with both damage and effect.'.format('a block' if block else 'an item'))
        elif 'tagValue' in item_stub:
            bottle.abort(500, 'Tried to make an info page for {} with both damage and tag.'.format('a block' if block else 'an item'))
        elif 'damageValues' in item_info:
            if str(item_stub['damage']) in item_info['damageValues']:
                item_info.update(item_info['damageValues'][str(item_stub['damage'])])
                del item_info['damageValues']
            else:
                bottle.abort(404, 'The {} {} does not occur with the damage value {}.'.format('block' if block else 'item', item_stub['id'], item_stub['damage']))
        else:
            bottle.abort(404, 'The {} {} has no damage values.'.format('block' if block else 'item', item_stub['id']))
    elif 'effect' in item_stub:
        effect_plugin, effect_id = item_stub['effect'].split(':')
        if 'tagValue' in item_stub:
            bottle.abort(500, 'Tried to make an info page for {} with both effect and tag.'.format('a block' if block else 'an item'))
        elif 'effects' in item_info:
            if effect_plugin in item_info['effects'] and effect_id in item_info['effects'][effect_plugin]:
                item_info.update(item_info['effects'][effect_plugin][effect_id])
                del item_info['effects']
            else:
                bottle.abort(404, 'The {} {} does not occur with the effect {}.'.format('block' if block else 'item', item_stub['id'], item_stub['effect']))
        else:
            bottle.abort(404, 'The {} {} has no effect values.'.format('block' if block else 'item', item_stub['id']))
    elif 'tagValue' in item_stub:
        if 'tagPath' in item_info:
            if item_stub['tagValue'] is None:
                if '' in item_info['tagVariants']:
                    item_info.update(item_info['tagVariants'][''])
                    del item_info['tagPath']
                    del item_info['tagVariants']
                else:
                    bottle.abort(404, 'The {} {} does not occur with the empty tag value.'.format('block' if 'block' else 'item', item_stub['id']))
            else:
                if str(item_stub['tagValue']) in item_info['tagVariants']:
                    item_info.update(item_info['tagVariants'][str(item_stub['tagValue'])])
                    del item_info['tagPath']
                    del item_info['tagVariants']
                else:
                    bottle.abort(404, 'The {} {} does not occur with the tag value {}.'.format('block' if 'block' else 'item', item_stub['id'], item_stub['tagValue']))
        else:
            bottle.abort(404, 'The {} {} has no tag variants.'.format('block' if block else 'item', item_stub['id']))
    elif 'damageValues' in item_info:
        # return damage value disambiguation page
        damage_values = sorted(int(damage) for damage in item_info['damageValues'])
        return bottle.template("""
            <h2>Damage values</h2>
            <p>
                %for damage in damage_values:
                    {{!item_stub_image({'id': item_stub['id'], 'damage': damage})}}
                %end
            </p>
        """, damage_values=damage_values, item_stub=item_stub, item_stub_image=item_stub_image)
    elif 'effects' in item_info:
        # return effect value disambiguation page
        effects = (effect_plugin + ':' + effect_id for effect_plugin in sorted(item_info['effects']) for effect_id in sorted(item_info['effects'][effect_plugin]))
        return bottle.template("""
            <h2>Effects</h2>
            <p>
                %for effect in effects:
                    {{!item_stub_image({'id': item_stub['id'], 'effect': effect})}}
                %end
            </p>
        """, effects=effects, item_stub=item_stub, item_stub_image=item_stub_image)
    elif 'tagPath' in item_info:
        if tag_values_are_ints:
            tag_values = sorted(((None if tag_value == '' else int(tag_value)) for tag_value in item_info['tagVariants']), key=lambda tag_value: -1 if tag_value is None else tag_value)
        else:
            tag_values = sorted(((None if tag_value == '' else tag_value) for tag_value in item_info['tagVariants']), key=lambda tag_value: '' if tag_value is None else tag_value)
        return bottle.template("""
            <h2>Variants</h2>
            <p>
                %for tag_value in tag_values:
                    {{!item_stub_image({'id': item_stub['id'], 'tagValue': tag_value})}}
                %end
            </p>
        """, tag_values=tag_values, item_stub=item_stub, item_stub_image=item_stub_image)

def item_title(item_info, item_stub, *, block=False, tag_path=None):
    return bottle.template("""
        %plugin, item_id = item_stub['id'].split(':', 1)
        <h1 style="font-size: 44px;">{{!item_image(plugin, item_id, item_info, style='vertical-align: baseline;', block=block)}}&thinsp;{{item_info['name']}}</h1>
        <p class="muted">
            {{plugin}}:{{!'<a href="/{}/{}/{}">'.format('block' if block else 'item', plugin, item_id) if 'damage' in item_stub or 'effect' in item_stub or 'tagValue' in item_stub else ''}}{{item_id}}{{!'</a>/{}'.format(item_stub['damage']) if 'damage' in item_stub else '</a> with {} effect'.format(item_stub['effect']) if 'effect' in item_stub else ('</a> with tag {} not set'.format('.'.join(tag_path)) if item_stub['tagValue'] is None else '</a> with tag {} set to {}'.format('.'.join(tag_path), item_stub['tagValue'])) if 'tagValue' in item_stub else ''}}
        </p>
    """, item_image=alltheitems.item.image_from_info, item_info=item_info, item_stub=item_stub, block=block, tag_path=tag_path)

def item_page(item_stub, block=False):
    if isinstance(item_stub, str):
        item_stub = {'id': item_stub}
    item_info = api.v2.api_item_by_id(*item_stub['id'].split(':', 1))
    tag_path=item_info.get('tagPath')
    tag_values_are_ints = all(tag_value == '' or is_int_str(tag_value) for tag_value in item_info.get('tagVariants', []))
    disambig = normalize_item_info(item_info, item_stub, block=block, tag_values_are_ints=tag_values_are_ints)
    yield ati.header(title=item_info.get('name', item_stub['id']))
    if disambig:
        yield item_title(item_info, item_stub, block=block, tag_path=tag_path)
        yield disambig
        yield ati.footer()
        return
    yield item_title(item_info, item_stub, block=block, tag_path=tag_path)
    def body():
        # tab bar
        yield """
            <ul id="pagination" class="nav nav-tabs">
                <li><a id="tab-section-general" class="tab-item" href="#general">General</a></li>
                <li><a id="tab-section-obtaining" class="tab-item" href="#obtaining">Obtaining</a></li>
                <li><a id="tab-section-usage" class="tab-item" href="#usage">Usage</a></li>
            </ul>
            <style type="text/css">
                .section p:first-child {
                    margin-top: 20px;
                }
            </style>
        """
        # general
        if block:
            yield bottle.template("""
                <div id="section-general" class="section">
                    <h2>Coming <a href="http://wiki.{{host}}/Soon™">soon™</a></h2>
                </div>
            """, host=ati.host) #TODO
        else:
            coords, corridor_length = alltheitems.cloud.chest_coords(item_stub, include_corridor_length=True)
            color_map = {
                'cyan': 'class="text-info"',
                'gray': 'class="muted"',
                'red': 'class="text-danger"',
                'orange': 'style="color: #bc714d;"',
                'yellow': 'class="text-warning"',
            }
            yield bottle.template("""
                <div id="section-general" class="section">
                    <h2>Cloud</h2>
                    %if coords is None:
                        <p>{{item_info['name']}} is not available in the Cloud.</p>
                    %else:
                        <p>The Cloud chest for {{item_info['name']}} is located on the {{coords[1]}}{{ordinal(coords[1])}} floor, in the {{'central' if coords[0] == 0 else '{}{}'.format(abs(coords[0]), ordinal(abs(coords[0])))}} corridor{{' to the left' if coords[0] > 0 else ' to the right' if coords[0] < 0 else ''}}. It is the {{coords[2] // 2 + 1}}{{ordinal(coords[2] // 2 + 1)}} chest on the {{'left' if coords[2] % 2 == 0 else 'right'}} wall.</p>
                        %color, state_message = chest_state()
                        %if color is None:
                            <p>{{!state_message}}</p>
                        %else:
                            <p {{!color_map[color]}}>{{!state_message}}</p>
                        %end
                    %end
                </div>
            """, ordinal=ati.ordinal, item_info=item_info, coords=coords, chest_state=lambda: alltheitems.cloud.chest_state(coords, item_stub, corridor_length), color_map=color_map)
        # obtaining
        yield bottle.template("""
            %import json
            %plugin, item_id = item_stub['id'].split(':', 1)
            %if 'effect' in item_stub:
                %effect_plugin, effect_id = item_stub['effect'].split(':', 1)
            %else:
                %effect_plugin = None
                %effect_id = None
            %end
            <div id="section-obtaining" class="section hidden">
                %i = 0
                %if block and 'itemID' in item_info:
                    %item = Item(item_stub).info()
                    %if 'whenPlaced' not in item:
                        <p>{{item_info['name']}} can be obtained by placing <a href="{{'/item/{}/{}/{}'.format(plugin, item_id, item_stub['damage']) if 'damage' in item_stub else '/item/{}/{}/effect/{}/{}'.format(plugin, item_id, effect_plugin, effect_id) if 'effect' in item_stub else '/item/{}/{}'.format(plugin, item_id)}}">{{item['name'] if item['name'] != item_info['name'] else 'its item form'}}</a>.</p>
                        %i += 1
                    %end
                %end
                %if (not block) and 'blockID' in item_info and item_info.get('dropsSelf', True):
                    %block_info = Block(item_stub).info()
                    <p>{{item_info['name']}} can be obtained by mining <a href="{{'/block/{}/{}/{}'.format(plugin, item_id, item_stub['damage']) if 'damage' in item_stub else '/block/{}/{}/effect/{}/{}'.format(plugin, item_id, effect_plugin, effect_id) if 'effect' in item_stub else '/block/{}/{}'.format(plugin, item_id)}}">{{block_info['name'] if block_info['name'] != item_info['name'] else 'its block form'}}</a>{{'.' if item_info.get('dropsSelf', True) is True else ', with the following properties:'}}</p>
                    %if item_info.get('dropsSelf', True) is not True:
                        <pre style="text-align: left;">{{json.dumps(item_info['dropsSelf'], indent=4)}}</pre>
                    %end
                    %i += 1
                %end
                %if len(item_info.get('obtaining', [])) > 0:
                    %for method in item_info['obtaining']:
                        %if i > 0:
                            <hr />
                        %end
                        <p>{{item_info['name']}} can {{'' if i == 0 else 'also '}}be obtained via a method called <code>{{method['type']}}</code> in the database. It looks like this:</p>
                        <pre style="text-align: left;">{{json.dumps(method, indent=4)}}</pre>
                        %i += 1
                    %end
                %end
                %if block:
                    %if 'effect' in item_stub:
                        %if i == 0:
                            <p>No known method exists for obtaining blocks with effect data.
                        %end
                    %elif 'tagValue' in item_stub:
                        %if i == 0:
                            <p>No known method exists for obtaining tag variants of blocks.
                        %end
                    %else:
                        <p>
                            %if i == 0:
                                {{item_info['name']}} is unobtainable in Survival.
                            %end
                            You can {{'obtain it' if i == 0 else 'also obtain ' + item_info['name']}} in Creative using the command <code>/<a href="//minecraft.gamepedia.com/Commands#setblock">setblock</a> &lt;x&gt; &lt;y&gt; &lt;x&gt; {{item_stub['id']}}{{' {}'.format(item_stub['damage']) if 'damage' in item_stub else ''}}</code>.
                        </p>
                    %end
                %else:
                    <p>
                        %if i == 0:
                            {{item_info['name']}} is unobtainable in Survival.
                        %end
                        You can {{'obtain it' if i == 0 else 'also obtain ' + item_info['name']}} in Creative using the command <code>/<a href="//minecraft.gamepedia.com/Commands#give">give</a> @p {{item_stub['id']}} {{'<amount> {}'.format(item_stub['damage']) if 'damage' in item_stub else '<amount> 0 {{Potion:"{}"}}'.format(item_stub['effect']) if 'effect' in item_stub else '<amount> 0 {' + ': {'.join(json.dumps(tag_path_elt) for tag_path_elt in tag_path) + ': ' + json.dumps(int(item_stub['tagValue']) if tag_values_are_ints else item_stub['tagValue']) + '}' * len(tag_path) if item_stub.get('tagValue') is not None else '[amount]'}}</code>.
                    </p>
                %end
            </div>
        """, Item=alltheitems.item.Item, Block=alltheitems.item.Block, normalize_item_info=normalize_item_info, item_stub=item_stub, item_info=item_info, block=block, tag_path=tag_path, tag_values_are_ints=tag_values_are_ints)
        #TODO usage
        yield bottle.template("""
            <div id="section-usage" class="section hidden">
                <h2>Coming <a href="http://wiki.{{host}}/Soon™">soon™</a></h2>
            </div>
        """, host=ati.host)
    yield from ati.html_exceptions(body())
    yield ati.footer(additional_js="""
        selectTabWithID("tab-general");
        bindTabEvents();
    """)
