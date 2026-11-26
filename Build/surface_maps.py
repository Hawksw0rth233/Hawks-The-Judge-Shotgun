"""Bake PD3 packed surface maps for the Unity Standard material workflow."""

import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image

root = Path(__file__).resolve().parents[2]
assets = Path("E:/Temp/Justicar-RSh/Unity/Assets")
files = {
    p.name.lower(): p
    for tree in ("Export", "Ammo")
    for p in (root / tree).rglob("*")
    if p.is_file()
}


def texture(name):
    return Image.open(files[(name.split(".")[-1] + ".png").lower()]).convert("RGBA")


def write(folder, name, color, normal, metallic, roughness, ao):
    path = folder / "Surface"
    path.mkdir(exist_ok=True)
    color.convert("RGB").save(folder / (name + ".png"))
    x, y, _, _ = normal.split()
    nx, ny = [np.asarray(c, dtype="float32") / 127.5 - 1 for c in (x, y)]
    z = Image.fromarray(
        ((np.sqrt(np.maximum(0, 1 - nx * nx - ny * ny)) + 1) * 127.5).astype("uint8")
    )
    Image.merge("RGB", (x, y.point(lambda p: 255 - p), z)).save(
        path / (name + "_normal.png")
    )
    Image.merge(
        "RGBA", (metallic, ao, metallic, roughness.point(lambda p: 255 - p))
    ).save(path / (name + "_surface.png"))


def standard(pattern="*.mat", folder=assets / "JudgeMaterials"):
    for mat in folder.glob(pattern):
        data = json.loads(
            files[(mat.stem + ".json").lower()].read_text(encoding="utf-8-sig")
        )
        tex = data["Textures"]
        if not ("NAC" in tex and "URCS" in tex):
            continue
        normal, mask = texture(tex["NAC"]), texture(tex["URCS"])
        channels = mask.split()
        params = data["Parameters"]
        # Approximate PD3's layered paint in a single pass, retaining authored palette and curvature.
        palette = params.get("Colors", {})
        colors = [
            bytes.fromhex(
                palette.get(f"Color00{i:02}", palette.get("Color0000", {})).get(
                    "Hex", "575757"
                )[:6]
            )
            for i in range(4)
        ]
        rail = mat.stem.lower() == "mi_shotgun_justicar_rails"
        if rail:
            colors = [bytes([shade] * 3) for shade in (77, 68, 86, 72)]
        table = np.array([list(c) for c in colors], float)
        values = np.arange(256) * 3 / 255
        ramps = [np.interp(values, np.arange(4), table[:, i]) for i in range(3)]
        color = Image.merge("RGB", tuple(channels[2].point(a.tolist()) for a in ramps))
        base = np.asarray(color, dtype="float32")
        curvature = (
            np.asarray(normal.getchannel("A").resize(color.size), dtype="float32") / 255
        )
        color = Image.fromarray(
            np.clip(base * (0.8 + 0.4 * curvature[:, :, None]), 0, 255).astype("uint8")
        )
        metal = [
            params.get("Scalars", {}).get(f"NRC_Metallic{i:02}", 0) for i in range(4)
        ]
        grip = "grip" in mat.stem.lower()
        metallic = channels[0].point(
            (np.interp(values, np.arange(4), metal) * 255).tolist()
        )
        if rail:
            metallic = channels[0].point(lambda p: 191 + p * 0.18)
        if grip:
            metallic = metallic.point(lambda p: p * 0.07)
        foregrip = mat.stem.lower() == "mi_shotgun_justicar_barrel_foregrip"
        if foregrip:
            # The exposed handguard uses the rubber layer, with metal limited
            # to the secondary regions of the authored material mask.
            metallic = channels[2].point(
                (np.interp(values, np.arange(4), metal) * 255).tolist()
            )
        roughness = channels[1].point(lambda p: 124 + p * 0.45) if grip else channels[1]
        if rail:
            roughness = channels[1].point(lambda p: 90 + p * 0.36)
        if foregrip:
            roughness = channels[1].point(lambda p: 110 + p * 0.55)
        write(
            folder,
            mat.stem,
            color,
            normal,
            metallic,
            roughness,
            normal.getchannel("B").resize(mask.size),
        )


def legendary():
    folder = assets / "RapidoMaterials"
    for mat in folder.glob("*.mat"):
        part = mat.stem.removeprefix("Rapido_")
        blob = files[
            ("SK_WP_Revolver_Justicar_Rapido_" + part + ".glb").lower()
        ].read_bytes()
        doc = json.loads(blob[20 : 20 + struct.unpack_from("<I", blob, 12)[0]])
        columns = []
        for prim in doc["meshes"][0]["primitives"]:
            material = doc["materials"][prim["material"]]["name"]
            tex = json.loads(
                files[(material + ".json").lower()].read_text(encoding="utf-8-sig")
            )["Textures"]
            columns.append((texture(tex["BR"]), texture(tex["NM"])))
        side = max(im.width for pair in columns for im in pair)

        def atlas(index):
            result = Image.new("RGBA", (side * len(columns), side))
            for i, pair in enumerate(columns):
                result.paste(pair[index].resize((side, side)), (i * side, 0))
            return result

        br, nm = atlas(0), atlas(1)
        write(
            folder,
            mat.stem,
            br,
            nm,
            nm.getchannel("A"),
            br.getchannel("A"),
            Image.new("L", br.size, 255),
        )


if __name__ == "__main__":
    standard()
    legendary()
