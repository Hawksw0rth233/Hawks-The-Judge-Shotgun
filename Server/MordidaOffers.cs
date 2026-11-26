using SPTarkov.DI.Annotations;
using SPTarkov.Server.Core.DI;
using SPTarkov.Server.Core.Models.Eft.Common.Tables;
using SPTarkov.Server.Core.Models.Spt.Config;
using SPTarkov.Server.Core.Models.Spt.Tables;


namespace Hawks.TheJudge;

[Injectable(TypePriority = OnLoadOrder.Preload + 3)]
public sealed class MordidaOffers(TemplateTable templates, GlobalTable globals, TradersTable traders,
    TraderConfig traderConfig) : IOnLoad
{
    const string Weapon = "ef9590b6d87a406b078ba926";
    const string Barrel = "d7dff6e35b6946ecae83ebca";
    const string Cylinder = "c85727fdf51091253a7d427e";
    const string Grip = "f10498f0d29c39f9a261790b";

    public Task OnLoadAsync(CancellationToken cancellationToken)
    {
        // Use the ordinary EFT item flags so flea restriction overrides still apply.
        foreach (string id in new[] { Weapon, Barrel, Cylinder, Grip })
            templates.Items[id].Properties!.CanSellOnRagfair = false;

        var assort = traders.GetTrader("5a7c2eca46aef81a7ca2145d")!.Assort;
        const string offer = "c5f074b50000000000000001";
        if (!assort.Items.Any(item => item.Id == offer))
        {
            var preset = globals.ItemPresets["79fd91493fe5d3d723e46202"];
            assort.Items.Add(new Item { Id=offer, Template=Weapon, ParentId="hideout", SlotId="hideout",
                Upd=new() { UnlimitedCount=true, StackObjectsCount=999999 } });
            int ordinal = 2;
            foreach (var child in preset.Items.Where(item => item.ParentId == preset.Parent))
                assort.Items.Add(new Item { Id=$"c5f074b500000000000000{ordinal++:00}", Template=child.Template,
                    ParentId=offer, SlotId=child.SlotId });
        }
        Price(offer, 54000);
        AddPart("c5f074b50000000000000011", Barrel, 3500);
        AddPart("c5f074b50000000000000012", Cylinder, 6300);
        // The serpent grip is part of the receiver. Its legacy template stays flea restricted.
        var fence = traderConfig.Fence.Blacklist;
        foreach (string id in new[] { Weapon, Barrel, Cylinder, Grip })
            if (!fence.Contains(id)) fence.Add(id);
        return Task.CompletedTask;

        void Price(string id, int rubles)
        {
            assort.BarterScheme[id] = [[new() { Template="5449016a4bdc2d6f028b456f", Count=rubles }]];
            assort.LoyalLevelItems[id] = 4;
        }
        void AddPart(string id, string template, int rubles)
        {
            if (!assort.Items.Any(item => item.Id == id))
                assort.Items.Add(new Item { Id=id, Template=template, ParentId="hideout", SlotId="hideout",
                    Upd=new() { UnlimitedCount=true, StackObjectsCount=999999 } });
            Price(id,rubles);
        }
    }
}
