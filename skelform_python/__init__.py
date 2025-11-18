import math
import copy
import zipfile
from dataclasses import dataclass
from typing import Optional


@dataclass
class Vec2:
    x: float
    y: float

    def __sub__(self, other):
        return Vec2(self.x - other.x, self.y - other.y)

    def __add__(self, other):
        return Vec2(self.x + other.x, self.y + other.y)

    def __mul__(self, other):
        return Vec2(self.x * other.x, self.y * other.y)

    def __isub__(self, other):
        return self.__sub__(other)

    def __iadd__(self, other):
        return self.__add__(other)

    def __imul__(self, other):
        return self.__mul__(other)


@dataclass
class Bone:
    name: str
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
    element: str
    value: float


@dataclass
class Animation:
    name: str
    keyframes: list[Keyframe]
    fps: int


@dataclass
class Texture:
    name: str
    offset: Vec2
    size: Vec2


@dataclass
class Style:
    name: str
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
            bone.scale *= parent.scale
            bone.pos *= parent.scale

            bone.pos = rotate(bone.pos, parent.rot)

            bone.pos += parent.pos

        if bone.id in ik_rots:
            bone.rot = ik_rots[bone.id]

    return bones


def magnitude(vec):
    return math.sqrt(vec.x * vec.x + vec.y * vec.y)


def normalize(vec):
    mag = magnitude(vec)
    if mag == 0:
        return Vec2(0, 0)
    return Vec2(vec.x / mag, vec.y / mag)


def inverse_kinematics(bones, ik_families):
    ik_rots = {}

    for family in ik_families:
        if family.target_id == -1:
            continue

        root = copy.deepcopy(bones[family.bone_ids[0]].pos)
        target = copy.deepcopy(bones[family.target_id].pos)

        for i in range(10):
            fabrik(family, bones, root, target)

        # setting bone rotations
        end_bone = bones[family.bone_ids[-1]].pos
        tip_pos = end_bone
        for i in range(len(family.bone_ids) - 1, -1, -1):
            dir = tip_pos - bones[family.bone_ids[i]].pos
            tip_pos = bones[family.bone_ids[i]].pos
            bones[family.bone_ids[i]].rot = math.atan2(dir.y, dir.x)

        # applying constraint
        joint_dir = normalize(bones[family.bone_ids[1]].pos - root)
        base_dir = normalize(target - root)
        dir = joint_dir.x * base_dir.y - base_dir.x * joint_dir.y
        base_angle = math.atan2(base_dir.y, base_dir.x)
        cw = family.constraint == "Clockwise" and dir > 0
        ccw = family.constraint == "CounterClockwise" and dir < 0
        if ccw or cw:
            for i in family.bone_ids:
                bones[i].rot = -bones[i].rot + base_angle * 2

        # saving rotations to map
        for i in range(len(family.bone_ids) - 1):
            ik_rots[family.bone_ids[i]] = bones[family.bone_ids[i]].rot

    return ik_rots


def fabrik(family, bones, root, target):
    # forward reaching
    next_pos = bones[family.target_id].pos
    next_length = 0
    for i in range(len(family.bone_ids) - 1, -1, -1):
        length = Vec2(0, 0)
        if i != len(family.bone_ids) - 1:
            length = normalize(next_pos - bones[family.bone_ids[i]].pos)
            length.x *= next_length
            length.y *= next_length

        if i != 0:
            next_bone = bones[family.bone_ids[i - 1]]
            bone_pos = bones[family.bone_ids[i]].pos
            next_length = magnitude(bone_pos - next_bone.pos)

        bones[family.bone_ids[i]].pos = next_pos - length
        next_pos = bones[family.bone_ids[i]].pos

    # backward reaching
    prev_pos = root
    prev_length = 0
    for i in range(len(family.bone_ids)):
        length = Vec2(0, 0)
        if i != 0:
            length = normalize(prev_pos - bones[family.bone_ids[i]].pos)
            length.x *= prev_length
            length.y *= prev_length

        if i != len(family.bone_ids) - 1:
            prev_bone = bones[family.bone_ids[i + 1]]
            bone_pos = bones[family.bone_ids[i]].pos
            prev_length = magnitude(bone_pos - prev_bone.pos)

        bones[family.bone_ids[i]].pos = prev_pos - length
        prev_pos = bones[family.bone_ids[i]].pos


def interpolate_keyframes(
    element, field, default, keyframes, frame, bone_id, blend_frames
):
    prev_kf = {}
    next_kf = {}

    for kf in keyframes:
        if kf.frame < frame and kf.bone_id == bone_id and kf.element == element:
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
