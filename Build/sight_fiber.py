from PIL import ImageDraw
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from judge_assets import *

def sight_fiber_mask(size):
    front = geo['FrontSight_Standard']
    vertices, indices = np.unique(front['v'].round(6), axis=0, return_inverse=True)
    faces = indices[front['tri']]
    edges = coo_matrix((np.ones(faces.size), (faces.ravel(), np.roll(faces, 1, axis=1).ravel())),
                       shape=(len(vertices), len(vertices)))
    count, islands = connected_components(edges, directed=False)
    fiber, = [i for i in range(count) if np.ptp(vertices[islands == i, 0]) > .01
              and vertices[islands == i, 1].min() > .003]
    mask = Image.new('L', size)
    metal = Image.new('L', size)
    draw_fiber, draw_metal = ImageDraw.Draw(mask), ImageDraw.Draw(metal)
    scale = np.array(size) - 1
    for shape, mesh in (('front', front), ('rear', geo['RearSight_Standard'])):
        for index, face in enumerate(mesh['tri']):
            drawer = draw_fiber if shape == 'front' and islands[faces[index, 0]] == fiber else draw_metal
            drawer.polygon([tuple(uv) for uv in mesh['uv'][face] * scale], fill=255)
    overlap = np.count_nonzero(np.asarray(mask) & np.asarray(metal))
    print(f'Fiber pixels: {np.count_nonzero(mask)}, shared texture boundary: {overlap}')
    return mask

def build_sight_material():
    path = pkg/'bundles/hawks_judge_materials.bundle'
    env = UnityPy.load(str(path))
    objects = {o.peek_name(): o for o in env.objects if o.type.name == 'Texture2D'}
    base = objects['MI_Shotgun_justicar_Sights'].read()
    surface = objects['MI_Shotgun_justicar_Sights_surface'].read()
    source = json.loads(next(src.rglob('MI_Shotgun_justicar_Sights.json')).read_text(encoding='utf-8-sig'))
    color = '#'+source['Parameters']['Colors']['Color0101']['Hex'][:6]
    mask = sight_fiber_mask(base.image.size)
    base.image = Image.composite(Image.new('RGBA', base.image.size, color), base.image.convert('RGBA'), mask)
    base.save()
    image = surface.image.convert('RGBA')
    diffuse_fiber = Image.merge('RGBA', (Image.new('L', image.size, 0), image.getchannel('G'),
                                        Image.new('L', image.size, 0), Image.new('L', image.size, 145)))
    surface.image = Image.composite(diffuse_fiber, image, mask.resize(image.size))
    surface.save()
    path.write_bytes(next(iter(env.files.values())).save(packer='lz4'))

if __name__ == '__main__':
    build_sight_material()
