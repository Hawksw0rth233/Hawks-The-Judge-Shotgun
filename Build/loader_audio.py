def align_loader_sounds(data):
    """Replace the five loose-cartridge sounds on the native fistful state."""
    changed = 0
    for state in data.get("_stateHashToEventsCollection", []):
        events = state["_animationEvents"]
        inserts = [
            event for event in events if event["_functionName"] == "AddAmmoInMag"
        ]
        sounds = {
            event["Parameter"]["StringParam"]: event
            for event in events
            if event["_functionName"] == "Sound"
        }
        if len(inserts) != 5 or "AmmoIn" not in sounds:
            continue
        sequence = [event for event in events if event["_functionName"] != "Sound"]
        for name, time in [("MagPullOut", 0.07), ("AmmoIn", 0.60), ("HandOff", 0.77)]:
            event = dict(sounds[name])
            event["_time"] = time
            sequence.append(event)
        state["_animationEvents"] = sorted(sequence, key=lambda event: event["_time"])
        changed += 1
    return changed
