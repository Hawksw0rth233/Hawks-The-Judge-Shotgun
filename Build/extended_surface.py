"""Rebake the Extended barrel handguard without changing its material references."""
from pathlib import Path
import shutil
import tempfile

from PIL import Image
import UnityPy

from judge_assets import pkg, tmp
from surface_maps import standard

NAME = 'MI_Shotgun_justicar_Barrel_ForeGrip'

def build():
    path = pkg/'bundles/hawks_judge_foregrip_material.bundle'
    env = UnityPy.load(str(path))
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        material = NAME+'.mat'
        shutil.copyfile(tmp/'Unity/Assets/JudgeForeGrip'/material, output/material)
        standard(material, output)
        inputs = {NAME: output/(NAME+'.png'),
                  NAME+'_surface': output/'Surface'/(NAME+'_surface.png')}
        for name, image_path in inputs.items():
            obj, = (o for o in env.objects if o.type.name == 'Texture2D' and o.peek_name() == name)
            texture = obj.read()
            with Image.open(image_path) as image:
                assert image.size == (texture.m_Width, texture.m_Height)
                texture.image = image.convert('RGBA')
                texture.save()
    path.write_bytes(next(iter(env.files.values())).save(packer='lz4'))

if __name__ == '__main__':
    build()
