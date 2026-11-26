using SPTarkov.Server.Core.Models.Spt.Mod;

namespace Hawks.TheJudge;

public record ModMetadata : IModMetadata
{
    public string ModGuid { get; init; } = "team.aminus.thejudge";
    public string Name { get; init; } = "Hawks's The Judge Shotgun";
    public string Author { get; init; } = "Hawks";
    public List<string>? Contributors { get; init; }
    public SemanticVersioning.Version Version { get; init; } = new("0.1.0");
    public SemanticVersioning.Range SptVersion { get; init; } = new("~4.1.6");
    public List<string>? Incompatibilities { get; init; }
    public Dictionary<string, SemanticVersioning.Range>? ModDependencies { get; init; } =
        new()
        {
            ["com.wtt.commonlib"] = new("^3.0.6"),
            ["com.vinihns.makeshotgunsgreatagain"] = new("^1.20.0"),
        };
    public string? Url { get; init; } = null;
    public string License { get; init; } = "MIT (mod code); third-party game assets excluded";
    public bool HasPrepatcher { get; init; } = false;
}
