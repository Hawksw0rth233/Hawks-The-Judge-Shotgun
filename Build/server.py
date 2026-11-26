from judge_assets import *

dbroot = pathlib.Path("E:/SPT 4.1.6/SPT_Runtime/SPT_Data/database/templates")
db = json.loads((dbroot / "items.json").read_text(encoding="utf8"))
hb = {
    i["Id"]: i
    for i in json.loads((dbroot / "handbook.json").read_text(encoding="utf8"))["Items"]
}


def id(s):
    return hashlib.sha256(("team.aminus.thejudge/" + s).encode()).hexdigest()[:24]


def bundle(s):
    return "hawks_judge_" + s.lower() + ".bundle"


items = {}


def item(k, donor, title, price, props, short=None):
    name, cn, ja = title
    locales = {
        lang: dict(name=t, shortName=short or t, description=t)
        for lang, t in zip(("en", "ch", "ja"), title)
    }
    items[id(k)] = dict(
        itemTplToClone=donor,
        parentId=db[donor]["_parent"],
        handbookParentId=hb[donor]["ParentId"],
        handbookPriceRoubles=price,
        fleaPriceRoubles=price,
        addtoTraders=False,
        locales=locales,
        overrideProperties=dict(
            Prefab=dict(path=bundle(k), rcid=""),
            ExaminedByDefault=True,
            CanSellOnRagfair=True,
            **props,
        ),
    )


def slot(parent, n, allowed, required=False):
    return dict(
        _id=id(parent + "/" + n),
        _parent=id(parent),
        _name=n,
        _required=required,
        _mergeSlotWithChildren=False,
        _proto="55d30c394bdc2dae468b4577",
        _props={"filters": [dict(Filter=[id(k) for k in allowed], AnimationIndex=0)]},
    )


body = "633ec7c2a6918cb895019c6c"
mag = "633ec6ee025b096d320a3b15"
barrels = [k for k in geo if k.startswith("Barrel_")]
grips = [k for k in geo if k.startswith("Grip_")]
spec = [
    ("mod_magazine", ["Mag_Standard"], True),
    ("mod_pistol_grip", grips, True),
    ("mod_barrel", barrels, True),
]
# Match the ammunition whitelist used by the dependency's own revolver.
provider_dir = dbroot.parents[2] / "user/mods/makeshotgunsgreatagain/db/CustomItems"
provider = json.loads(
    (provider_dir / "raging_judge.json").read_text(encoding="utf-8-sig")
)
provider_gun = next(
    row["overrideProperties"]
    for row in provider.values()
    if "defAmmo" in row["overrideProperties"]
)
provider_cylinder = provider[provider_gun["defMagType"]]["overrideProperties"]
provider_rounds = provider_cylinder["Slots"][0]["_props"]["filters"][0]["Filter"]
assert provider_gun["defAmmo"] in provider_rounds
item(
    "weapon",
    body,
    ("The Judge Shotgun", "The Judge 转轮霰弹枪", "The Judge リボルバーショットガン"),
    54000,
    dict(
        Slots=[slot("weapon", *x) for x in spec],
        ammoCaliber=provider_gun["ammoCaliber"],
        defAmmo=provider_gun["defAmmo"],
        defMagType=id("Mag_Standard"),
        weapClass="shotgun",
        Width=2,
        Height=1,
        Ergonomics=db[body]["_props"]["Ergonomics"] + 40,
        weapFireType=["doubleaction"],
        bFirerate=300,
        SingleFireRate=300,
        DoubleActionAccuracyPenalty=0,
    ),
    "The Judge",
)
items[id("weapon")]["addtoInventorySlots"] = ["Holster"]
w = db[mag]["_props"]
props = {}
for key in ["Slots", "Cartridges"]:
    props[key] = copy.deepcopy(w[key])
    for s in props[key]:
        s["_id"] = id("mag/" + s["_name"])
        s["_parent"] = id("Mag_Standard")
        for filt in s["_props"]["filters"]:
            filt["Filter"] = provider_rounds.copy()
