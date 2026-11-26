"""Read the factory Justicar muzzle whitelist and its gameplay tags from PD3."""
import json
from judge_assets import P, src, readgl, tmp

root = P / 'Muzzles'
def document(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def parts():
    shared = document(next(root.rglob('DA_SharedParts_BarrelExt_12G.json')))
    result = {}
    for ref in shared['Properties']['SharedModParts']:
        stem = ref['ObjectPath'].split('/')[-1].split('.')[0]
        props = document(next(root.rglob(stem + '.json')))['Properties']
        mesh = props['ModularMeshes'][0]['SkeletalMesh']['AssetPathName'].split('.')[-1]
        name = stem.removeprefix('WPD_BarrelExt_')
        key = 'BarrelExtension_' + ('MuzzleBreak' if name == 'SilentKiller' else name)
        search = src if name == 'SilentKiller' else root
        result[key] = (name, next(search.rglob(mesh + '.glb')), 'Weapon.Parts.BarrelExtension.Suppressor' in props.get('AddTagToWeapon', []))
    return result

def bake():
    import shutil
    import surface_maps as surf
    from PIL import Image
    folder = tmp/'Unity/Assets/JudgeMuzzles'
    folder.mkdir(exist_ok=True)
    surf.files.update({p.name.lower():p for p in root.rglob('*') if p.is_file()})
    for name, model, _ in parts().values():
        if name=='SilentKiller':continue
        mat=readgl(model)['mat']
        dest=folder/(mat+'.mat')
        if not dest.exists():shutil.copyfile(next((tmp/'Unity/Assets/JudgeMaterials').glob('*Barrel_Medium.mat')),dest)
        textures=document(surf.files[(mat+'.json').lower()])['Textures']
        if 'NAC' in textures:
            surf.standard(dest.name,folder)
        else:
            color=surf.texture(textures['BR'])
            normal=surf.texture(textures['NM'])
            mask=surf.texture(textures['MOS'])
            surf.write(folder,mat,color,normal,mask.getchannel('R'),mask.getchannel('B').point(lambda x:255-x),mask.getchannel('G'))
if __name__=='__main__':bake()

