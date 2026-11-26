from judge_assets import *

pd3 = np.load(tmp / "pd3reload.npz")
target = work / "ClientFiles"
U = G.copy()
U[:3, :3] = np.array([[0, -1, 0], [0, 0, 1], [1, 0, 0]])
root = idle[names.index("Weapon_root")]
invroot = np.linalg.inv(root)
mapping = {
    "weapon": "Body",
    "weapon_cylinder_axis": "Hinge",
    "mod_magazine": "Mag",
    "weapon_extractor": "Ejector",
}
for side in ["Left", "Right"]:
    e = "Base Human" + side[0]
    mapping.update(
        {
            e + "Upperarm": side + "Arm",
            e + "Forearm1": side + "ForeArm",
            e + "Forearm2": side + "ForeArmTwist2",
            e + "Forearm3": side + "ForeArmTwist3",
            e + "Palm": side + "Hand",
        }
    )
    for marker, bone in [
        ("hand_marker", "Hand"),
        ("IK_marker", "ForeArm"),
        ("Collarbone_marker", "Shoulder"),
    ]:
        key = (
            "weapon_"
            + side[0]
            + ("" if marker.startswith("Collarbone") else "_")
            + marker
        )
        mapping[key] = side + bone
    for i, digit in enumerate(["Thumb", "Index", "Middle", "Ring", "Pinky"], 1):
        for j in range(1, 4):
            mapping[e + "Digit" + str(i) + str(j)] = side + "Hand" + digit + str(j)


def normalized(x):
    a = x.copy()
    a[:, :3, :3] /= np.linalg.norm(a[:, :3, :3], axis=1)[:, None, :]
    return a


tracks = {}
for eft, source in mapping.items():
    src = normalized(pd3[source])
    neutral = idle[names.index(eft)].copy()
    if eft in ["mod_magazine", "weapon_cylinder_axis", "weapon_extractor"]:
        neutral[:3, 3] = world(piv[source])
    q = invroot @ U @ src @ np.linalg.inv(src[0]) @ np.linalg.inv(U) @ neutral
    tracks[eft] = q
# Use the mesh's original world-space orientation from the inserted frame.
# A glTF X-axis shotshell extends down the bore when the loader reaches the cylinder.
basis = np.eye(4)
basis[:3, :3] = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
l = normalized(pd3["SpeedLoader"])
mag = normalized(pd3["Mag"])
bind = np.linalg.inv(mag[0, :3, :3]) @ basis[:3, :3]
meshbasis = np.eye(4)
meshbasis[:3, :3] = bind
loader = invroot @ U @ l @ np.linalg.inv(l[66]) @ mag[66] @ meshbasis
# Mesh vertices are reflected before serializing the rigid orientation.
reflection = np.diag([-1, 1, 1, 1])
tracks["PD3 Speedloader"] = loader @ reflection


def packstr(f, s):
    b = s.encode()
    f.write(struct.pack("<i", len(b)))
    f.write(b)


with (target / "judge_reload.dat").open("wb") as f:
    f.write(struct.pack("<iii", 1, len(tracks), 114))
    for k, m in tracks.items():
        packstr(f, k)
        v = m[:, :3, 3]
        q = Rot.from_matrix(m[:, :3, :3]).as_quat()
        f.write(np.column_stack([v, q]).astype("<f4").tobytes())
    for k in ["SpeedLoader", "SM_WP_Ammo_410GA"]:
        g = geo[k]
        v = g["v"].copy()
        v[:, 0] *= -1
        n = g["n"].copy()
        n[:, 0] *= -1
        tex = g["uv"].copy()
        tex[:, 1] = 1 - tex[:, 1]
        f.write(struct.pack("<ii", len(v), g["tri"].size))
        f.write(np.column_stack([v, n, tex]).astype("<f4").tobytes())
        f.write(g["tri"].astype("<i4").tobytes())
    for j in range(5):
        # Positions in loader-local GLTF coordinates at the original insertion pose.
        point = np.r_[piv["Bullet%02d" % j], 1]
        local = np.linalg.inv(mag[0] @ meshbasis) @ point
        f.write((reflection @ local)[:3].astype("<f4").tobytes())
