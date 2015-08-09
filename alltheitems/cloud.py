import alltheitems.__main__ as ati
import api
import json
import pathlib

def chest_iter():
    """Returns an iterator yielding tuples (x, corridor, y, floor, z, chest)."""
    with (ati.assets_root / 'json/cloud.json').open() as cloud_json:
        cloud_data = json.load(cloud_json)
    for y, floor in enumerate(cloud_data):
        for x, corridor in sorted(((int(x), corridor) for x, corridor in floor.items()), key=lambda tup: tup[0]):
            for z, chest in enumerate(corridor):
                yield x, corridor, y, floor, z, chest

def chest_background_color(cloud_chest):
    exists = cloud_chest.get('exists', True)
    has_smart_chest = cloud_chest.get('hasSmartChest', True)
    has_sorter = cloud_chest.get('hasSorter', exists)
    has_overflow = cloud_chest.get('hasOverflow', exists)
    stackable = ati.item_info_from_stub(cloud_chest).get('stackable', True)
    if stackable and has_sorter and not has_overflow:
        return '#f00'
    elif not exists:
        return '#777'
    elif not has_smart_chest:
        return '#f70'
    elif not stackable:
        return '#0ff'
    elif not has_sorter:
        return '#ff0'
    else:
        return 'transparent'

def image_from_chest(cloud_chest):
    return '<td style="background-color: {};">{}</td>'.format(chest_background_color(cloud_chest), ati.item_stub_image(cloud_chest))

def index():
    yield ati.header(title='Cloud')
    def body():
        yield '<p>The <a href="http://wiki.{host}/Cloud">Cloud</a> is the public item storage on <a href="http://{host}/">Wurstmineberg</a>, consisting of 6 underground floors with <a href="http://wiki.{host}/SmartChest">SmartChests</a> in them.</p>'.format(host=ati.host)
        color_explanations = {
            '#f00': '<p>A red background means that the chest has a sorter but the SmartChest and/or the overflow is missing. This can break other SmartChests, so it should be fixed as soon as possible!</p>',
            '#777': "<p>A gray background means that the chest hasn't been built yet or is still located somewhere else.</p>",
            '#f70': "<p>An orange background means that the chest doesn't have a SmartChest yet. It can only store 54 stacks.</p>",
            '#0ff': '<p>A cyan background means that the chest has no sorter because it stores an unstackable item. These items should not be automatically <a href="http://wiki.wurstmineberg.de/Soup#Cloud">sent</a> to the Cloud.</p>',
            '#ff0': "<p>A yellow background means that the chest doesn't have a sorter yet.</p>",
            'transparent': '<p>A white background means that everything is okay: the chest has a SmartChest, a sorter, and overflow protection.</p>'
        }
        explained_colors = set()
        for _, _, _, _, _, chest in chest_iter():
            chest_color = chest_background_color(chest)
            if chest_color not in explained_colors:
                if chest_color != 'transparent':
                    yield color_explanations[chest_color]
                explained_colors.add(chest_color)
        if 'transparent' in explained_colors and len(explained_colors) > 1:
            yield color_explanations['transparent']
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
        for x, corridor, y, floor, z, chest in chest_iter():
            if y not in floors:
                floors[y] = floor
        for y, floor in sorted(floors.items(), key=lambda tup: tup[0]):
            yield bottle.template("""
                %import itertools
                <h2 id="floor{{y}}">{{y}}{{ati.ordinal(y)}} floor (y={{73 - 10 * y}})</h2>
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
            """, ati=ati, image=image_from_chest, floor=floor, y=y)
    yield from ati.html_exceptions(body())
    yield ati.footer(linkify_headers=True)