item(
    "Mag_Standard",
    mag,
    ("The Judge five-shot cylinder", "The Judge 五发转轮", "The Judge 5連シリンダー"),
    6300,
    props,
)
for k in (
    barrels
    + grips
    + [
        "BarrelExtension_MuzzleBreak",
        "FrontSight_Standard",
        "RearSight_Standard",
        "SightMount_Standard",
    ]
):
    group = k.split("_")[0]
    donor, en, cn, ja = {
        "Grip": ("633ec8e4025b096d320a3b1e", "grip", "握把", "グリップ"),
        "Barrel": ("55d4491a4bdc2d882f8b456e", "barrel", "枪管", "バレル"),
        "BarrelExtension": (
            "5b363dd25acfc4001a598fd2",
            "suppressor",
            "消音器",
            "サプレッサー",
        ),
        "FrontSight": (
            "5ba26b01d4351e0085325a51",
            "front sight",
            "准星",
            "フロントサイト",
        ),
        "RearSight": ("56083e1b4bdc2dc8488b4572", "rear sight", "照门", "リアサイト"),
        "SightMount": ("609b9e31506cf869cf3eaf41", "sight mount", "瞄具座", "マウント"),
    }[group]
    variant = k.partition("_")[2].replace("_", " ")
    prefix = "The Judge " + (variant + " " if group in ("Grip", "Barrel") else "")
    props = {"Slots": []}
    if group == "Barrel":
        props["Slots"] = [
            slot(k, "mod_sight_front", ["FrontSight_Standard"]),
            slot(k, "mod_muzzle", ["BarrelExtension_MuzzleBreak"]),
        ]
    item(k, donor, (prefix + en, prefix + cn, prefix + ja), 3500, props)
variants = [
    ("weapon", "weapon_rapido", "mod_weapon", ("", "", "")),
    ("Barrel_Medium", "Barrel_Rapido", "mod_barrel", (" barrel", " 枪管", " バレル")),
    (
        "Grip_Standard",
        "Grip_Rapido",
        "mod_pistol_grip",
        (" grip", " 握把", " グリップ"),
    ),
    (
        "Mag_Standard",
        "Mag_Rapido",
        "mod_magazine",
        (" cylinder", " 转轮", " シリンダー"),
    ),
]
for base_part, variant, slotname, suffixes in variants:
    row = copy.deepcopy(items[id(base_part)])
    items[id(variant)] = row
    for lang, suffix in zip(("en", "ch", "ja"), suffixes):
        label = "Mordida Venenosa" + suffix
        row["locales"][lang] = dict(name=label, shortName=label, description=label)
    props = row["overrideProperties"]
    props["Prefab"]["path"] = bundle(variant)
    if base_part == "weapon":
        props["defMagType"] = id("Mag_Rapido")
        props["Slots"] = [slot(variant, n, [v], True) for _, v, n, _ in variants[1:]]
    else:
        for field in ("Slots", "Cartridges"):
            for entry in props.get(field, []):
                entry["_id"] = id(variant + "/" + entry["_name"])
                entry["_parent"] = id(variant)
# Both rails accept the native UM3 pistol rail's optics and adapter plates.
for part in ("SightMount_Standard", "Barrel_Rapido"):
    scope = copy.deepcopy(
        next(
            s
            for s in db["5a7b4900e899ef197b331a2a"]["_props"]["Slots"]
            if s["_name"] == "mod_scope"
        )
    )
    scope.update(_id=id(part + "/mod_scope"), _parent=id(part))
    items[id(part)]["overrideProperties"]["Slots"].append(scope)
from muzzle_parts import parts as payday_muzzles

muzzles = {
    k: v
    for k, v in payday_muzzles().items()
    if v[0] not in {"12GObelisk", "12GGrimCompensator"}
}
labels = {
    "12GObelisk": "Obelisk",
    "12GVentComp": "Vent Comp",
    "SedimentChoke": "Sediment Choke",
    "JawChoke": "Jaw Choke",
    "Ridgecyl": "Ridgecyl",
    "12GCoronetMuzzle": "Coronet",
    "SilentKiller": "Silent Killer",
    "Breacher": "Breacher",
    "12GTorqued": "Torqued",
    "12GGrimCompensator": "Grim Comp",
}


