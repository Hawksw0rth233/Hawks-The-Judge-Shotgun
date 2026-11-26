using System.Linq;
using System.Threading.Tasks;
using EFT;
using EFT.CameraControl;
using EFT.InventoryLogic;
using HarmonyLib;
using UnityEngine;

namespace Hawks.TheJudge
{
    internal static class JudgePreviewAmmo
    {
        static readonly Vector3[] ChamberPositions =
        {
            new Vector3(.00000617f, 0, -.01346684f),
            new Vector3(-.01283891f, 0, -.00405669f),
            new Vector3(-.00791878f, 0, .01089311f),
            new Vector3(.00791067f, 0, .01089787f),
            new Vector3(.01281438f, -.00003603f, -.00414658f),
        };

        static bool IsCylinder(Item item) =>
            item is CylinderMagazine
            && (
                item.TemplateId == "884d08cfe5a118a9a8692a7a"
                || item.TemplateId == "c85727fdf51091253a7d427e"
            );

        static CylinderMagazine Cylinder(Item item)
        {
            if (
                item is Weapon gun
                && (
                    gun.TemplateId == "fac0d265ec36a83fa89e5ed8"
                    || gun.TemplateId == "ef9590b6d87a406b078ba926"
                )
            )
                item = gun.GetCurrentMagazine();
            return IsCylinder(item) ? (CylinderMagazine)item : null;
        }

        internal static void Install(Harmony harmony)
        {
            harmony.Patch(
                AccessTools.Method(
                    typeof(ObjectsFactory),
                    nameof(ObjectsFactory.CreateCleanLootPrefab)
                ),
                postfix: new HarmonyMethod(typeof(JudgePreviewAmmo), nameof(Sync))
            );
            harmony.Patch(
                AccessTools.Method(
                    typeof(ObjectsFactory),
                    nameof(ObjectsFactory.CreateCleanLootPrefabAsync)
                ),
                postfix: new HarmonyMethod(typeof(JudgePreviewAmmo), nameof(Async))
            );
            harmony.Patch(
                AccessTools.Method(
                    typeof(IconsHash),
                    nameof(IconsHash.GetItemHash),
                    new[] { typeof(Item) }
                ),
                postfix: new HarmonyMethod(typeof(JudgePreviewAmmo), nameof(IconHash))
            );
        }

        static void IconHash(Item item, ref int __result)
        {
            var cylinder = Cylinder(item);
            if (cylinder == null)
                return;
            unchecked
            {
                int chambers = 381821;
                for (int i = 0; i < cylinder.Camoras.Length; i++)
                {
                    var ammo = cylinder.GetAmmoByCamoraIndex(i);
                    chambers = chambers * 31 + (ammo == null ? 0 : IconsHash.GetItemHash(ammo));
                }
                __result = __result * 31 + chambers;
            }
        }

        static void Sync(
            ObjectsFactory __instance,
            Item __0,
            ECameraType __1,
            IPlayer __2,
            GameObject __result
        )
        {
            var cylinder = Cylinder(__0);
            if (cylinder == null || __2 != null || !__result)
                return;
            bool standalone = IsCylinder(__0);
            var nodes = standalone ? null : __result.GetComponentsInChildren<Transform>(true);
            for (int i = 0; i < ChamberPositions.Length && i < cylinder.Camoras.Length; i++)
            {
                var ammo = cylinder.GetAmmoByCamoraIndex(i);
                if (ammo == null)
                    continue;
                var marker = standalone ? __result.transform : FindChamber(nodes, i);
                if (!marker || (!standalone && marker.childCount != 0))
                    continue;
                var round = __instance.CreateCleanLootPrefab(ammo, __1);
                Mount(round, marker, standalone ? ChamberPositions[i] : Vector3.zero);
            }
        }

        static void Async(
            ObjectsFactory __instance,
            Item __0,
            IPlayer __1,
            ref Task<GameObject> __result
        )
        {
            var cylinder = Cylinder(__0);
            if (cylinder != null && __1 == null)
                __result = PopulateAsync(__instance, __result, cylinder, IsCylinder(__0));
        }

        static async Task<GameObject> PopulateAsync(
            ObjectsFactory factory,
            Task<GameObject> pending,
            CylinderMagazine cylinder,
            bool standalone
        )
        {
            var visual = await pending;
            if (!visual)
                return visual;
            var nodes = standalone ? null : visual.GetComponentsInChildren<Transform>(true);
            for (int i = 0; i < ChamberPositions.Length && i < cylinder.Camoras.Length; i++)
            {
                var ammo = cylinder.GetAmmoByCamoraIndex(i);
                if (ammo == null)
                    continue;
                var marker = standalone ? visual.transform : FindChamber(nodes, i);
                if (!marker || (!standalone && marker.childCount != 0))
                    continue;
                var round = await factory.CreateCleanLootPrefabAsync(ammo);
                Mount(round, marker, standalone ? ChamberPositions[i] : Vector3.zero);
            }
            return visual;
        }

        static Transform FindChamber(Transform[] nodes, int slot)
        {
            string name = $"patron_in_weapon_{slot + 1:000}";
            return nodes.FirstOrDefault(t => t.name == name && t.gameObject.activeInHierarchy);
        }

        static void Mount(GameObject round, Transform marker, Vector3 position)
        {
            if (!round || !marker)
                return;
            round.transform.SetParent(marker, false);
            round.transform.localPosition = position;
            round.transform.localRotation = Quaternion.identity;
            foreach (var node in round.GetComponentsInChildren<Transform>(true))
                node.gameObject.layer = marker.gameObject.layer;
            foreach (var collider in round.GetComponentsInChildren<Collider>(true))
                collider.enabled = false;
        }
    }
}
