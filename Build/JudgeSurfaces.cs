using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public class JudgeSurfaces
{
    public static void Build()
    {
        AssetDatabase.Refresh();
        var output = "E:/SPT Mod Workspace/PAYDAY3 Justicar/SPT/Package/bundles";
        var builds = new[]
        {
            Configure("JudgeMaterials", "hawks_judge_materials.bundle"),
            Configure("RapidoMaterials", "hawks_judge_rapido_materials.bundle"),
        };
        AssetDatabase.SaveAssets();
        if (
            !BuildPipeline.BuildAssetBundles(
                output,
                builds,
                BuildAssetBundleOptions.ChunkBasedCompression | BuildAssetBundleOptions.StrictMode,
                BuildTarget.StandaloneWindows64
            )
        )
            throw new System.Exception("Judge material build failed");
    }

    public static void BuildForeGrip()
    {
        AssetDatabase.Refresh();
        var entry = Configure("JudgeForeGrip", "hawks_judge_foregrip_material.bundle");
        AssetDatabase.SaveAssets();
        string output = "E:/Temp/Justicar-RSh/foregrip-output";
        Directory.CreateDirectory(output);
        if (
            !BuildPipeline.BuildAssetBundles(
                output,
                new[] { entry },
                BuildAssetBundleOptions.ChunkBasedCompression | BuildAssetBundleOptions.StrictMode,
                BuildTarget.StandaloneWindows64
            )
        )
            throw new System.Exception("Foregrip material build failed");
    }

    public static void BuildMuzzles()
    {
        AssetDatabase.Refresh();
        var entry = Configure("JudgeMuzzles", "hawks_judge_muzzle_materials.bundle");
        AssetDatabase.SaveAssets();
        string output = "E:/Temp/Justicar-RSh/muzzle-output";
        Directory.CreateDirectory(output);
        if (
            !BuildPipeline.BuildAssetBundles(
                output,
                new[] { entry },
                BuildAssetBundleOptions.ChunkBasedCompression | BuildAssetBundleOptions.StrictMode,
                BuildTarget.StandaloneWindows64
            )
        )
            throw new System.Exception("Foregrip material build failed");
    }

    static AssetBundleBuild Configure(string folder, string bundle)
    {
        var materials = Directory
            .GetFiles("Assets/" + folder, "*.mat")
            .Select(f => f.Replace('\\', '/'))
            .ToArray();
        foreach (string path in materials)
        {
            string name = Path.GetFileNameWithoutExtension(path);
            string prefix = "Assets/" + folder + "/Surface/" + name;
            if (!File.Exists(prefix + "_normal.png"))
                continue;
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            mat.name = name;
            mat.mainTexture = Import("Assets/" + folder + "/" + name + ".png", false, true);
            mat.SetTexture("_BumpMap", Import(prefix + "_normal.png", true, false));
            var surface = Import(prefix + "_surface.png", false, false);
            mat.SetTexture("_MetallicGlossMap", surface);
            mat.SetTexture("_OcclusionMap", surface);
            mat.SetFloat("_GlossMapScale", 1);
            mat.SetFloat("_OcclusionStrength", 0.7f);
            mat.EnableKeyword("_METALLICGLOSSMAP");
            mat.EnableKeyword("_NORMALMAP");
            EditorUtility.SetDirty(mat);
        }
        return new AssetBundleBuild { assetBundleName = bundle, assetNames = materials };
    }

    static Texture2D Import(string path, bool normals, bool srgb)
    {
        var importer = (TextureImporter)AssetImporter.GetAtPath(path);
        importer.textureType = normals
            ? TextureImporterType.NormalMap
            : TextureImporterType.Default;
        importer.sRGBTexture = srgb;
        importer.maxTextureSize = 8192;
        importer.npotScale = TextureImporterNPOTScale.None;
        importer.SaveAndReimport();
        return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
    }
}
