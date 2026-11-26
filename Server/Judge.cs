using SPTarkov.DI.Annotations;
using SPTarkov.Server.Core.DI;
using SPTarkov.Server.Core.Models.Eft.Common.Tables;
using SPTarkov.Server.Core.Models.Spt.Tables;
using System.Reflection;
namespace Hawks.TheJudge;
[Injectable(TypePriority=OnLoadOrder.Preload+2)]
public sealed class Judge(WTTServerCommonLib.WTTServerCommonLib wtt,GlobalTable globals,TemplateTable templates):IOnLoad{
 public async Task OnLoadAsync(CancellationToken cancellationToken){
 await wtt.CustomItemServiceExtended.CreateCustomItems(Assembly.GetExecutingAssembly());
 string[] required={"fac0d265ec36a83fa89e5ed8","884d08cfe5a118a9a8692a7a","78f739cade5b42d0cc151522","760074881b4700d6d069ad39","8a9bfdee11ef076e83a0abff","5661f8dea523d82ff2760514","03855a6fd3403e686e8ec746","da5359d72bc86f4ab1c955f9","5757101b0ae09d45948c3442","aea059b8c300eaa8dd34931d","843c5ef82279b410bd43cefa","396aa8e4ea6fecee9018a5cb","d812a73fab9d2b3f1478a8b4","ef9590b6d87a406b078ba926","d7dff6e35b6946ecae83ebca","f10498f0d29c39f9a261790b","c85727fdf51091253a7d427e","149afeb78f2eda6a0e8cc0f7"};
 foreach(var id in required)if(!templates.Items.ContainsKey(id))throw new InvalidOperationException("Missing The Judge item "+id);
 globals.ItemPresets["485153f8bf0d53866ea5f8c3"]=new Preset{Id="485153f8bf0d53866ea5f8c3",Encyclopedia="fac0d265ec36a83fa89e5ed8",Parent="9ddcb098ac3a1c9b8057f8b4",Type="Preset",Name="The Judge Shotgun",ChangeWeaponName=false,Items=[new Item{Id="9ddcb098ac3a1c9b8057f8b4",Template="fac0d265ec36a83fa89e5ed8"},new Item{Id="9a1f5ce2cd58b7934fb2542e",Template="8a9bfdee11ef076e83a0abff",ParentId="9ddcb098ac3a1c9b8057f8b4",SlotId="mod_barrel"},new Item{Id="c83c9649f65052725ce98629",Template="03855a6fd3403e686e8ec746",ParentId="9ddcb098ac3a1c9b8057f8b4",SlotId="mod_pistol_grip"},new Item{Id="92b398844658eaf55470ded2",Template="884d08cfe5a118a9a8692a7a",ParentId="9ddcb098ac3a1c9b8057f8b4",SlotId="mod_magazine"},new Item{Id="2d425f3cda2d07335392295d",Template="396aa8e4ea6fecee9018a5cb",ParentId="9a1f5ce2cd58b7934fb2542e",SlotId="mod_sight_rear"},new Item{Id="1bc27872d9db8f66a8282105",Template="d812a73fab9d2b3f1478a8b4",ParentId="9a1f5ce2cd58b7934fb2542e",SlotId="mod_mount"},new Item{Id="961feb6762c062847b0cf4fc",Template="843c5ef82279b410bd43cefa",ParentId="9a1f5ce2cd58b7934fb2542e",SlotId="mod_sight_front"}]};
 globals.ItemPresets["79fd91493fe5d3d723e46202"]=new Preset{Id="79fd91493fe5d3d723e46202",Encyclopedia="ef9590b6d87a406b078ba926",Parent="d20f4cb7856d455b0fe2e157",Type="Preset",Name="Mordida Venenosa",ChangeWeaponName=false,Items=[new Item{Id="d20f4cb7856d455b0fe2e157",Template="ef9590b6d87a406b078ba926"},new Item{Id="7990382eb27bb6eade957e24",Template="d7dff6e35b6946ecae83ebca",ParentId="d20f4cb7856d455b0fe2e157",SlotId="mod_barrel"},new Item{Id="327a4717ee4b1b4df295fb4c",Template="c85727fdf51091253a7d427e",ParentId="d20f4cb7856d455b0fe2e157",SlotId="mod_magazine"}]};
 }}
