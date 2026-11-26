using System;
using System.Collections.Generic;
using System.IO;
using BepInEx.Configuration;
using Comfort.Common;
using EFT;
using EFT.InputSystem;
using EFT.Animations;
using EFT.InventoryLogic;
using HarmonyLib;
using UnityEngine;

namespace Hawks.TheJudge {
internal sealed class ConfigurationManagerAttributes {
 public Action<ConfigEntryBase> CustomDrawer;
 public bool? Browsable;
}

public sealed class JudgeViewmodel : MonoBehaviour {
 sealed class Axis {
  static readonly float[] Steps = { .1f, 1f, 5f };
  static readonly string[] Labels = { "0.1", "1", "5" };
  public readonly ConfigEntry<float> Setting;
  readonly string minus, plus;
  int step = 1;

  public Axis(ConfigFile config, string pose, string name, string minus, string plus, float limit) {
   this.minus = minus;
   this.plus = plus;
   var controls = new ConfigurationManagerAttributes { Browsable = false };
   Setting = config.Bind("Judge Pose - " + pose, name, 0f, new ConfigDescription(
    "Adjust the first-person model. Choose a step, then a direction.",
    new AcceptableValueRange<float>(-limit, limit), controls));
  }
  public void Draw() {
   GUILayout.BeginVertical();
   GUILayout.BeginHorizontal();
   GUILayout.Label("Step", GUILayout.Width(40));
   step = GUILayout.Toolbar(step, Labels, GUILayout.Width(145));
   GUILayout.EndHorizontal();
   GUILayout.BeginHorizontal();
   if (GUILayout.Button(minus)) Adjust(-Steps[step]);
   GUILayout.Label(Setting.Value.ToString("0.0"), GUILayout.Width(48));
   if (GUILayout.Button(plus)) Adjust(Steps[step]);
   GUILayout.EndHorizontal();
   GUILayout.EndVertical();
  }
  void Adjust(float delta) { Setting.Value = (float)Math.Round(Setting.Value + delta, 1); Setting.ConfigFile.Save(); }
 }

 readonly Dictionary<string,Axis[]> profiles = new Dictionary<string,Axis[]>();
 ConfigEntry<bool> moveArms;
 int appliedCount;
 readonly Dictionary<string,ConfigEntry<bool>> customActions=new Dictionary<string,ConfigEntry<bool>>();
 ConfigFile settings;
 string editingPose;
 string saveStatus;
 static readonly AccessTools.FieldRef<ProceduralWeaponAnimation,float> AimWeight =
  AccessTools.FieldRefAccess<ProceduralWeaponAnimation,float>("_aimingWeight");
 struct Offset {
  public Vector3 position, angles;
  public static Offset Mix(Offset a,Offset b,float t) => new Offset {
   position=Vector3.Lerp(a.position,b.position,t),angles=Vector3.Lerp(a.angles,b.angles,t)
  };
 }
 Offset ReadPose(string name) {
  var a=profiles[name];
  return new Offset {position=new Vector3(a[1].Setting.Value,a[0].Setting.Value,a[2].Setting.Value)*.01f,
   angles=new Vector3(-a[3].Setting.Value,a[4].Setting.Value,0)};
 }
 static readonly Dictionary<int,string> StatePoses=new Dictionary<int,string>();
 static void Register(string profile,params string[] states) {
  foreach(var state in states)StatePoses[Animator.StringToHash(state)]=profile;
 }
 static JudgeViewmodel() {
  Register("Fire","FIRE","FIRE ARM","DOUBLE_ACTION_FIRE","DRY FIRE","DRY FIRE DOUBLE ACTION");
  Register("Draw","OUT TO IDLE","OUT TO IDLE ARM");
  Register("Holster","IDLE TO OUT","FAST IDLE TO OUT");
  Register("Inspect","LOOK","TO LOOK","FROM LOOK");
  Register("Check chamber","CHECK CHAMBER");
  Register("Check cylinder","CHECK");
  Register("Check fire mode","SWITCH HAMMER TO SINGLE");
  Register("Inventory","OPEN INVENTORY","IN INVENTORY","CLOSE INVENTORY","RELOAD INVENTORY END");
 }
 Offset StateOffset(AnimatorStateInfoWrapper state,Offset stance,float ads,Player player) {
  if(!StatePoses.TryGetValue(state.shortNameHash,out var name))return stance;
  Offset Target(string key)=>customActions[key].Value?ReadPose(key):stance;
  var action=name=="Fire"?Offset.Mix(Target("Fire"),Target("Fire ADS"),ads):Target(name);
  // Match the stance at each endpoint, including native zero-duration state cuts.
  float progress=Mathf.Clamp01(state.normalizedTime);
  float envelope=state.loop ? 1f : Mathf.SmoothStep(0,1,Mathf.Min(progress,1-progress)*6f);
  return Offset.Mix(stance,action,envelope);
 }
 Offset AnimatedOffset(Player player) {
  float ads=Mathf.Clamp01(AimWeight(player.ProceduralWeaponAnimation));
  float standing=Mathf.Clamp01(player.MovementContext.SmoothedPoseLevel);
  var hip=Offset.Mix(ReadPose("Crouched"),ReadPose("Standing"),standing);
  string adsSuffix=HasSight(player.ProceduralWeaponAnimation)?" Optic ADS":" ADS";
  var aim=Offset.Mix(ReadPose("Crouched"+adsSuffix),ReadPose("Standing"+adsSuffix),standing);
  if(player.IsInPronePose){hip=ReadPose("Prone");aim=ReadPose("Prone"+adsSuffix);}
  var stance=Offset.Mix(hip,aim,ads);
  if(player.IsSprintEnabled)stance=ReadPose("Sprint");
  var animator=player.ArmsAnimatorCommon;
  if(animator==null)return stance;
  int layer=animator.GetLayerIndex("Hands");
  if(layer<0)return stance;
  var pose=StateOffset(animator.GetCurrentAnimatorStateInfo(layer),stance,ads,player);
  if(!animator.IsInTransition(layer))return pose;
  return Offset.Mix(pose,StateOffset(animator.GetNextAnimatorStateInfo(layer),stance,ads,player),
   animator.GetTransitionNormalizedTime(layer));
 }

