from judge_assets import *
from tangent_space import tangents
from actions import rest, static, clipcab, clipkey
from UnityPy.streams import EndianBinaryReader
from copy import deepcopy
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
import sys

rapido = "--rapido" in sys.argv
muzzles = "--muzzles" in sys.argv
payday = "--payday" in sys.argv
rapido_body = "--rapido-body" in sys.argv
rail_only = "--rail" in sys.argv
rapido = rapido or rapido_body
if payday:
    geo["Barrel_Payday"] = geo["Barrel_Standard"]
if muzzles:
    from muzzle_parts import parts

    geo = {
        k: readgl(model)
        for k, (name, model, _) in parts().items()
        if name != "SilentKiller"
    }
if rapido:
    from rapido import load_parts

    geo = load_parts()
matfile = (
    pkg
    / "bundles"
    / (
        "hawks_judge_rapido_materials.bundle"
        if rapido
        else "hawks_judge_materials.bundle"
    )
)
if muzzles:
    matfile = pkg / "bundles/hawks_judge_muzzle_materials.bundle"
me = UnityPy.load(str(matfile))
mcab = next(k for k in next(iter(me.files.values())).files if not k.endswith(".resS"))
mats = {o.peek_name(): o.path_id for o in me.objects if o.type.name == "Material"}


def makeid(s):
    return hashlib.sha256(("team.aminus.thejudge/" + s).encode()).hexdigest()[:24]


def key(s):
    return "hawks_judge_" + s.lower() + ".bundle"


def ref(b):
    return idle[names.index(b)].astype(float)


bodyorigin = np.array([0.31817049, -0.07415094, 1.54991138])
barorigin = np.array([0.40070516, -0.07415163, 1.54990888])
origins = {
    "Body_LowerReceiver": bodyorigin,
    "Mag_Standard": piv["Mag"],
    "Bolt_Hammer": piv["Bolt"],
}
# Standalone EFT modification prefabs face +Z in their root and -Y in the mesh.
A = np.array([[0, 0, 1], [-1, 0, 0], [0, 1, 0.0]])


def pieces(k, rot, offset, group=None):
    g = geo[k]
    ts = g["tri"]
    tri = ts if group is None else ts[g["groups"][ts[:, 0]] == group]
    idx, rev = np.unique(tri, return_inverse=True)
    v = g["v"][idx] @ rot.T + offset
    n = g["n"][idx] @ rot.T
    uv = g["uv"][idx].copy()
    uv[:, 1] = 1 - uv[:, 1]
    tri = rev.reshape(-1, 3)
    return v, n, uv, tri[:, ::-1] if np.linalg.det(rot) < 0 else tri, g["mat"]


def mounted(k, bn, group=None):
    r = rest[names.index(bn)]
    return pieces(
        k, r[:3, :3].T @ axes, r[:3, :3].T @ (world(origins[k]) - r[:3, 3]), group
    )


def loddata(m):
    n = m.lower()
    if "weapon_kbp" in n:
        return mounted("Body_LowerReceiver", "weapon", "Body")
    if "release_lod" in n:
        return mounted("Body_LowerReceiver", "weapon_mag_release", "MagRelease")
    if "trigger_lod" in n:
        return mounted("Body_LowerReceiver", "mod_trigger", "Trigger")
    if "hammer_lod" in n:
        return mounted("Bolt_Hammer", "mod_hammer")
    if "cylinder_axis" in n:
        return mounted("Mag_Standard", "weapon_cylinder_axis", "Hinge")
    if "extractor" in n:
        return mounted("Mag_Standard", "weapon_extractor", "Ejector")
    return None