def part_props(key):
    return items[id(key)]["overrideProperties"]


def find_slot(key, name):
    return next(s for s in part_props(key)["Slots"] if s["_name"] == name)


def short_names(key, labels):
    for lang, label in zip(("en", "ch", "ja"), labels):
        items[id(key)]["locales"][lang]["shortName"] = label


for key, (source_name, _, silent) in muzzles.items():
    label = labels[source_name]
    if silent:
        nouns = ("suppressor", "消音器", "サプレッサー")
    elif "Choke" in label:
        nouns = ("choke", "喉缩", "チョーク")
    else:
        nouns = ("muzzle brake", "制退器", "マズルブレーキ")
    title = (
        label + ("" if label.lower().endswith(nouns[0]) else " " + nouns[0]),
        f"{label} {nouns[1]}",
        f"{label} {nouns[2]}",
    )
    donor = "5b363dd25acfc4001a598fd2" if silent else "58272d7f2459774f6311ddfd"
    modifiers = {
        "SilentKiller": (-1, -1, 0.04),
        "Ridgecyl": (0, 1, -0.04),
        "SedimentChoke": (0, 0.05, -0.06),
        "JawChoke": (0.5, 0.1, -0.09),
        "12GVentComp": (-1, -0.05, 0.04),
        "12GCoronetMuzzle": (-0.5, 0, 0.07),
        "Breacher": (0.75, -0.1, 0.09),
        "12GTorqued": (-0.75, 0.1, -0.02),
    }
    recoil, ergo, weight = modifiers[source_name]
    base_stats = db[donor]["_props"]
    props = {
        "Slots": [],
        "Recoil": base_stats["Recoil"] + recoil,
        "Ergonomics": base_stats["Ergonomics"] + ergo,
        "Weight": round(base_stats["Weight"] * (1 + weight), 4),
    }
    assert all(
        abs(props[k] - base_stats[k]) <= abs(base_stats[k]) * 0.100001
        for k in ("Recoil", "Ergonomics", "Weight")
    )
    item(key, donor, title, 3500, props, label)

for gun in ("weapon", "weapon_rapido"):
    find_slot(gun, "mod_barrel")["_props"]["filters"][0]["Filter"] = [
        id(k) for k in barrels + ["Barrel_Rapido"]
    ]
    find_slot(gun, "mod_magazine")["_props"]["filters"][0]["Filter"] = [
        id("Mag_Standard"),
        id("Mag_Rapido"),
    ]
part_props("Barrel_Rapido")["Slots"] = [
    s for s in part_props("Barrel_Rapido")["Slots"] if s["_name"] != "mod_sight_front"
]
for k in barrels + ["Barrel_Rapido"]:
    part_props(k)["Slots"] = [
        entry for entry in part_props(k)["Slots"] if entry["_name"] != "mod_muzzle"
    ]
# Retain the obsolete adapter template for already-owned items.
adapter = "5c0111ab0db834001966914d"
item(
    "Judge12GAdapter",
    adapter,
    ("12-gauge muzzle adapter", "12号枪口转接座", "12ゲージマズルアダプター"),
    3500,
    {"Slots": []},
    "12G Adapter",
)
part_props("Judge12GAdapter")["Prefab"] = copy.deepcopy(db[adapter]["_props"]["Prefab"])
part_props("Judge12GAdapter")["CanSellOnRagfair"] = False
for k in barrels:
    label = k.split("_", 1)[1]
    short_names(k, ["Judge " + label] * 3)
for k in grips:
    label = k.split("_", 1)[1].replace("_", " ")
    short_names(
        k, (f"Judge {label} Grip", f"Judge {label} 握把", f"Judge {label} グリップ")
    )
