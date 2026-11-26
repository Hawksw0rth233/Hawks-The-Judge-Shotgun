"""Convert sampled PD3 first-person poses to the local transforms consumed by EFT."""

from judge_assets import *


def local_pose(clip, frames, rest, parents):
    if clip == "rsh12_look":
        source, first, last, neutral = "inspect", 0, 250, 0
    elif clip == "rsh12_out_to_idle":
        source, first, last, neutral = "draw", 0, 32, 32
    elif clip == "rsh12_idle_to_out":
        source, first, last, neutral = "draw", 33, 50, 33
    elif clip == "rsh12_ammo_in_fistful":
        source, first, last, neutral = "reload", 39, 84, 0
    else:
        return {}
    index = {name: i for i, name in enumerate(names)}
    mapping = {
        "weapon": "Body",
        "weapon_cylinder_axis": "Hinge",
        "mod_magazine": "Mag",
        "weapon_extractor": "Ejector",
    }
    for side in ("Left", "Right"):
        prefix = "Base Human" + side[0]
        for eft, pd3 in [
            ("Collarbone", "Shoulder"),
            ("Upperarm", "Arm"),
            ("Forearm1", "ForeArm"),
            ("Forearm2", "ForeArmTwist2"),
            ("Forearm3", "ForeArmTwist3"),
            ("Palm", "Hand"),
        ]:
            mapping[prefix + eft] = side + pd3
        for digit, finger in enumerate(
            ("Thumb", "Index", "Middle", "Ring", "Pinky"), 1
        ):
            for joint in range(1, 4):
                mapping[f"{prefix}Digit{digit}{joint}"] = f"{side}Hand{finger}{joint}"
        for marker, bone in [
            ("hand_marker", "Hand"),
            ("IK_marker", "ForeArm"),
            ("Collarbone_marker", "Shoulder"),
        ]:
            name = (
                "weapon_"
                + side[0]
                + ("" if marker.startswith("Collarbone") else "_")
                + marker
            )
            mapping[name] = side + bone
    world_pose = {}
    local = {}
    timeline = np.linspace(first, last, frames)
    U = G.copy()
    with np.load(tmp / f"pd3{source}.npz") as data:
        for j, name in enumerate(names):
            parent = parents.get(name)
            parent_pose = world_pose[names[parent]] if parent is not None else np.eye(4)
            if name in mapping:
                src = data[mapping[name]].copy()
                src[:, :3, :3] /= np.linalg.norm(src[:, :3, :3], axis=1)[:, None, :]
                pose = (
                    U @ src @ np.linalg.inv(src[neutral]) @ np.linalg.inv(U) @ rest[j]
                )
                position = np.column_stack(
                    [
                        np.interp(timeline, np.arange(len(src)), pose[:, i, 3])
                        for i in range(3)
                    ]
                )
                from scipy.spatial.transform import Slerp

                rotation = Slerp(np.arange(len(src)), Rot.from_matrix(pose[:, :3, :3]))(
                    timeline
                )
                dest = np.tile(np.eye(4), (frames, 1, 1))
                dest[:, :3, :3] = rotation.as_matrix()
                dest[:, :3, 3] = position
                value = np.linalg.inv(parent_pose) @ dest
                world_pose[name] = dest
            else:
                value = (
                    np.linalg.solve(rest[parent], rest[j])
                    if parent is not None
                    else rest[j]
                )
                world_pose[name] = parent_pose @ value
                value = np.broadcast_to(value, (frames, 4, 4))
            local[name] = value
    return local
