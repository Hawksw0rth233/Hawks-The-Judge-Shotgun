using System;
using System.Linq;
using BepInEx;
using EFT;
using EFT.InventoryLogic;
using HarmonyLib;
using UnityEngine;

namespace Hawks.TheJudge
{
    [BepInPlugin("team.aminus.thejudge.client", "Hawks's The Judge Shotgun", "0.1.1")]
    public sealed class TheJudgePlugin : BaseUnityPlugin
    {
        internal const string ItemId = "fac0d265ec36a83fa89e5ed8";

        void Awake()
        {
            var h = new Harmony("team.aminus.thejudge.client");
            h.Patch(
                AccessTools.Method(
                    typeof(Player.FirearmController),
                    nameof(Player.FirearmController.UpdateIsWithSilencer)
                ),
                postfix: new HarmonyMethod(typeof(TheJudgePlugin), nameof(ApplyIntegralSuppressor))
            );
            h.Patch(
                AccessTools.Method(typeof(Player.FirearmController), "SetAnimatorValues"),
                prefix: new HarmonyMethod(typeof(TheJudgePlugin), nameof(NormalizeFireMode))
            );
            gameObject.AddComponent<JudgeViewmodel>().Initialize(Config);
            JudgePreviewAmmo.Install(h);
        }

        // Normalize weapons saved with the retired single-action selector on equip.
        static void NormalizeFireMode(Player.FirearmController __instance)
        {
            if (
                __instance.Item is Weapon weapon
                && (weapon.TemplateId == ItemId || weapon.TemplateId == "ef9590b6d87a406b078ba926")
                && weapon.SelectedFireMode != Weapon.EFireMode.doubleaction
            )
            {
                weapon.FireMode.SetFireMode(Weapon.EFireMode.doubleaction);
            }
        }

        // The Payday barrel carries the suppressor geometry inside its own prefab.
        static void ApplyIntegralSuppressor(Player.FirearmController __instance)
        {
            if (__instance.IsSilenced || __instance.Item is not Weapon weapon)
                return;
            if (weapon.TemplateId != ItemId && weapon.TemplateId != "ef9590b6d87a406b078ba926")
                return;
            __instance.IsSilenced = weapon.AllSlots.Any(slot =>
                slot.ContainedItem?.TemplateId == "149afeb78f2eda6a0e8cc0f7"
            );
        }
    }
}
