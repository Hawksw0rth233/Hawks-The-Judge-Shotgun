from judge_assets import *
import zlib

nodes = json.loads((tmp / "rig.json").read_text())["nodes"]
paths = [n["path"] for n in nodes]
idx = {n: j for j, n in enumerate(names)}
parent = {
    n: idx[paths[j].rsplit("/", 1)[0].split("/")[-1]]
    for j, n in enumerate(names)
    if "/" in paths[j]
}
crc = {zlib.crc32(pa.encode()): j for j, pa in enumerate(paths)}
rest = idle.copy()
for bone, pivot in [
    ("mod_pistol_grip", "Grip"),
    ("weapon_cylinder_axis", "Hinge"),
    ("mod_magazine", "Mag"),
    ("weapon_extractor", "Ejector"),
    ("mod_hammer", "Bolt"),
]:
    rest[idx[bone], :3, 3] = world(piv[pivot])
for j in range(5):
    # Keep EFT's chamber numbering and rotate the PD3 cylinder half a turn
    # around its bore axis. Blender's source frame uses X as that axis.
    mag_pivot = np.asarray(piv["Mag"])
    chamber = mag_pivot + (np.asarray(piv["Bullet%02d" % j]) - mag_pivot) * [1, -1, -1]
    for prefix in ["shellport_", "patron_in_weapon_"]:
        rest[idx[prefix + "%03d" % (j + 1)], :3, 3] = world(chamber)
bar = np.array([0.40070516, -0.07415163, 1.54990888])
rest[idx["fireport"], :3, 3] = (
    world(bar) + axes @ geo["Barrel_Medium"]["nodes"]["BarrelExtension"]
)
# Project the ADS camera onto the line through the installed sights.
rear = world(
    [
        0.322719 + 0.0016,
        -0.074151,
        1.566265 + geo["RearSight_Standard"]["v"][:, 1].max(),
    ]
)
front = world(
    bar
    + np.array(
        [
            *np.array(geo["Barrel_Medium"]["nodes"]["FrontSight"])[[0, 2]],
            geo["Barrel_Medium"]["nodes"]["FrontSight"][1],
        ]
    )
    + [0.012, 0, geo["FrontSight_Standard"]["v"][:, 1].max()]
)
camera = rest[idx["aim_camera"], :3, 3]
camera[:] = rear + (front - rear) * (camera[2] - rear[2]) / (front[2] - rear[2])
static = {}
for n in [
    "mod_hammer",
    "aim_camera",
    "mod_pistol_grip",
    "weapon_cylinder_axis",
    "mod_magazine",
    "weapon_extractor",
    "fireport",
] + [n for n in names if n.startswith(("patron_in_weapon", "shellport_"))]:
    j = idx[n]
    h = parent[n]
    static[n] = (np.linalg.inv(rest[h]) @ rest[j])[:3, 3] - (
        np.linalg.inv(idle[h]) @ idle[j]
    )[:3, 3]
clipkey = "hawks_judge_actions.bundle"
clipcab = "CAB-" + uuid.uuid5(uuid.NAMESPACE_URL, clipkey).hex


def extract(a, ts):
    c = a.m_MuscleClip.m_Clip.data
    s = c.m_StreamedClip
    d = c.m_DenseClip
    k = c.m_ConstantClip.data
    v = np.zeros((len(ts), s.curveCount + d.m_CurveCount + len(k)))
    raw = np.asarray(s.data, dtype="<u4")
    f = raw.view("<f4")
    i = 0
    while i < len(raw):
        t = float(f[i])
        ct = int(raw[i + 1])
        blk = raw[i + 2 : i + 2 + 5 * ct].reshape(-1, 5)
        i += 2 + 5 * ct
        ix = blk[:, 0]
        co = blk.view("<f4")[:, 1:]
        sel = np.where(ts >= t - 1e-6)[0]
        dt = (ts[sel] - t)[:, None] if abs(t) < 1e10 else np.zeros((len(sel), 1))
        v[np.ix_(sel, ix)] = ((co[:, 0] * dt + co[:, 1]) * dt + co[:, 2]) * dt + co[
            :, 3
        ]
    if len(k):
        v[:, -len(k) :] = k
    if d.m_CurveCount:
        v[:, s.curveCount : s.curveCount + d.m_CurveCount] = np.array(
            d.m_SampleArray
        ).reshape(-1, d.m_CurveCount)[
            np.clip(
                np.rint((ts - d.m_BeginTime) * d.m_SampleRate).astype(int),
                0,
                d.m_FrameCount - 1,
            )
        ]
    return v