for k, labels3 in {
    "Mag_Standard": ("Judge Cyl.", "Judge 弹巢", "Judge シリンダー"),
    "FrontSight_Standard": ("Judge FS", "Judge 准星", "Judge フロント"),
    "RearSight_Standard": ("Judge RS", "Judge 照门", "Judge リア"),
    "SightMount_Standard": ("Judge Rail", "Judge 导轨", "Judge レール"),
    "Barrel_Rapido": ("Mordida Barrel", "Mordida 枪管", "Mordida バレル"),
    "Mag_Rapido": ("Mordida Cyl.", "Mordida 弹巢", "Mordida シリンダー"),
    "Grip_Rapido": ("Mordida Grip", "Mordida 蛇形握把", "Mordida グリップ"),
}.items():
    short_names(k, labels3)
for k in barrels:
    part_props(k)["Slots"].extend(
        [
            slot(k, "mod_sight_rear", ["RearSight_Standard"]),
            slot(k, "mod_mount", ["SightMount_Standard"]),
        ]
    )
part_props("weapon_rapido")["Slots"] = [
    entry
    for entry in part_props("weapon_rapido")["Slots"]
    if entry["_name"] != "mod_pistol_grip"
]
part_props("Grip_Rapido").update(
    IsUnremovable=True, RaidModdable=False, CanSellOnRagfair=False
)
grip_template = items[id("Grip_Rapido")]
for stat in ("Weight", "Ergonomics", "Recoil"):
    grip_stats = grip_template["overrideProperties"]
    grip_value = grip_stats.get(
        stat, db[grip_template["itemTplToClone"]]["_props"].get(stat, 0)
    )
    body_stats = part_props("weapon_rapido")
    body_stats[stat] = round(
        (body_stats.get(stat, db[body]["_props"].get(stat, 0)) or 0)
        + (grip_value or 0),
        4,
    )

payday = "Barrel_Payday"
silent = next(k for k, (source, _, _) in muzzles.items() if source == "SilentKiller")
standard = items[id("Barrel_Standard")]
payday_slots = copy.deepcopy(part_props("Barrel_Standard")["Slots"])
for entry in payday_slots:
    entry.update(_parent=id(payday), _id=id(payday + "/" + entry["_name"]))
# EFT reports MOA as center of impact times 100 / 2.9089 at full condition.
barrel_stats = db[standard["itemTplToClone"]]["_props"]
barrel_balance = {
    "Barrel_Standard": (10.67, 0, 0, 0, 0),
    "Barrel_Rapido": (10.67, 0, 0, 0, 0),
    "Barrel_Medium": (8.08, -5, -2, 1, 0.01),
    "Barrel_Long": (7.25, -12, -4, 2.5, 0.025),
    "Barrel_Extended": (5.33, -25, -8, 4, 0.04),
}
for k, (moa, recoil, ergo, velocity, weight_rate) in barrel_balance.items():
    part_props(k).update(
        CenterOfImpact=round(moa * 2.9089 / 100, 8),
        Recoil=recoil,
        Ergonomics=ergo,
        Velocity=barrel_stats["Velocity"] + velocity,
        Weight=round(barrel_stats["Weight"] * (1 + weight_rate), 4),
        Accuracy=0,
    )
suppressor_stats = part_props(silent)
suppressor_donor = db[items[id(silent)]["itemTplToClone"]]["_props"]
standard_stats = part_props("Barrel_Standard")
combined_stats = {
    stat: round(
        standard_stats[stat] + suppressor_stats.get(stat, suppressor_donor[stat]), 4
    )
    for stat in ("Weight", "Ergonomics", "Recoil", "Velocity", "Accuracy")
}
combined_stats["CenterOfImpact"] = standard_stats["CenterOfImpact"]
item(
    payday,
    standard["itemTplToClone"],
    ("Payday Barrel", "Payday 枪管", "Payday バレル"),
    standard["fleaPriceRoubles"] + items[id(silent)]["fleaPriceRoubles"],
    dict(Slots=payday_slots, **combined_stats),
)
for gun in ("weapon", "weapon_rapido"):
    find_slot(gun, "mod_barrel")["_props"]["filters"][0]["Filter"].append(id(payday))

for barrel in (*barrel_balance, payday):
    props = part_props(barrel)
    props["CenterOfImpact"] = round(props["CenterOfImpact"] * 0.75, 8)
    props["Recoil"] = round((100 + props["Recoil"]) * 0.65 - 100, 2)