 static readonly string[] PoseNames = {
  "Standing","Standing ADS","Crouched","Crouched ADS","Prone","Prone ADS","Sprint","Standing Optic ADS","Crouched Optic ADS","Prone Optic ADS",
  "Draw","Holster","Inspect","Check chamber","Check cylinder","Check fire mode",
  "Fire","Fire ADS","Inventory"
 };
 static Player ActivePlayer() {
  var p=Singleton<GameWorld>.Instantiated ? Singleton<GameWorld>.Instance.MainPlayer : null;
  if (!p || !p.IsYourPlayer || !p.FirstPersonPointOfView ||
      !(p.HandsController is Player.FirearmController fc) || fc.Item==null) return null;
  return fc.Item.TemplateId==TheJudgePlugin.ItemId || fc.Item.TemplateId=="ef9590b6d87a406b078ba926" ? p : null;
 }
 internal static string CurrentPose(Player p) {
  var fc=(Player.FirearmController)p.HandsController;
  var op=fc.CurrentHandsOperation;
  if (op is Player.FirearmController.SpawnOperation) return "Draw";
  if (op is Player.FirearmController.Remove) return "Holster";
  if (op is Player.FirearmController.ReloadCylinderMagOperation reload)
   return reload._highLevelMasteringFullReload ? "Full reload" : "Single reload";
  if (op is Player.FirearmController.UtilityOperation utility) {
   switch(utility._utilityOperationType) {
    case Player.FirearmController.UtilityOperation.EUtilityType.ExamineWeapon: return "Inspect";
    case Player.FirearmController.UtilityOperation.EUtilityType.CheckChamber: return "Check chamber";
    case Player.FirearmController.UtilityOperation.EUtilityType.CheckMagazine: return "Check cylinder";
    case Player.FirearmController.UtilityOperation.EUtilityType.CheckFireMode: return "Check fire mode";
   }
  }
  if (fc.IsInventoryOpen()) return "Inventory";
  if (op is Player.FirearmController.FireOperationBase) return fc.IsAiming ? "Fire ADS" : "Fire";
  if (p.IsSprintEnabled) return "Sprint";
  string suffix=HasSight(p.ProceduralWeaponAnimation)?" Optic ADS":" ADS";
  if (p.IsInPronePose) return fc.IsAiming ? "Prone"+suffix : "Prone";
  if (p.PoseLevel<.99f) return fc.IsAiming ? "Crouched"+suffix : "Crouched";
  return fc.IsAiming ? "Standing"+suffix : "Standing";
 }
 static bool open;
 Rect window = new Rect(40, 80, 500, 0);
 CursorLockMode oldLock;
 bool oldVisible;
 Transform rig;
 Transform[] roots = Array.Empty<Transform>();
 Vector3[] positions;
 Quaternion[] rotations;
 Camera rendering;

