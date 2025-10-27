import math
import copy
import zipfile
from dataclasses import dataclass
from typing import Optional


@dataclass
class Vec2:
    x: float
    y: float


@dataclass
class Bone:
    _name: str
    id: int
    parent_id: int
    style_ids: Optional[list[int]]
    tex_idx: Optional[int]
    rot: float
    scale: Vec2
    pos: Vec2
    init_rot: float
    init_scale: Vec2
    init_pos: Vec2
    zindex: Optional[int] = 0


@dataclass
class IkFamily:
    target_id: int
    constraint: str
    bone_ids: list[int]


@dataclass
class Keyframe:
    frame: int
    bone_id: int
    _element: str
    value: float


@dataclass
class Animation:
    name: str
    keyframes: list[Keyframe]
    fps: int


@dataclass
class Texture:
    _name: str
    offset: Vec2
    size: Vec2


@dataclass
class Style:
    _name: str
    textures: list[Texture]


@dataclass
class Armature:
    bones: list[Bone]
    animations: Optional[list[Animation]]
    ik_families: Optional[list[IkFamily]]
    styles: list[Style]


def animate(armature, animation: Animation, frame, blend_frames):
    bones = []
    kf = animation.keyframes
    bf = blend_frames
    ikf = interpolate_keyframes

    for bone in armature.bones:
        bone = copy.deepcopy(bone)
        bones.append(bone)
        id = bone.id

        # interpolate
        # yapf: disable
        bone.rot     = ikf("Rotation",  bone.rot,     bone.init_rot,     kf, frame, id, bf)
        bone.pos.x   = ikf("PositionX", bone.pos.x,   bone.init_pos.x,   kf, frame, id, bf)
        bone.pos.y   = ikf("PositionY", bone.pos.y,   bone.init_pos.y,   kf, frame, id, bf)
        bone.scale.x = ikf("ScaleX",    bone.scale.x, bone.init_scale.x, kf, frame, id, bf)
        bone.scale.y = ikf("ScaleY",    bone.scale.y, bone.init_scale.y, kf, frame, id, bf)

    return bones


def rotate(point: Vec2, rot: float):
    return Vec2(
        point.x * math.cos(rot) - point.y * math.sin(rot),
        point.x * math.sin(rot) + point.y * math.cos(rot),
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

        if bone.id in ik_rots:
            bone.rot = ik_rots[bone.id]

    return bones


def magnitude(vec):
    return math.sqrt(vec.x * vec.x + vec.y * vec.y)


def normalize(vec):
    mag = magnitude(vec)
    return Vec2(vec.x / mag, vec.y / mag)


def vec_sub(vec1, vec2):
    return Vec2(vec1.x - vec2.x, vec1.y - vec2.y)


def vec_add(vec1, vec2):
    return Vec2(vec1.x + vec2.x, vec1.y + vec2.y)


def vec_mul(vec1, vec2):
    return Vec2(vec1.x * vec2.x, vec1.y * vec2.y)


def inverse_kinematics(bones, ik_families, reverse_constraints):
    ik_rots = {}

    for family in ik_families:
        if family.target_id == -1:
            continue

        start_pos = copy.deepcopy(bones[family.bone_ids[0]].pos)
        base_line = normalize(vec_sub(bones[family.target_id].pos, start_pos))
        base_angle = math.atan2(base_line.y, base_line.x)

        next_pos = bones[family.target_id].pos
        next_length = 0
        for i in range(len(family.bone_ids) - 1, -1, -1):
            length = Vec2(0, 0)
            if i != len(family.bone_ids) - 1:
                length = normalize(vec_sub(next_pos, bones[family.bone_ids[i]].pos))
                length.x *= next_length
                length.y *= next_length

            if i != 0:
                next_bone = bones[family.bone_ids[i - 1]]
                next_length = magnitude(
                    vec_sub(bones[family.bone_ids[i]].pos, next_bone.pos)
                )

            bones[family.bone_ids[i]].pos = vec_sub(next_pos, length)
            next_pos = bones[family.bone_ids[i]].pos

        prev_pos = start_pos
        prev_length = 0
        for i in range(len(family.bone_ids)):
            length = Vec2(0, 0)
            if i != 0:
                length = normalize(vec_sub(prev_pos, bones[family.bone_ids[i]].pos))
                length.x *= prev_length
                length.y *= prev_length

            if i != len(family.bone_ids) - 1:
                prev_bone = bones[family.bone_ids[i + 1]]
                prev_length = magnitude(
                    vec_sub(bones[family.bone_ids[i]].pos, prev_bone.pos)
                )

            bones[family.bone_ids[i]].pos = vec_sub(prev_pos, length)

            if i != 0 and i != len(family.bone_ids) - 1 and family.constraint != "None":
                joint_line = normalize(vec_sub(prev_pos, bones[family.bone_ids[i]].pos))
                joint_angle = math.atan2(joint_line.y, joint_line.x) - base_angle

                constraint_min = 0
                constraint_max = 0
                if not reverse_constraints:
                    if family.constraint == "Clockwise":
                        constraint_min = -3.14
                    else:
                        constraint_max = 3.14
                else:
                    if family.constraint == "Clockwise":
                        constraint_max = 3.14
                    else:
                        constraint_min = -3.14

                if joint_angle > constraint_max or joint_angle < constraint_min:
                    push_angle = -joint_angle * 2
                    new_point = rotate(
                        vec_sub(bones[family.bone_ids[i]].pos, prev_pos),
                        push_angle,
                    )
                    bones[family.bone_ids[i]].pos = vec_add(new_point, prev_pos)

            prev_pos = bones[family.bone_ids[i]].pos

        end_bone = bones[family.bone_ids[-1]].pos
        tip_pos = end_bone
        for i in range(len(family.bone_ids) - 1, -1, -1):
            if i == len(family.bone_ids) - 1:
                continue
            dir = vec_sub(tip_pos, bones[family.bone_ids[i]].pos)
            tip_pos = bones[family.bone_ids[i]].pos
            ik_rots[family.bone_ids[i]] = math.atan2(dir.y, dir.x)

    return ik_rots


def interpolate_keyframes(
    element, field, default, keyframes, frame, bone_id, blend_frames
):
    prev_kf = {}
    next_kf = {}

    for kf in keyframes:
        if kf.frame < frame and kf.bone_id == bone_id and kf._element == element:
            prev_kf = kf

    for kf in keyframes:
        if kf.frame >= frame and kf.bone_id == bone_id and kf._element == element:
            next_kf = kf
            break

    if prev_kf == {}:
        prev_kf = next_kf
    elif next_kf == {}:
        next_kf = prev_kf

    if prev_kf == {} and next_kf == {}:
        return interpolate(frame, blend_frames, field, default)

    total_frames = next_kf.frame - prev_kf.frame
    current_frame = frame - prev_kf.frame

    result = interpolate(current_frame, total_frames, prev_kf.value, next_kf.value)
    blend = interpolate(current_frame, blend_frames, field, result)

    return blend


def interpolate(current, max, start_val, end_val):
    if current > max or max == 0:
        return end_val
    interp = current / max
    end = end_val - start_val
    return start_val + (end * interp)


def format_frame(frame, animation: Animation, reverse, loop):
    last_kf = len(animation.keyframes) - 1
    last_frame = animation.keyframes[last_kf].frame

    if loop:
        frame %= last_frame + 1

    if reverse:
        frame = last_frame - frame

    return int(frame)


def time_frame(time, animation, reverse, loop):
    frametime = 1 / animation.fps
    frame = time / frametime

    frame = format_frame(frame, animation, reverse, loop)

    return int(frame)
