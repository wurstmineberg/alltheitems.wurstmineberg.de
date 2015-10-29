import alltheitems.__main__ as ati

import api.v2
import enum
import minecraft

class Dimension(enum.Enum):
    overworld = 0
    nether = -1
    end = 1

class World:
    def __init__(self, world=None):
        if world is None:
            self.world = minecraft.World()
        elif isinstance(world, minecraft.World):
            self.world = world
        elif isinstance(world, str):
            self.world = minecraft.World(world)
        else:
            raise TypeError('Invalid world type: {}'.format(type(world)))

    def block_at(self, x, y, z, dimension=Dimension.overworld):
        chunk_x, block_x = divmod(x, 16)
        chunk_y, block_y = divmod(y, 16)
        chunk_z, block_z = divmod(z, 16)
        chunk = {
            Dimension.overworld: api.v2.chunk_info_overworld,
            Dimension.nether: api.v2.chunk_info_nether,
            Dimension.end: api.v2.chunk_info_end
        }[dimension](self.world, chunk_x, chunk_y, chunk_z)
        return chunk[block_y][block_z][block_x]