def setmesh(o, geom):
    v, n, u, tr, mat = geom
    t = o.read_typetree()
    c = t["m_VertexData"]["m_Channels"]
    for ch in c:
        ch.update(stream=0, offset=0, format=0, dimension=0)
    for ix, offset, d in [(0, 0, 3), (1, 12, 3), (2, 24, 4), (4, 40, 2)]:
        c[ix].update(offset=offset, dimension=d)
    t["m_StreamData"] = {"offset": 0, "size": 0, "path": ""}
    t["m_VertexData"].update(
        m_VertexCount=len(v),
        m_DataSize=np.column_stack((v, n, tangents(v, n, u, tr), u))
        .astype("<f4")
        .tobytes(),
    )
    t["m_IndexFormat"] = 0
    t["m_IndexBuffer"] = tr.astype("<u2").tobytes()
    assert len(v) < 65536 and len(tr) > 0
    bb = {
        "m_Center": xyz((v.max(0) + v.min(0)) / 2),
        "m_Extent": xyz((v.max(0) - v.min(0)) / 2),
    }
    t["m_LocalAABB"] = bb
    t["m_SubMeshes"] = [
        dict(
            firstByte=0,
            indexCount=int(tr.size),
            topology=0,
            baseVertex=0,
            firstVertex=0,
            vertexCount=len(v),
            localAABB=bb,
        )
    ]
    o.save_typetree(t)
    return t


rootdb = json.loads(
    pathlib.Path(
        "E:/SPT 4.1.6/SPT_Runtime/SPT_Data/database/templates/items.json"
    ).read_text(encoding="utf8")
)
donor = {
    k: rootdb[id]["_props"]["Prefab"]["path"]
    for k, id in [
        ("gun", "633ec7c2a6918cb895019c6c"),
        ("mag", "633ec6ee025b096d320a3b15"),
        ("grip", "633ec8e4025b096d320a3b1e"),
        ("ammo", "5a38ebd9c4a282000d722a5b"),
    ]
}
clips = {
    o.path_id
    for o in UnityPy.load(str(pkg / "bundles" / clipkey)).objects
    if o.type.name == "AnimationClip"
}
manifest = [
    dict(key=matfile.name, dependencyKeys=[]),
    dict(key=clipkey, dependencyKeys=[]),
]
targets = ([] if muzzles else ["weapon"]) + [
    k
    for k in geo
    if k not in ["Body_LowerReceiver", "Bolt_Hammer", "SpeedLoader"]
    and not k.startswith("SM_")
]
if payday:
    targets = ["Barrel_Payday"]
if rapido_body:
    targets = ["weapon"]
if rail_only:
    targets = ["SightMount_Standard"]