for k in barrels + ["Barrel_Rapido", payday]:
    part_props(k).update(
        ExtraSizeLeft=int(k in ("Barrel_Extended", payday)),
        ExtraSizeRight=0,
        ExtraSizeUp=0,
        ExtraSizeDown=0,
        ExtraSizeForceAdd=False,
    )
part_props("SightMount_Standard")["Ergonomics"] = -1
stock_grip = items[id("Grip_Standard")]
stock_ergo = db[stock_grip["itemTplToClone"]]["_props"]["Ergonomics"]
for k in grips:
    part_props(k)["Ergonomics"] = stock_ergo + (
        2 if k == "Grip_Tac" else int(k.startswith("Grip_Wood_"))
    )

weapon_locales = {
    "weapon": {
        "en": (
            '"The Judge" .410 revolver',
            "The Judge",
            "A classic revolving shotgun. Its devastating damage at close range, barely controllable recoil and surprisingly effective gas seal make quite an impression. For some reason, a crew of criminals from Washington, D.C. who wear clown masks are particularly fond of it.",
        ),
        "ch": (
            "“判官” .410 左轮霰弹枪",
            "判官",
            "一把经典的转轮霰弹枪。近距离下极高的伤害，几乎无法控制的后坐力与意外地出色的气密性使它令人印象深刻。不知为何，这把枪十分受到一伙来自华盛顿的面具小丑犯罪组织青睐。",
        ),
        "ja": (
            "「ジャッジ」 .410 リボルバーショットガン",
            "ジャッジ",
            "古典的なリボルバーショットガン。至近距離での凄まじい威力、制御しきれないほどの反動、そして意外なほど優れた気密性が強烈な印象を残す。なぜか、ワシントンD.C.を拠点に道化師の仮面をかぶって活動する犯罪グループが、この銃をいたく気に入っている。",
        ),
    },
    "weapon_rapido": {
        "en": (
            '"Mordida Venenosa" .410 revolver',
            "Mordida Venenosa",
            "An ornately decorated revolving shotgun. Elaborate Latin American engravings cover the frame. A rattlesnake cast in solid gold coils around the custom grip, its jaws agape and its fangs gleaming with a cold, vicious light. Emeralds are set into its eyes. It is as much a collector’s piece as a firearm, if not more so.",
        ),
        "ch": (
            "“毒噬” .410 左轮霰弹枪",
            "毒噬",
            "一把拥有华丽装饰的转轮霰弹枪。机匣上附着着华丽的拉丁美洲风格雕纹，特制的握把上盘踞着一条纯金打造的、血口大张的响尾蛇，毒牙凶狠地闪耀着寒光，眼睛用镶嵌的祖母绿装饰。与其说是一把枪，不如说是一把精美的收藏品。",
        ),
        "ja": (
            "「毒牙」 .410 リボルバーショットガン",
            "毒牙",
            "豪奢な装飾をまとったリボルバーショットガン。フレームにはラテンアメリカ風の華やかな彫刻が施され、特製グリップには純金のガラガラヘビがとぐろを巻いている。大きく開いた口からのぞく毒牙は冷たく獰猛な光を放ち、その両眼にはエメラルドがはめ込まれている。銃というより、むしろコレクションにふさわしい逸品だ。",
        ),
    },
}
for key, translations in weapon_locales.items():
    for lang, (name, short_name, description) in translations.items():
        items[id(key)]["locales"][lang] = dict(
            name=name, shortName=short_name, description=description
        )

