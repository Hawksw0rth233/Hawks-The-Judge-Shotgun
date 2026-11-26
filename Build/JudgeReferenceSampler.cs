using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.Animations;
using UnityEngine.Playables;

public class JudgeReferenceSampler
{
    [Serializable]
    public class Node
    {
        public string path;
        public float[] pos,
            rot,
            scale;
    }

    [Serializable]
    public class Rig
    {
        public Node[] nodes;
    }

    public static void Run()
    {
        string dir = "E:/Temp/Justicar-RSh/",
            source = "E:/SPT 4.1.6/SPT_Runtime/user/mods/makeshotgunsgreatagain/bundles";
        var root = new GameObject("Sampler");
        var ns = JsonUtility.FromJson<Rig>(File.ReadAllText(dir + "rig.json")).nodes;
        var tr = new Transform[ns.Length];
        var lookup = new Dictionary<string, Transform>();
        for (int i = 0; i < ns.Length; i++)
        {
            var n = ns[i];
            int split = n.path.LastIndexOf('/');
            var t = new GameObject(n.path.Substring(split + 1)).transform;
            t.SetParent(split < 0 ? root.transform : lookup[n.path.Substring(0, split)], false);
            lookup[n.path] = tr[i] = t;
        }
        var actor = root.AddComponent<Animator>();
        actor.avatar = AvatarBuilder.BuildGenericAvatar(root, "");
        actor.cullingMode = AnimatorCullingMode.AlwaysAnimate;
        foreach (var f in Directory.GetFiles(source, "raging_judge_animations.bundle"))
        {
            var b = AssetBundle.LoadFromFile(f);
            if (!b)
                continue;
            foreach (var clip in b.LoadAllAssets<AnimationClip>())
            {
                if (
                    !System.Text.RegularExpressions.Regex.IsMatch(
                        clip.name,
                        @"^rsh12_ammo_in_[0-4]$"
                    )
                )
                    continue;
                for (int i = 0; i < ns.Length; i++)
                {
                    var n = ns[i];
                    tr[i].localPosition = new Vector3(n.pos[0], n.pos[1], n.pos[2]);
                    tr[i].localRotation = new Quaternion(n.rot[0], n.rot[1], n.rot[2], n.rot[3]);
                    tr[i].localScale = new Vector3(n.scale[0], n.scale[1], n.scale[2]);
                }
                var graph = PlayableGraph.Create("Sample Judge");
                graph.SetTimeUpdateMode(DirectorUpdateMode.Manual);
                var play = AnimationClipPlayable.Create(graph, clip);
                AnimationPlayableOutput.Create(graph, "rig", actor).SetSourcePlayable(play);
                graph.Play();
                int frames = Mathf.CeilToInt(clip.length * 30) + 1;
                using (
                    var w = new BinaryWriter(
                        File.Create(dir + "msga-samples/" + clip.name + ".bin")
                    )
                )
                {
                    for (int j = 0; j < frames; j++)
                    {
                        play.SetTime(Mathf.Min(j / 30f, clip.length));
                        graph.Evaluate(0);
                        foreach (var t in tr)
                        {
                            var m = t.localToWorldMatrix;
                            for (int r = 0; r < 4; r++)
                            for (int c = 0; c < 4; c++)
                                w.Write(m[r, c]);
                        }
                    }
                }
                graph.Destroy();
            }
        }
    }
}