 internal void Initialize(ConfigFile config) {
  settings=config;
  BindProfiles(config);
  var h = new Harmony("team.aminus.thejudge.viewmodel.input");
  h.Patch(AccessTools.Method(typeof(ProceduralWeaponAnimation),"method_11"),prefix:new HarmonyMethod(typeof(JudgeViewmodel),nameof(PreferMountedSight)));
  h.Patch(AccessTools.Method(typeof(GamePlayerOwner),"TranslateCommand"),prefix:new HarmonyMethod(typeof(JudgeViewmodel),nameof(Command)));
  h.Patch(AccessTools.DeclaredMethod(typeof(HideoutPlayerOwner),"TranslateCommand"),prefix:new HarmonyMethod(typeof(JudgeViewmodel),nameof(Command)));
  h.Patch(AccessTools.Method(typeof(GamePlayerOwner),"TranslateAxes"),prefix:new HarmonyMethod(typeof(JudgeViewmodel),nameof(Axes)));
 }
 // Resolve the mounted sight before EFT computes the aiming plane and camera depth.
 static bool HasSight(ProceduralWeaponAnimation animation) =>
  animation.ScopeAimTransforms.Count>0 && animation.CurrentScope.Mod!=null &&
  !animation.CurrentScope.AlignIfAvailable;
 static bool MountedSight(ProceduralWeaponAnimation animation,Player.FirearmController fc) {
  if(!fc || fc.Item==null || (fc.Item.TemplateId!=TheJudgePlugin.ItemId &&
    fc.Item.TemplateId!="ef9590b6d87a406b078ba926") || !animation.FirstPersonPointOfView ||
    HasSight(animation) || !animation.HandsContainer.Weapon)return false;
  var available=animation.ScopeAimTransforms;
  var valid=available.FindAll(a=>a.ScopePrefabCache && !a.AlignIfAvailable && a.Mod!=null);
  if(valid.Count==0) {
   foreach(var mod in fc.Weapon.Mods) {
    var sight=mod.GetItemComponent<SightComponent>();
    if(sight==null || mod is IronSight)continue;
    string prefab=Path.GetFileNameWithoutExtension(mod.Template.Prefab.path);
    foreach(var cache in animation.HandsContainer.Weapon.GetComponentsInChildren<ScopePrefabCache>()) {
     if(!cache.name.StartsWith(prefab,StringComparison.OrdinalIgnoreCase))continue;
     foreach(var bone in cache.GetComponentsInChildren<Transform>()) {
      if(!bone.name.StartsWith("mod_aim_camera",StringComparison.Ordinal) ||
       !animation.ScopeRotationWithinLimits(bone))continue;
      float angle=TransformTools.GetRotationRelativeToParent(animation.HandsContainer.Weapon,bone).eulerAngles.y;
      valid.Add(new ProceduralWeaponAnimation.SightNBone { Bone=bone,Mod=sight,ScopePrefabCache=cache,
       Rotation=180-angle,LeftStanceRotation=190-angle,BoneRelatesToOptics=cache.IsOpticBone(bone) });
     }
    }
   }
  }
  if(valid.Count==0)return false;
  available.Clear();available.AddRange(valid);return true;
 }
 static void PreferMountedSight(ProceduralWeaponAnimation __instance,Player.FirearmController ____firearmController) {
  MountedSight(__instance,____firearmController);
 }
 float nextSightCheck;
 void CheckAttachedSight() {
  if(Time.unscaledTime<nextSightCheck)return;
  nextSightCheck=Time.unscaledTime+.25f;
  var p=ActivePlayer();
  if(!p || !p.ProceduralWeaponAnimation.IsAiming)return;
  var animation=p.ProceduralWeaponAnimation;
  if(MountedSight(animation,(Player.FirearmController)p.HandsController))animation.method_11();
 }
 void BindProfiles(ConfigFile config) {
  var autoSave=config.SaveOnConfigSet;
  config.SaveOnConfigSet=false;
  try {
  foreach (var pose in PoseNames) profiles.Add(pose,new[] {
   new Axis(config,pose,"Vertical (cm)","Down","Up",50),
   new Axis(config,pose,"Horizontal (cm)","Left","Right",50),
   new Axis(config,pose,"Depth (cm)","Back","Forward",50),
   new Axis(config,pose,"Pitch (deg)","Muzzle down","Muzzle up",60),
   new Axis(config,pose,"Yaw (deg)","Turn left","Turn right",60)
  });
  moveArms=config.Bind("Judge Viewmodel","Move arms with weapon",true,
   new ConfigDescription("Move both arms with the weapon model.",null,
    new ConfigurationManagerAttributes {CustomDrawer = _ => DrawControls()}));
  MigrateGlobalOffsets(config);
  foreach(string name in PoseNames) {
   if(name=="Sprint" || name.StartsWith("Standing") || name.StartsWith("Crouched") || name.StartsWith("Prone"))continue;
   var old=ReadPose(name);
   var legacy=ReadPose("Standing");
   bool edited=(old.position!=Vector3.zero || old.angles!=Vector3.zero) &&
    (old.position!=legacy.position || old.angles!=legacy.angles);
   customActions[name]=config.Bind("Judge Pose - "+name,"Use custom action offset",edited,
    new ConfigDescription("Override the current stance during this action.",null,new ConfigurationManagerAttributes {Browsable=false}));
  }
  } finally {config.SaveOnConfigSet=autoSave;}
  config.Save();
 }
 void MigrateGlobalOffsets(ConfigFile config) {
  if(!File.Exists(config.ConfigFilePath))return;
  var keys=new HashSet<string>();
  var sections=new HashSet<string>();
  string section="";
  foreach(var raw in File.ReadLines(config.ConfigFilePath)){
   string line=raw.Trim();
   if(line.StartsWith("[") && line.EndsWith("]")) {
    section=line.Substring(1,line.Length-2);
    sections.Add(section);
   } else if(section=="Judge Viewmodel" && !line.StartsWith("#") && line.Contains("=")) {
    keys.Add(line.Substring(0,line.IndexOf('=')).Trim());
   }
  }
  for(int i=0;i<profiles["Standing"].Length;i++){
   string name=profiles["Standing"][i].Setting.Definition.Key;
   if(!keys.Contains(name))continue;
   var old=config.Bind("Judge Viewmodel",name,0f);
   foreach(var profile in profiles.Values)
    if(!sections.Contains(profile[i].Setting.Definition.Section))profile[i].Setting.Value=old.Value;
   config.Remove(old.Definition);
  }
 }
 static bool Command(ref InputNode.ETranslateResult __result) {
  if (!open) return true;
  __result = InputNode.ETranslateResult.BlockAll;
  return false;
 }
 static bool Axes(ref float[] axes) {
  if (!open) return true;
  if (axes != null) Array.Clear(axes,0,axes.Length);
  return false;
 }
 void SetOpen(bool value) {
  if (value == open) return;
  if (value) { var p=ActivePlayer();editingPose=p?CurrentPose(p):null;saveStatus=null;oldLock = Cursor.lockState; oldVisible = Cursor.visible; }
  if(!value){settings?.Save();editingPose=null;}
  open = value;
  Cursor.lockState = open ? CursorLockMode.None : oldLock;
  Cursor.visible = open || oldVisible;
 }
 void Update() {
  if (Input.GetKeyDown(KeyCode.F9)) SetOpen(!open);
  else if (open && (Input.GetKeyDown(KeyCode.Escape) || Input.GetKeyDown(KeyCode.F12))) SetOpen(false);
 }
 void LateUpdate() {
  CheckAttachedSight();
  if (open) { Cursor.lockState = CursorLockMode.None; Cursor.visible = true; }
 }
 void OnGUI() {
  if (!open || moveArms == null) return;
  GUI.depth = -1000;
  window = GUILayout.Window(GetInstanceID(),window,DrawWindow,"Judge Viewmodel",GUILayout.Width(360));
 }
 void DrawWindow(int id) {
  DrawControls();
  if (GUILayout.Button("Close")) SetOpen(false);
  GUI.DragWindow(new Rect(0,0,360,24));
 }
 void DrawControls() {
  bool next=GUILayout.Toggle(moveArms.Value,"Move arms with weapon");
  if(next!=moveArms.Value){moveArms.Value=next;settings.Save();}
  var player=ActivePlayer();
  if (!player) { GUILayout.Label("Equip The Judge to edit its current pose."); return; }
  string pose=open && editingPose!=null?editingPose:CurrentPose(player);
  GUILayout.Label("Current pose: "+pose);
  if(customActions.TryGetValue(pose,out var custom)) {
   bool enable=GUILayout.Toggle(custom.Value,"Use custom action offset");
   if(enable!=custom.Value){custom.Value=enable;settings.Save();}
   if(!enable){GUILayout.Label("Using the current stance offset throughout this action.");return;}
  }
  var axes=profiles[pose];
  foreach (var axis in axes) {
   GUILayout.Label(axis.Setting.Definition.Key);
   axis.Draw();
  }
  if(GUILayout.Button("Reset this pose")) {foreach(var axis in axes)axis.Setting.Value=0;settings.Save();}
  if(GUILayout.Button("Save offsets")){settings.Save();saveStatus="Saved " + pose;}
  if(saveStatus!=null)GUILayout.Label(saveStatus);
 }

