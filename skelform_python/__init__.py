import math
import copy
import zipfile

def get_frame_by_time(armature, anim_idx, elapsed, reverse):
    anim = armature["animations"][anim_idx]
    last_frame = anim["keyframes"][-1]["frame"]

    frametime = 1 / anim["fps"]
    frame = elapsed / frametime

    if reverse:
        frame = last_frame - frame

    return frame


def animate(armature, anim_idx, frame, after_animate=None):
    props = []
    keyframes = armature["animations"][anim_idx]["keyframes"]

    frame %= keyframes[-1]["frame"]

    for bone in armature["bones"]:
        prop = copy.deepcopy(bone)
        props.append(prop)

        # interpolate
        # yapf: disable
        prop["rot"]        += animate_float(keyframes, frame, prop["id"], "Rotation",  0)
        prop["pos"]["x"]   += animate_float(keyframes, frame, prop["id"], "PositionX", 0)
        prop["pos"]["y"]   += animate_float(keyframes, frame, prop["id"], "PositionY", 0)
        prop["scale"]["x"] *= animate_float(keyframes, frame, prop["id"], "ScaleX",    1)
        prop["scale"]["y"] *= animate_float(keyframes, frame, prop["id"], "ScaleY",    1)

        try:
            after_animate(props, prop)
        except:
            pass

        if prop["parent_id"] == -1:
            continue

        # inherit parent
        parent = [prop for prop in props if prop["id"] == props[-1]["parent_id"]][0]

        prop["rot"] += parent["rot"]
        prop["scale"]["x"] *= parent["scale"]["x"]
        prop["scale"]["y"] *= parent["scale"]["y"]
        prop["pos"]["x"] *= parent["scale"]["x"]
        prop["pos"]["y"] *= parent["scale"]["y"]

        x = copy.deepcopy(prop["pos"]["x"])
        y = copy.deepcopy(prop["pos"]["y"])
        prop["pos"]["x"] = x * math.cos(parent["rot"]) - y * math.sin(parent["rot"])
        prop["pos"]["y"] = x * math.sin(parent["rot"]) + y * math.cos(parent["rot"])

        prop["pos"]["x"] += parent["pos"]["x"]
        prop["pos"]["y"] += parent["pos"]["y"]

    return props


def animate_float(keyframes, frame, bone_id, element, default):
    prev_kf = {}
    next_kf = {}

    for kf in keyframes:
        if kf["frame"] > frame:
            break
        elif kf["bone_id"] == bone_id and kf["element"] == element:
            prev_kf = kf

    for kf in keyframes:
        if (
            kf["frame"] >= frame
            and kf["bone_id"] == bone_id
            and kf["element"] == element
        ):
            next_kf = kf
            break

    if prev_kf == {}:
        prev_kf = next_kf
    elif next_kf == {}:
        next_kf = prev_kf

    if prev_kf == {} and next_kf == {}:
        return default

    total_frames = next_kf["frame"] - prev_kf["frame"]
    current_frame = frame - prev_kf["frame"]

    if total_frames == 0:
        return prev_kf["value"]

    interp = current_frame / total_frames
    start = prev_kf["value"]
    end = next_kf["value"] - prev_kf["value"]
    result = start + (end * interp)
    return result
