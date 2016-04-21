import alltheitems.__main__ as ati

import api.util2
import api.v2
import enum
import minecraft

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

    def block_at(self, x, y, z, dimension=api.util2.Dimension.overworld, *, chunk_cache=None):
        if chunk_cache is None:
            chunk_cache = {}
        chunk_x, block_x = divmod(x, 16)
        chunk_y, block_y = divmod(y, 16)
        chunk_z, block_z = divmod(z, 16)
        if (chunk_x, chunk_y, chunk_z) not in chunk_cache:
            chunk_cache[chunk_x, chunk_y, chunk_z] = api.v2.api_chunk_info(self.world, dimension, chunk_x, chunk_y, chunk_z)
        return chunk_cache[chunk_x, chunk_y, chunk_z][block_y][block_z][block_x]