descriptions = {
    payday: (
        "A reminder to the biggest, the untouchable.",
        "致那些最高高在上、无人能触及的人。",
        "最大にして不可侵の者たちへの戒め。",
    ),
    "Grip_Rapido": (
        "The sculpted serpent forms an integral part of the Mordida Venenosa grip.",
        "雕刻的蛇形饰件与 Mordida Venenosa 握把连为一体。",
        "蛇の彫刻が一体となった Mordida Venenosa のグリップ。",
    ),
    "Barrel_Rapido": (
        "The Mordida Venenosa barrel incorporates its own optic mounting surface.",
        "Mordida Venenosa 的枪管带有一体式瞄具安装位。",
        "光学照準器用の取り付け部を一体化した Mordida Venenosa のバレル。",
    ),
    "FrontSight_Standard": (
        "A front sight for the modular Judge barrels.",
        "适用于 Judge 模块化枪管的准星。",
        "Judge のモジュラーバレル用フロントサイト。",
    ),
    "RearSight_Standard": (
        "A rear sight mounted on the Judge barrel assembly.",
        "安装在 Judge 枪管总成上的照门。",
        "Judge のバレルアセンブリに取り付けるリアサイト。",
    ),
    "SightMount_Standard": (
        "A rail for mounting compatible pistol optics on the Judge.",
        "可为 Judge 安装兼容手枪瞄具的导轨。",
        "対応するピストル用光学照準器を Judge に取り付けるレール。",
    ),
    "Judge12GAdapter": (
        "A legacy 12-gauge muzzle adapter retained for existing inventories.",
        "为已有库存保留的旧版 12 号枪口转接座。",
        "既存のインベントリ向けに残された旧式12ゲージアダプター。",
    ),
    "BarrelExtension_MuzzleBreak": (
        "A cylindrical suppressor with an extended body.",
        "采用加长圆柱外壳的消音器。",
        "長い円筒形の本体を備えたサプレッサー。",
    ),
}
for k in barrels:
    variant = k.split("_", 1)[1].replace("_", " ")
    descriptions[k] = (
        f"The {variant.lower()} Judge barrel accepts separate iron sights and an optic rail.",
        f"Judge 的 {variant} 枪管，可单独安装机械瞄具和瞄具导轨。",
        f"アイアンサイトと光学照準器用レールを個別に取り付けられる Judge の {variant} バレル。",
    )
for k in grips:
    if k in descriptions:
        continue
    variant = k.split("_", 1)[1].replace("_", " ")
    descriptions[k] = (
        f"The {variant.lower()} replacement grip for the Judge frame.",
        f"适用于 Judge 枪身的 {variant} 替换握把。",
        f"Judge のフレームに装着する {variant} 交換用グリップ。",
    )
for k in ("Mag_Standard", "Mag_Rapido"):
    name = "The Judge" if k == "Mag_Standard" else "Mordida Venenosa"
    descriptions[k] = (
        f"A five-chamber .410 cylinder in the {name} pattern.",
        f"{name} 样式的五膛 .410 弹巢。",
        f"{name} 仕様の5連 .410 シリンダー。",
    )
for k, (source, _, suppressed) in muzzles.items():
    label = labels[source]
    if source == "SilentKiller":
        descriptions[k] = (
            f"The {label} suppressor prioritizes recoil reduction.",
            f"{label} 消音器侧重减轻后坐力。",
            f"反動の軽減を重視した {label} サプレッサー。",
        )
    elif suppressed:
        descriptions[k] = (
            f"The {label} suppressor prioritizes handling.",
            f"{label} 消音器侧重操控性。",
            f"取り回しを重視した {label} サプレッサー。",
        )
    elif "Choke" in label:
        descriptions[k] = (
            f"The {label} shotgun choke fits at the muzzle.",
            f"{label} 是装在霰弹枪枪口的喉缩。",
            f"銃口に装着するショットガン用 {label} チョーク。",
        )
    else:
        descriptions[k] = (
            f"The {label} shotgun muzzle brake redirects propellant gases.",
            f"{label} 霰弹枪制退器用于改变枪口燃气方向。",
            f"発射ガスの向きを変えるショットガン用 {label} マズルブレーキ。",
        )
for k, localized in descriptions.items():
    for lang, description in zip(("en", "ch", "ja"), localized):
        items[id(k)]["locales"][lang]["description"] = description