def build():
    src = base / "assets/content/weapons/rsh12/client_assets.bundle"
    e = UnityPy.load(str(src))
    b = next(iter(e.files.values()))
    cab = next(iter(b.files))
    sf = b.files[cab]
    clips = {}
    for o in list(e.objects):
        if o.type.name != "AnimationClip":
            continue
        a = o.read()
        f = tmp / "samples" / (a.m_Name + ".bin")
        if not f.exists():
            continue
        m = np.fromfile(f, "<f4").reshape(-1, len(names), 4, 4)
        original_frames = len(m)
        frames = original_frames
        ticks = np.arange(frames)
        v = extract(a, ticks / 30)
        native_values = v.copy()
        hammer_index = idx["mod_hammer"]
        slide_index = parent["mod_hammer"]
        receiver_index = idx["weapon"]
        receiver_to_hinge = np.linalg.solve(rest[receiver_index], rest[hammer_index])
        hammer_local = (
            np.linalg.inv(m[:, slide_index]) @ m[:, receiver_index] @ receiver_to_hinge
        )
        slot = re.fullmatch(r"rsh12_(?:ammo_in|ammo_out|shell_out)_([0-4])", a.m_Name)
        left_targets = {
            "Base HumanLCollarbone",
            "weapon_L_hand_marker",
            "weapon_L_IK_marker",
        }
        adjusted = set()
        if slot:
            prefix = (
                "shellport_"
                if a.m_Name.startswith("rsh12_shell_out_")
                else "patron_in_weapon_"
            )
            node = f"{prefix}{int(slot[1])+1:03}"
            # Each offset is local to a moving ancestor. Accumulate the translations
            # through the animated hinge and cylinder instead of using the idle delta.
            frame_delta = np.zeros((frames, 3))
            while node in parent:
                ancestor = parent[node]
                if node in static:
                    frame_delta += m[:, ancestor, :3, :3] @ static[node]
                node = names[ancestor]
        off = 0
        for binding in a.m_ClipBindingConstant.genericBindings:
            size = (
                {1: 3, 2: 4, 3: 3, 4: 3}.get(binding.attribute, 1)
                if binding.typeID == 4
                else 1
            )
            if binding.typeID == 4 and crc.get(binding.path) == hammer_index:
                if binding.attribute == 1:
                    v[:, off : off + 3] = hammer_local[:, :3, 3]
                if binding.attribute in (2, 4):
                    track = v[:, off : off + size]
                    native = (
                        Rot.from_euler("ZXY", track[:, [2, 0, 1]], degrees=True)
                        if binding.attribute == 4
                        else Rot.from_quat(track)
                    )
                    rotation = Rot.from_matrix(hammer_local[:, :3, :3]) * native
                    v[:, off : off + size] = (
                        rotation.as_euler("ZXY", degrees=True)[:, [1, 2, 0]]
                        if binding.attribute == 4
                        else rotation.as_quat()
                    )
            elif binding.typeID == 4 and binding.attribute == 1:
                bone = names[crc[binding.path]] if binding.path in crc else ""
                if bone in (
                    "weapon_cylinder_axis",
                    "mod_magazine",
                    "weapon_extractor",
                    "mod_pistol_grip",
                ) or bone.startswith(("patron_in_weapon_", "shellport_")):
                    v[:, off : off + size] += static[bone]
                elif slot and bone in left_targets:
                    if bone in parent:
                        parent_basis = m[:, parent[bone], :3, :3]
                        shift = np.linalg.solve(parent_basis, frame_delta[:, :, None])[
                            :, :, 0
                        ]
                        assert np.allclose(
                            (parent_basis @ shift[:, :, None])[:, :, 0], frame_delta
                        )
                    else:
                        shift = frame_delta
                    v[:, off : off + 3] += shift
                    adjusted.add(bone)
                else:
                    assert np.array_equal(
                        v[:, off : off + size], native_values[:, off : off + size]
                    )
            else:
                assert np.array_equal(
                    v[:, off : off + size], native_values[:, off : off + size]
                )
            off += size
        if slot:
            assert adjusted == left_targets, (a.m_Name, adjusted)
        # F8 Weapon / Forward is the animated weapon root's local +Z.
        root = "Weapon_root_anim"
        forward = m[:, idx[root], :3, :3] @ np.array([0.0, 0.0, 0.005])
        is_reload = re.match(
            r"rsh12_(?:reload_|ammo_in_|ammo_out_|shell_out_)", a.m_Name
        )
        targets = {"weapon": 1}
        grip_markers = (
            "weapon_R_hand_marker",
            "weapon_R_IK_marker",
            "weapon_L_hand_marker",
            "weapon_L_IK_marker",
        )
        for marker in grip_markers:
            if not is_reload or marker.startswith("weapon_R_"):
                targets[marker] = -1
        if is_reload:
            targets["Base HumanLCollarbone"] = 1
        cursor = 0
        shifted = set()
        for binding in a.m_ClipBindingConstant.genericBindings:
            width = (
                {1: 3, 2: 4, 3: 3, 4: 3}.get(binding.attribute, 1)
                if binding.typeID == 4
                else 1
            )
            bone = names[crc[binding.path]] if binding.path in crc else ""
            if binding.typeID == 4 and binding.attribute == 1 and bone in targets:
                shift = (
                    np.linalg.solve(m[:, parent[bone], :3, :3], forward[:, :, None])[
                        :, :, 0
                    ]
                    if bone in parent
                    else forward
                )
                v[:, cursor : cursor + 3] += targets[bone] * shift
                shifted.add(bone)
            cursor += width
        assert shifted == set(targets), (a.m_Name, shifted)
        assert off == v.shape[1] and np.isfinite(v).all()
        d = o.read_typetree()
        c = d["m_MuscleClip"]["m_Clip"]["data"]
        s = c["m_StreamedClip"]
        s.update(curveCount=0, discreteCurveCount=0, data=[])
        c["m_ConstantClip"]["data"] = []
        c["m_DenseClip"].update(
            m_FrameCount=frames,
            m_CurveCount=off,
            m_SampleRate=30.0,
            m_BeginTime=0.0,
            m_SampleArray=v.astype("f").ravel().tolist(),
        )
        o.save_typetree(d)
        clips[o.path_id] = a.m_Name
    ab = next(o for o in e.objects if o.type.name == "AssetBundle")
    d = ab.read_typetree()
    d.update(
        m_Name=clipkey,
        m_AssetBundleName=clipkey,
        m_Dependencies=[],
        m_PreloadTable=[],
        m_Container=[],
    )
    for j, (id, name) in enumerate(clips.items()):
        ptr = dict(m_FileID=0, m_PathID=id)
        d["m_PreloadTable"].append(ptr)
        d["m_Container"].append(
            (
                "assets/hawks/judge/" + name + ".anim",
                dict(preloadIndex=j, preloadSize=1, asset=ptr),
            )
        )
    ab.save_typetree(d)
    sf.objects = {i: o for i, o in sf.objects.items() if i in clips or i == ab.path_id}
    b.files = {clipcab: sf}
    (pkg / "bundles" / clipkey).write_bytes(b.save(packer="lz4"))
    print("retargeted", len(clips))
    return clips


if __name__ == "__main__":
    build()
