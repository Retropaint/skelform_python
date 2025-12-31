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
    tex: Optional[str]
    rot: float
    scale: Vec2
    pos: Vec2
    ik_bone_ids: Optional[list[int]]
    ik_mode: Optional[int]
    ik_constraint_str: Optional[str]
    ik_constraint: Optional[int]
    ik_family_id: Optional[int]
    ik_target_id: Optional[int]
    init_rot: float
    init_scale: Vec2
    init_pos: Vec2
    init_ik_constraint: Optional[int]
    zindex: Optional[int] = 0


@dataclass
class Keyframe:
    frame: int
    bone_id: int
    element: int
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
    atlas_idx: int


@dataclass
class Style:
    name: str
    textures: list[Texture]


@dataclass
class Atlas:
    filename: str
    size: Vec2


@dataclass
class Armature:
    bones: list[Bone]
    ik_root_ids: list[int]
    animations: Optional[list[Animation]]
    atlases: list[Atlas]
    styles: list[Style]


def animate(
    armature: Armature, animations: [Animation], frames: [int], blend_frames: [int]
):
    bones = []
    for a in range(len(animations)):
        kf = animations[a].keyframes
        bf = blend_frames[a]
        ikf = interpolate_keyframes

        for bone in armature.bones:
            bone = copy.deepcopy(bone)
            bones.append(bone)
            id = bone.id
            # yapf: disable
            bone.pos.x   = ikf(0, bone.pos.x,   bone.init_pos.x,   kf, frames[a], id, bf)
            bone.pos.y   = ikf(1, bone.pos.y,   bone.init_pos.y,   kf, frames[a], id, bf)
            bone.rot     = ikf(2, bone.rot,     bone.init_rot,     kf, frames[a], id, bf)
            bone.scale.x = ikf(3, bone.scale.x, bone.init_scale.x, kf, frames[a], id, bf)
            bone.scale.y = ikf(4, bone.scale.y, bone.init_scale.y, kf, frames[a], id, bf)

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


def construct(armature: Armature):
    inh_props = copy.deepcopy(armature.bones)

    inh_props = inheritance(inh_props, {})
    ik_rots = inverse_kinematics(inh_props, armature.ik_root_ids)

    final_bones = copy.deepcopy(armature.bones)
    final_bones = inheritance(final_bones, ik_rots)

    return final_bones


def inverse_kinematics(bones: list[Bone], ik_root_ids: list[int]):
    ik_rots = {}

    for root_id in ik_root_ids:
        family = bones[root_id]
        if (
            family.ik_target_id == -1
            or not family.ik_bone_ids
            or family.ik_target_id == -1
        ):
            continue

        root = copy.deepcopy(bones[family.ik_bone_ids[0]].pos)
        target = copy.deepcopy(bones[family.ik_target_id].pos)

        for i in range(10):
            fabrik(family, bones, root, target)

        # setting bone rotations
        end_bone = bones[family.ik_bone_ids[-1]].pos
        tip_pos = end_bone
        for i in range(len(family.ik_bone_ids) - 1, -1, -1):
            dir = tip_pos - bones[family.ik_bone_ids[i]].pos
            tip_pos = bones[family.ik_bone_ids[i]].pos
            bones[family.ik_bone_ids[i]].rot = math.atan2(dir.y, dir.x)

        # applying constraint
        joint_dir = normalize(bones[family.ik_bone_ids[1]].pos - root)
        base_dir = normalize(target - root)
        dir = joint_dir.x * base_dir.y - base_dir.x * joint_dir.y
        base_angle = math.atan2(base_dir.y, base_dir.x)
        cw = family.ik_constraint == 1 and dir > 0
        ccw = family.ik_constraint == 2 and dir < 0
        if ccw or cw:
            for i in family.ik_bone_ids:
                bones[i].rot = -bones[i].rot + base_angle * 2

        # saving rotations to map
        for i in range(len(family.ik_bone_ids) - 1):
            ik_rots[family.ik_bone_ids[i]] = bones[family.ik_bone_ids[i]].rot

    return ik_rots


def fabrik(family, bones, root, target):
    # forward reaching
    next_pos = bones[family.ik_target_id].pos
    next_length = 0
    for i in range(len(family.ik_bone_ids) - 1, -1, -1):
        length = Vec2(0, 0)
        if i != len(family.ik_bone_ids) - 1:
            length = normalize(next_pos - bones[family.ik_bone_ids[i]].pos)
            length.x *= next_length
            length.y *= next_length

        if i != 0:
            next_bone = bones[family.ik_bone_ids[i - 1]]
            bone_pos = bones[family.ik_bone_ids[i]].pos
            next_length = magnitude(bone_pos - next_bone.pos)

        bones[family.ik_bone_ids[i]].pos = next_pos - length
        next_pos = bones[family.ik_bone_ids[i]].pos

    # backward reaching
    prev_pos = root
    prev_length = 0
    for i in range(len(family.ik_bone_ids)):
        length = Vec2(0, 0)
        if i != 0:
            length = normalize(prev_pos - bones[family.ik_bone_ids[i]].pos)
            length.x *= prev_length
            length.y *= prev_length

        if i != len(family.ik_bone_ids) - 1:
            prev_bone = bones[family.ik_bone_ids[i + 1]]
            bone_pos = bones[family.ik_bone_ids[i]].pos
            prev_length = magnitude(bone_pos - prev_bone.pos)

        bones[family.ik_bone_ids[i]].pos = prev_pos - length
        prev_pos = bones[family.ik_bone_ids[i]].pos


# Flips bone's rotation if either axis of provided scale is negative.
# Returns new bone rotations
def check_bone_flip(bone_rot: float, scale: Vec2):
    either = scale.x < 0 or scale.y < 0
    both = scale.x < 0 and scale.y < 0
    if either and not both:
        bone_rot = -bone_rot
    return bone_rot


# Returns a (bone.id, Texture) map of textures to draw bones with.
def setup_bone_textures(bones: [Bone], styles: [Style]):
    final_textures = {}
    for bone in bones:
        for style in styles:
            if bone.tex is None:
                continue
            final_tex = {}
            has_final = False
            for tex in style.textures:
                if tex.name == bone.tex:
                    final_tex = tex
                    has_final = True
                    break
            if has_final:
                final_textures[bone.id] = final_tex

    return final_textures


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
