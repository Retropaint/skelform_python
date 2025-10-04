import math
import copy
import zipfile
from types import SimpleNamespace


def get_frame_by_time(armature, anim_idx, elapsed, reverse):
    anim = armature.animations[anim_idx]
    last_frame = anim.keyframes[-1].frame

    frametime = 1 / anim.fps
    frame = elapsed / frametime

    if reverse:
        frame = last_frame - frame

    return frame


def animate(armature, anim_idx, frame, after_animate=None):
    bones = []
    keyframes = armature.animations[anim_idx].keyframes

    frame %= keyframes[-1].frame

    for bone in armature.bones:
        bone = copy.deepcopy(bone)
        bones.append(bone)

        # interpolate
        # yapf: disable
        bone.rot     += animate_float(keyframes, frame, bone.id, "Rotation",  0)
        bone.pos.x   += animate_float(keyframes, frame, bone.id, "PositionX", 0)
        bone.pos.y   += animate_float(keyframes, frame, bone.id, "PositionY", 0)
        bone.scale.x *= animate_float(keyframes, frame, bone.id, "ScaleX",    1)
        bone.scale.y *= animate_float(keyframes, frame, bone.id, "ScaleY",    1)

    return bones


def rotate(point, rot):
    return SimpleNamespace(
        x=point.x * math.cos(rot) - point.y * math.sin(rot),
        y=point.x * math.sin(rot) + point.y * math.cos(rot),
    )


def inheritance(bones, ik_rots):
    for bone in bones:
        if bone.parent_id != -1:
            # inherit parent
            parent = bones[bone.parent_id]

            bone.rot += parent.rot
            bone.scale.x *= parent.scale.x
            bone.scale.y *= parent.scale.y
            bone.pos.x *= parent.scale.x
            bone.pos.y *= parent.scale.y

            bone.pos = rotate(bone.pos, parent.rot)

            bone.pos.x += parent.pos.x
            bone.pos.y += parent.pos.y

        if len(ik_rots) and ik_rots[bone.id]:
            bone.id.rot = ik_rots[bone.id]

    return bones


def Vec2(x, y):
    return SimpleNamespace(x=x, y=y)


def magnitude(vec):
    return math.sqrt(vec.x * vec.x + vec.y * vec.y)


def normalize(vec):
    mag = magnitude(vec)
    return Vec2(vec.x / mag, vec.y / mag)


def vec_sub(vec1, vec2):
    return SimpleNamespace(x=vec1.x - vec2.x, y=vec1.y - vec2.y)


def inverse_kinematics(bones, families):
    ik_rots = {}

    for family in families:
        if family.target_id == -1:
            continue
        next_pos = bones[family.target_id].pos
        next_length = 0
        for i in range(len(family.bone_ids)):
            length = Vec2(0, 0)
            if i != len(family.bone_ids) - 1:
                length = (
                    normalize(next_pos - bones[family.bone_ids[i]].pos) * next_length
                )

            if i != 0:
                next_bone = bones[family.bone_ids[i - 1]]
                next_length = magnitude(bones[family.bone_ids[i]] - next_bone.pos)

            bones[family.bone_ids[i]].pos = next_pos - length
            next_pos = bones[family.bone_ids[i]].pos

    return ik_rots


def animate_float(keyframes, frame, bone_id, element, default):
    prev_kf = {}
    next_kf = {}

    for kf in keyframes:
        if kf.frame > frame:
            break
        elif kf.bone_id == bone_id and kf.element == element:
            prev_kf = kf

    for kf in keyframes:
        if kf.frame >= frame and kf.bone_id == bone_id and kf.element == element:
            next_kf = kf
            break

    if prev_kf == {}:
        prev_kf = next_kf
    elif next_kf == {}:
        next_kf = prev_kf

    if prev_kf == {} and next_kf == {}:
        return default

    total_frames = next_kf.frame - prev_kf.frame
    current_frame = frame - prev_kf.frame

    if total_frames == 0:
        return prev_kf.value

    interp = current_frame / total_frames
    start = prev_kf.value
    end = next_kf.value - prev_kf.value
    result = start + (end * interp)
    return result
