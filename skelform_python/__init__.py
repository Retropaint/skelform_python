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
    bones = []
    keyframes = armature["animations"][anim_idx]["keyframes"]

    frame %= keyframes[-1]["frame"]

    for bone in armature["bones"]:
        bone = copy.deepcopy(bone)
        bones.append(bone)

        # interpolate
        # yapf: disable
        bone["rot"]        += animate_float(keyframes, frame, bone["id"], "Rotation",  0)
        bone["pos"]["x"]   += animate_float(keyframes, frame, bone["id"], "PositionX", 0)
        bone["pos"]["y"]   += animate_float(keyframes, frame, bone["id"], "PositionY", 0)
        bone["scale"]["x"] *= animate_float(keyframes, frame, bone["id"], "ScaleX",    1)
        bone["scale"]["y"] *= animate_float(keyframes, frame, bone["id"], "ScaleY",    1)

        try:
            after_animate(bones, bone)
        except:
            pass

        if bone["parent_id"] == -1:
            continue

        # inherit parent
        parent = [bone for bone in bones if bone["id"] == bones[-1]["parent_id"]][0]

        bones["rot"] += parent["rot"]
        bones["scale"]["x"] *= parent["scale"]["x"]
        bones["scale"]["y"] *= parent["scale"]["y"]
        bones["pos"]["x"] *= parent["scale"]["x"]
        bones["pos"]["y"] *= parent["scale"]["y"]

        x = copy.copy(bone["pos"]["x"])
        y = copy.deepcopy(bone["pos"]["y"])
        bone["pos"]["x"] = x * math.cos(parent["rot"]) - y * math.sin(parent["rot"])
        bone["pos"]["y"] = x * math.sin(parent["rot"]) + y * math.cos(parent["rot"])

        bone["pos"]["x"] += parent["pos"]["x"]
        bone["pos"]["y"] += parent["pos"]["y"]

    return bones


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