assert all(
    row["locales"]["en"]["description"] != row["locales"]["en"]["name"]
    for key, row in items.items()
    if key not in (id("weapon"), id("weapon_rapido"))
)
# Standalone devices keep their original item IDs but are registered by the muzzle mod.
muzzle_project = work.parent.parent / "Payday Shotgun Muzzle Devices"
muzzle_target = muzzle_project / "Package/db/CustomItems"
muzzle_target.mkdir(parents=True, exist_ok=True)
standalone = {}
for key in muzzles:
    row = items.pop(id(key))
    prefab = row["overrideProperties"]["Prefab"]
    prefab["path"] = prefab["path"].replace("hawks_judge_", "hawks_pdshotgun_")
    standalone[id(key)] = row
(muzzle_target / "payday-shotgun-muzzles.json").write_text(
    json.dumps(standalone, ensure_ascii=False, indent=2), encoding="utf8"
)
ids = ",".join('"' + key + '"' for key in standalone)
(muzzle_project / "Server/DeviceIds.cs").write_text(
    "namespace Hawks.PaydayShotgunMuzzles;\ninternal static class DeviceIds { internal static readonly string[] All = ["
    + ids
    + "]; }\n",
    encoding="utf8",
)
target = pkg / "db/CustomItems"
target.mkdir(parents=True, exist_ok=True)
(target / "thejudge.json").write_text(
    json.dumps(items, ensure_ascii=False, indent=2), encoding="utf8"
)
preset = [
    ("weapon", "", ""),
    ("Barrel_Medium", "weapon", "mod_barrel"),
    ("Grip_Standard", "weapon", "mod_pistol_grip"),
    ("Mag_Standard", "weapon", "mod_magazine"),
    ("RearSight_Standard", "Barrel_Medium", "mod_sight_rear"),
    ("SightMount_Standard", "Barrel_Medium", "mod_mount"),
    ("FrontSight_Standard", "Barrel_Medium", "mod_sight_front"),
]


def preset_code(key, title, parts):
    root = parts[0][0]
    lines = []
    for part, parent, slotname in parts:
        fields = [
            'Id="' + id(key + "/" + part) + '"',
            'Template="'
            + ("619d36da53b4d42ee724fae4" if part == "Native12GChoke" else id(part))
            + '"',
        ]
        if parent:
            fields += [
                'ParentId="' + id(key + "/" + parent) + '"',
                'SlotId="' + slotname + '"',
            ]
        lines.append("new Item{" + ",".join(fields) + "}")
    return (
        'globals.ItemPresets["'
        + id(key)
        + '"]=new Preset{Id="'
        + id(key)
        + '",Encyclopedia="'
        + id(root)
        + '",Parent="'
        + id(key + "/" + root)
        + '",Type="Preset",Name="'
        + title
        + '",ChangeWeaponName=false,Items=['
        + ",".join(lines)
        + "]};"
    )


rapido_preset = [("weapon_rapido", "", "")] + [
    (v, "weapon_rapido", n) for _, v, n, _ in variants[1:] if n != "mod_pistol_grip"
]
server = work / "Server"
(server / "Judge.cs").write_text(
    """using SPTarkov.DI.Annotations;
using SPTarkov.Server.Core.DI;
using SPTarkov.Server.Core.Models.Eft.Common.Tables;
using SPTarkov.Server.Core.Models.Spt.Tables;
using System.Reflection;
namespace Hawks.TheJudge;
[Injectable(TypePriority=OnLoadOrder.Preload+2)]
public sealed class Judge(WTTServerCommonLib.WTTServerCommonLib wtt,GlobalTable globals,TemplateTable templates):IOnLoad{
 public async Task OnLoadAsync(CancellationToken cancellationToken){
 await wtt.CustomItemServiceExtended.CreateCustomItems(Assembly.GetExecutingAssembly());
 string[] required={"""
    + ",".join(
        '"' + k + '"'
        for k in items
        if k != id("Judge12GAdapter")
        and k not in {id(n) for n in muzzles if n != "BarrelExtension_MuzzleBreak"}
    )
    + """};
 foreach(var id in required)if(!templates.Items.ContainsKey(id))throw new InvalidOperationException("Missing The Judge item "+id);
 """
    + preset_code("preset", "The Judge Shotgun", preset)
    + "\n "
    + preset_code("preset_rapido", "Mordida Venenosa", rapido_preset)
    + """
 }}
"""
)
