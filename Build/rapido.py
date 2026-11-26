from judge_assets import src, readgl, tmp
from PIL import Image
import json, struct
from pathlib import Path

parts = {
    "Body_LowerReceiver": "Body",
    "Bolt_Hammer": "Bolt_Hammer",
    "Barrel_Rapido": "Barrel_Frame",
    "Grip_Rapido": "Grip",
    "Mag_Standard": "Mag_Standard",
}


def load_parts(write_textures=False):
    result = {}
    folder = tmp / "Unity/Assets/RapidoMaterials"
    if write_textures:
        folder.mkdir(exist_ok=True)
    for key, name in parts.items():
        file = next(src.rglob("SK_WP_Revolver_Justicar_Rapido_" + name + ".glb"))
        mesh = readgl(file)
        data = file.read_bytes()
        doc = json.loads(data[20 : 20 + struct.unpack_from("<I", data, 12)[0]])
        primitives = doc["meshes"][0]["primitives"]
        maps = []
        start = 0
        for column, primitive in enumerate(primitives):
            count = doc["accessors"][primitive["attributes"]["POSITION"]]["count"]
            mat = doc["materials"][primitive["material"]]["name"]
            tex_name = mat.replace("MI_Revolver_", "T_") + "_BR.png"
            if write_textures:
                maps.append(
                    Image.open(next(src.rglob(tex_name)))
                    .convert("RGB")
                    .resize((1024, 1024))
                )
            if len(primitives) > 1:
                uv = mesh["uv"][start : start + count, 0]
                uv[:] = (uv.clip(0, 1) + column) / len(primitives)
            start += count
        mesh["mat"] = "Rapido_" + name
        result[key] = mesh
        if write_textures:
            atlas = Image.new("RGB", (len(maps) * 1024, 1024))
            for column, texture in enumerate(maps):
                atlas.paste(texture, (column * 1024, 0))
            atlas.save(folder / (mesh["mat"] + ".png"))
    return result


if __name__ == "__main__":
    load_parts(True)