for k in targets:
    gun = k == "weapon"
    ismag = k == "Mag_Standard"
    srcname = donor[
        "gun" if gun else "mag" if ismag else "ammo" if k == "ammo" else "grip"
    ]
    dest = key(
        {"weapon": "weapon_rapido", "Mag_Standard": "Mag_Rapido"}.get(k, k)
        if rapido
        else k
    )
    env = UnityPy.load(str(base / srcname))
    bundle = next(iter(env.files.values()))
    cab = next(x for x in bundle.files if not x.endswith(".resS"))
    sf = bundle.files[cab]
    newcab = "CAB-" + uuid.uuid5(uuid.NAMESPACE_URL, dest).hex
    ext = copy.copy(sf.externals[0])
    ext.path = "archive:/" + mcab + "/" + mcab
    ext.guid = bytes(16)
    sf.externals.append(ext)
    extid = len(sf.externals)
    if k == "Barrel_Extended":
        forekey = "hawks_judge_foregrip_material.bundle"
        fore = UnityPy.load(str(pkg / "bundles" / forekey))
        material = next(
            o
            for o in fore.objects
            if o.type.name == "Material"
            and o.peek_name() == geo[k]["material_names"][1]
        )
        forecab = material.assets_file.name
        other = copy.copy(ext)
        other.path = "archive:/" + forecab + "/" + forecab
        sf.externals.append(other)
        foreptr = dict(m_FileID=len(sf.externals), m_PathID=material.path_id)
        manifest.append(dict(key=forekey, dependencyKeys=[]))
    if gun:
        mpkey = "assets/content/audio/banks/mr153.bundle"
        mp = UnityPy.load(
            str(base / rootdb["606dae0ab0e443224b421bb7"]["_props"]["Prefab"]["path"])
        )
        sound = next(
            o
            for o in mp.objects
            if o.type.name == "MonoBehaviour" and "BodySilenced" in o.read_typetree()
        )
        body = sound.read_typetree()["BodySilenced"].copy()
        bankext = copy.copy(sound.assets_file.externals[body["m_FileID"] - 1])
        animExt = copy.copy(ext)
        animExt.path = "archive:/" + clipcab + "/" + clipcab
        sf.externals.append(animExt)
        aid = len(sf.externals)
        sf.externals.append(bankext)
        body["m_FileID"] = len(sf.externals)
    objs = list(env.objects)
    gob = {o.path_id: o for o in objs if o.type.name == "GameObject"}
    trans = {
        o.read_typetree()["m_GameObject"]["m_PathID"]: o
        for o in objs
        if o.type.name == "Transform"
    }
    geometries = {}
    integrals = {}
    for o in objs:
        if o.type.name != "Mesh":
            continue
        name = o.peek_name()
        if gun:
            g = loddata(name)
        elif k == "ammo":
            g = pieces(
                "SM_WP_Ammo_410GA" + ("_Empty" if "_shell_" in name else ""),
                A,
                np.zeros(3),
            )
        elif ismag:
            g = pieces(k, np.diag([-1.0, 1.0, -1.0]) @ A, np.zeros(3), "Mag")
        else:
            g = pieces(k, A, np.zeros(3))
        integral = None
        if k == "Barrel_Payday":
            x, y, z = geo["Barrel_Standard"]["nodes"]["BarrelExtension"]
            integral = pieces("BarrelExtension_MuzzleBreak", A, np.array([z, -x, y]))
        elif rapido_body and g is not None and "weapon_kbp" in name.lower():
            frame = rest[names.index("weapon")]
            integral = pieces(
                "Grip_Rapido",
                frame[:3, :3].T @ axes,
                frame[:3, :3].T @ (world(piv["Grip"]) - frame[:3, 3]),
            )
        if integral is not None:
            v, n, uv, tri, mat = g
            iv, inn, iu, it, im = integral
            first_count = tri.size
            g = (
                np.concatenate((v, iv)),
                np.concatenate((n, inn)),
                np.concatenate((uv, iu)),
                np.concatenate((tri, it + len(v))),
                mat,
            )
            integrals[o.path_id] = (first_count, im)
        geometries[o.path_id] = g
        if g is not None:
            data = setmesh(o, g)
            if o.path_id in integrals:
                first_count, _ = integrals[o.path_id]
                template = data["m_SubMeshes"][0]
                triangles = g[3].ravel()
                data["m_SubMeshes"] = []
                for start, end in ((0, first_count), (first_count, len(triangles))):
                    indices = triangles[start:end]
                    points = g[0][indices]
                    bounds = dict(
                        m_Center=xyz((points.max(0) + points.min(0)) / 2),
                        m_Extent=xyz((points.max(0) - points.min(0)) / 2),
                    )
                    data["m_SubMeshes"].append(
                        dict(
                            template,
                            firstByte=start * 2,
                            indexCount=end - start,
                            firstVertex=int(indices.min()),
                            vertexCount=int(indices.max() - indices.min() + 1),
                            localAABB=bounds,
                        )
                    )
                o.save_typetree(data)
            if k == "Barrel_Extended":
                template = data["m_SubMeshes"][0]
                parts = []
                start = 0
                for count in geo[k]["index_counts"]:
                    indices = g[3].ravel()[start : start + count]
                    points = g[0][indices]
                    bounds = dict(
                        m_Center=xyz((points.max(0) + points.min(0)) / 2),
                        m_Extent=xyz((points.max(0) - points.min(0)) / 2),
                    )
                    parts.append(
                        dict(
                            template,
                            firstByte=start * 2,
                            indexCount=count,
                            firstVertex=int(indices.min()),
                            vertexCount=int(indices.max() - indices.min() + 1),
                            localAABB=bounds,
                        )
                    )
                    start += count
                assert start == g[3].size
                data["m_SubMeshes"] = parts
                o.save_typetree(data)
        else:
            setmesh(
                o,
                (
                    np.zeros((3, 3)),
                    np.zeros((3, 3)),
                    np.zeros((3, 2)),
                    np.array([[0, 1, 2]]),
                    None,
                ),
            )
    filters = {
        o.read_typetree()["m_GameObject"]["m_PathID"]: o.read_typetree()["m_Mesh"][
            "m_PathID"
        ]
        for o in objs
        if o.type.name == "MeshFilter"
    }
    for o in objs:
        if o.type.name == "MeshRenderer":
            d = o.read_typetree()
            go = d["m_GameObject"]["m_PathID"]
            mid = filters.get(go)
            if mid not in geometries:
                continue
            g = geometries[mid]
            if g is None:
                d["m_Enabled"] = False
            else:
                d["m_Materials"] = [dict(m_FileID=extid, m_PathID=mats[g[-1]])]
            if mid in integrals:
                d["m_Materials"].append(
                    dict(m_FileID=extid, m_PathID=mats[integrals[mid][1]])
                )
            if k == "Barrel_Extended":
                d["m_Materials"].append(foreptr)
            o.save_typetree(d)
    # New attachment transforms exist in both first- and third-person native hierarchies.
    extra = []
    parents = {}

    def addslot(parent, name, pos, rot=(0, 0, 0, 1)):
        go = copy.copy(gob[parent.read_typetree()["m_GameObject"]["m_PathID"]])
        t = copy.copy(parent)
        go.path_id = 1000000 + len(extra)
        t.path_id = go.path_id + 1
        extra.extend([go.path_id, t.path_id])
        sf.objects[go.path_id] = go
        sf.objects[t.path_id] = t
        gd = go.read_typetree()
        gd.update(m_Name=name, m_Component=[{"component": pointer(t.path_id)}])
        go.save_typetree(gd)
        td = parents.setdefault(parent.path_id, parent.read_typetree())
        child = deepcopy(td)
        child.update(
            m_Children=[],
            m_Father=pointer(parent.path_id),
            m_GameObject=pointer(go.path_id),
            m_LocalPosition=xyz(pos),
            m_LocalRotation=dict(zip("xyzw", map(float, rot))),
            m_LocalScale=xyz([1, 1, 1]),
        )
        t.save_typetree(child)
        td["m_Children"].append(pointer(t.path_id))
        parent.save_typetree(td)

    for goid, go in gob.items():
        n = go.peek_name()
        t = trans.get(goid)
        if gun and n == "weapon":
            r = ref("weapon")
            addslot(t, "mod_barrel", r[:3, :3].T @ (world(barorigin) - r[:3, 3]))
        if gun and n in static:
            d = t.read_typetree()
            v = d["m_LocalPosition"]
            d["m_LocalPosition"] = xyz(np.array([v[c] for c in "xyz"]) + static[n])
            t.save_typetree(d)
        if (
            k in ("SightMount_Standard", "Barrel_Rapido")
            and t
            and t.read_typetree()["m_Father"]["m_PathID"] == 0
        ):
            if k == "SightMount_Standard":
                x, y, z = geo[k]["nodes"]["Sight"]
                rail = geo[k]["v"]
                x = (rail[:, 0].min() + rail[:, 0].max()) / 2
            else:
                rail = geo[k]["v"]
                top = rail[rail[:, 1] > rail[:, 1].max() - 0.0005]
                x, y, z = (top[:, 0].min() + top[:, 0].max()) / 2, top[:, 1].max(), 0
            addslot(
                t,
                "mod_scope",
                [z, y - 0.001, x],
                Rot.from_euler("x", -90, degrees=True).as_quat(),
            )
        if (
            k.startswith("Barrel_")
            and t
            and t.read_typetree()["m_Father"]["m_PathID"] == 0
        ):
            if k != "Barrel_Rapido":
                for slot, pos in {
                    "mod_sight_rear": [-7.79e-07, 0.016356123, -0.077986149],
                    "mod_mount": [2.238e-06, 0.015203123, -0.06933515],
                }.items():
                    addslot(
                        t, slot, pos, Rot.from_euler("x", -90, degrees=True).as_quat()
                    )
            for slot, bone in [
                ("mod_sight_front", "FrontSight"),
                ("mod_muzzle", "BarrelExtension"),
            ]:
                if k == "Barrel_Payday" and slot == "mod_muzzle":
                    continue
                pos = geo[k]["nodes"][bone]
                addslot(
                    t,
                    slot,
                    np.array([pos[2], pos[1], pos[0]]),
                    Rot.from_euler("x", -90, degrees=True).as_quat(),
                )
    for o in objs:
        if gun and o.type.name in ["AnimatorController", "AnimatorOverrideController"]:
            d = o.read_typetree()

            def redirect(data):
                if isinstance(data, dict):
                    if data.get("m_FileID") == 1 and data.get("m_PathID") in clips:
                        data["m_FileID"] = aid
                    for v in data.values():
                        redirect(v)
                elif isinstance(data, list):
                    for v in data:
                        redirect(v)

            redirect(d)
            o.save_typetree(d)
        if (
            k.startswith("BarrelExtension_") or k == "Barrel_Payday"
        ) and o.type.name == "MonoBehaviour":
            data = o.read_typetree()
            if "pivotPosition" in data:
                vertices = pieces(k, A, np.zeros(3))[0]
                if k == "Barrel_Payday":
                    x, y, z = geo[k]["nodes"]["BarrelExtension"]
                    vertices = np.concatenate(
                        (
                            vertices,
                            pieces(
                                "BarrelExtension_MuzzleBreak", A, np.array([z, -x, y])
                            )[0],
                        )
                    )
                x, y, z = (vertices.min(0) + vertices.max(0)) / 2
                data["pivotPosition"] = xyz([x, z, -y])
                data["Icon"]["boundsScale"] = 1.0
                o.save_typetree(data)
        if gun and o.type.name == "MonoBehaviour":
            d = o.read_typetree()
            if "BodySilenced" in d:
                d["BodySilenced"] = body
                o.save_typetree(d)
        if o.type.name == "AssetBundle":
            d = o.read_typetree()
            d["m_Name"] = d["m_AssetBundleName"] = dest
            d["m_Dependencies"].append(mcab.lower())
            container = []
            if gun:
                d["m_Dependencies"].append(clipcab.lower())
                for ptr in d["m_PreloadTable"]:
                    if ptr["m_FileID"] == 1 and ptr["m_PathID"] in clips:
                        ptr["m_FileID"] = aid
            if gun:
                d["m_Dependencies"].append(bankext.path.rsplit("/", 1)[-1].lower())
            if k == "Barrel_Extended":
                d["m_Dependencies"].append(forecab.lower())
            for name, entry in d["m_Container"]:
                additions = (
                    [body] if gun else [foreptr] if k == "Barrel_Extended" else []
                )
                if extra or additions:
                    old = d["m_PreloadTable"][
                        entry["preloadIndex"] : entry["preloadIndex"]
                        + entry["preloadSize"]
                    ]
                    entry["preloadIndex"] = len(d["m_PreloadTable"])
                    adds = [pointer(i) for i in extra] + additions
                    d["m_PreloadTable"].extend(old + adds)
                    entry["preloadSize"] = len(old) + len(adds)
                container.append(
                    (
                        name.replace(
                            pathlib.Path(srcname).stem, pathlib.Path(dest).stem
                        ),
                        entry,
                    )
                )
            d["m_Container"] = container
            o.save_typetree(d)
        elif o.type.name == "AudioClip":
            d = o.read_typetree()
            resource = d.get("m_Resource", {})
            path = resource.get("m_Source", "")
            if cab in path:
                resource["m_Source"] = path.replace(cab, newcab)
                o.save_typetree(d)
        elif o.type.name == "Texture2D":
            d = o.read_typetree()
            stream = d.get("m_StreamData", {})
            path = stream.get("path", "")
            if cab in path:
                stream["path"] = path.replace(cab, newcab)
                o.save_typetree(d)
    bundle.files = {n.replace(cab, newcab): f for n, f in bundle.files.items()}
    (pkg / "bundles" / dest).write_bytes(bundle.save(packer="lz4"))
    manifest.append(
        dict(
            key=dest,
            dependencyKeys=native[srcname]["Dependencies"]
            + [matfile.name]
            + (
                [clipkey, mpkey] if gun else [forekey] if k == "Barrel_Extended" else []
            ),
        )
    )
if rapido or muzzles or payday or rail_only:
    prior = json.loads((pkg / "bundles.json").read_text())["manifest"]
    replace = {x["key"] for x in manifest}
    manifest = [x for x in prior if x["key"] not in replace] + manifest
(pkg / "bundles.json").write_text(json.dumps({"manifest": manifest}, indent=2))