 void OnDisable() {
  Camera.onPreCull -= BeforeRender; Camera.onPostRender -= AfterRender;
  Restore(); SetOpen(false);
 }
 void CacheRig(Transform weapon, Player player) {
  rig = weapon;
  var result = new List<Transform> { weapon };
  // The EFT view rig has separate collarbone branches beside Weapon_root.
  if (weapon.parent && weapon.parent.parent) {
   foreach (Transform sibling in weapon.parent.parent)
    if (sibling.name=="Base HumanLCollarbone" || sibling.name=="Base HumanRCollarbone") result.Add(sibling);
  }
  // The animated weapon skeleton and the visible player skin can use separate arm bones.
  if(player.PlayerBones.Upperarms!=null) foreach(var arm in player.PlayerBones.Upperarms) {
   if (!arm || arm==weapon || weapon.IsChildOf(arm) || arm.IsChildOf(weapon)) continue;
   if(result.Exists(t=>arm==t || arm.IsChildOf(t))) continue;
   result.RemoveAll(t=>t!=weapon && t.IsChildOf(arm));
   result.Add(arm);
  }
  roots=result.ToArray(); positions=new Vector3[roots.Length]; rotations=new Quaternion[roots.Length];
 }
 // The shield carry controller owns the sidearm pose while both items are raised.
 static bool checkedShieldCompatibility;
 static Func<Player.FirearmController,bool> shieldControls;
 static bool IsShieldSidearm(Player player) {
  if (!checkedShieldCompatibility) {
   checkedShieldCompatibility=true;
   var type=AccessTools.TypeByName("Hawks.RonShields.ShieldCarry");
   var method=type==null ? null : AccessTools.DeclaredMethod(type,"Controls",new[]{typeof(Player.FirearmController)});
   if(method?.IsStatic==true && method.ReturnType==typeof(bool))
    shieldControls=(Func<Player.FirearmController,bool>)Delegate.CreateDelegate(typeof(Func<Player.FirearmController,bool>),method);
  }
  return player.HandsController is Player.FirearmController gun && shieldControls?.Invoke(gun)==true;
 }
 const string FrontIron="843c5ef82279b410bd43cefa";
 const string RearIron="396aa8e4ea6fecee9018a5cb";
 static bool HasCompleteIronPair(Weapon weapon) {
  bool front=false,rear=false;
  foreach(var mod in weapon.Mods) {
   if(mod.TemplateId==FrontIron)front=true;
   else if(mod.TemplateId==RearIron)rear=true;
   else if(mod is IronSight || mod.GetItemComponent<SightComponent>()!=null)return false;
  }
  return front && rear;
 }
 void OnEnable() { Camera.onPreCull += BeforeRender; Camera.onPostRender += AfterRender; }
 void BeforeRender(Camera camera) {
  if (moveArms==null || rendering || camera.cameraType!=CameraType.Game) return;
  var player=ActivePlayer();
  if(!player || IsShieldSidearm(player) ||
     !(player.HandsController is Player.FirearmController gun) ||
     !HasCompleteIronPair(gun.Weapon))return;
  var animation=player.ProceduralWeaponAnimation;
  var hands=animation?.HandsContainer;
  if(hands==null || !hands.WeaponRootAnim || !hands.CameraTransform || HasSight(animation))return;
  float weight=Mathf.SmoothStep(0,1,Mathf.Clamp01(AimWeight(animation)));
  if(weight<=0)return;
  var offset=player.IsInPronePose?ReadPose("Prone ADS"):
   Offset.Mix(ReadPose("Crouched ADS"),ReadPose("Standing ADS"),player.MovementContext.SmoothedPoseLevel);
  if(rig!=hands.WeaponRootAnim)CacheRig(hands.WeaponRootAnim,player);
  var basis=hands.CameraTransform.rotation;
  var pivot=rig.position;
  var shift=basis*(offset.position*weight);
  var turn=basis*Quaternion.Euler(offset.angles*weight)*Quaternion.Inverse(basis);
  rendering=camera;
  appliedCount=roots.Length;
  for(int i=0;i<appliedCount;i++){
   var target=roots[i];
   positions[i]=target.localPosition;
   rotations[i]=target.localRotation;
   target.SetPositionAndRotation(pivot+shift+turn*(target.position-pivot),turn*target.rotation);
  }
 }
 void AfterRender(Camera camera) { if (rendering==camera) Restore(); }
 void Restore() {
  if (!rendering) return;
  for (int i=0;i<appliedCount;i++) if (roots[i]) {
   roots[i].localPosition=positions[i]; roots[i].localRotation=rotations[i];
  }
  rendering=null;
 }
}
}





