import alltheitems.__main__ as ati

import enum
import json
import more_itertools

class OrderedEnum(enum.Enum):
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

def format_num(number, ord=False):
    result = ''.join(list(reversed('\u202f'.join(''.join(l) for l in more_itertools.chunked(reversed(str(number)), 3)))))
    if ord:
        result += ordinal(number)
    return result

def inventory_table(rows, *, table_id=None, style=None, items_data=None):
    import alltheitems.item

    if items_data is None:
        with (ati.assets_root / 'json' / 'items.json').open() as items_file:
            items_data = json.load(items_file)
    result = '<table class="inventory-table"'
    if table_id is not None:
        result += ' id="{}"'.format(table_id)
    if style is not None:
        result += ' style="{}"'.format(style)
    result += '>\n'
    for row, cells in enumerate(rows):
        result += '<tr class="inv-row inv-row-{}">\n'.format(row)
        for col, cell in enumerate(row):
            result += '<td class="inv-cell inv-cell-{}">\n'.format(col)
            if isinstance(cell, dict) and 'Count' in cell:
                item = alltheitems.item.Item.from_slot(cell)
            elif isinstance(cell, dict) and 'count' in cell:
                item = alltheitems.item.Item(cell)
            else:
                item = alltheitems.item.Item(cell)
            result += item.image(slot=True)
            result += '</td>\n'
        result += '</tr>\n'
    result += '</table>\n'
    return result

def join(sequence, *, word='and', default=None):
    sequence = [str(elt) for elt in sequence]
    if len(sequence) == 0:
        if default is None:
            raise IndexError('Tried to join empty sequence with no default')
        else:
            return str(default)
    elif len(sequence) == 1:
        return sequence[0]
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
