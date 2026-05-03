import math
import copy
import zipfile
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Vec2:
    x: float = 0
    y: float = 0

    def clone(self, other):
        self.x = other.x
        self.y = other.y

    def __sub__(self, other):
        return Vec2(self.x - other.x, self.y - other.y)

    def __add__(self, other):
        return Vec2(self.x + other.x, self.y + other.y)

    def __mul__(self, other):
        if isinstance(other, float):
            return Vec2(self.x * other, self.y * other)
        return Vec2(self.x * other.x, self.y * other.y)

    def __isub__(self, other):
        return self.__sub__(other)

    def __iadd__(self, other):
        return self.__add__(other)

    def __imul__(self, other):
        return self.__mul__(other)


@dataclass
class Vertex:
    pos: Vec2
    uv: Vec2
    init_pos: Vec2


@dataclass
class BoneBindVert:
    id: int
    weight: float


@dataclass
class BoneBind:
    bone_id: int
    is_path: bool
    verts: list[BoneBindVert]


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
    vertices: Optional[list[Vertex]]
    indices: Optional[list[int]]
    binds: Optional[list[BoneBind]]
    ik_bone_ids: Optional[list[int]]
    ik_mode: Optional[str]
    ik_constraint: Optional[str]
    ik_family_id: Optional[int]
    ik_target_id: Optional[int]

    init_rot: float
    init_scale: Vec2
    init_pos: Vec2
    init_ik_constraint: Optional[str]
    zindex: Optional[int] = 0

    has_physics: Optional[bool] = False
    phys_global_pos: Optional[Vec2] = field(default_factory=Vec2)
    phys_pos_damping: Optional[float] = 0
    phys_pos_ratio: Optional[float] = 0
    phys_global_rot: Optional[float] = 0
    phys_global_orbit: Optional[float] = 0
    phys_global_orbit_diff: Optional[float] = 0
    phys_global_orbit_vel: Optional[float] = 0
    phys_rot_damping: Optional[float] = 0
    phys_sway: Optional[float] = 0
    phys_rot_bounce: Optional[float] = 0
    phys_global_scale: Optional[Vec2] = field(default_factory=Vec2)
    phys_scale_damping: Optional[float] = 0
    phys_scale_ratio: Optional[float] = 0


@dataclass
class Keyframe:
    frame: int
    bone_id: int
    element: str
    value: float
    value_str: Optional[str]
    start_handle: Vec2
    end_handle: Vec2
    next_kf: Optional[int] = -1


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
    constructed_bones: Optional[list[Bone]]
    ik_root_ids: list[int]
    animations: Optional[list[Animation]]
    atlases: list[Atlas]
    styles: list[Style]


def animate(
    armature: Armature, animations: [Animation], frames: [int], smooth_frames: [int]
):
    resetMap = {}
    sf = smooth_frames
    for a in range(len(animations)):
        keyframes = animations[a].keyframes
        for k in range(len(keyframes)):
            if keyframes[k].frame > frames[a]:
                continue

            kf = keyframes[k]

            if kf.next_kf == -1:
                kf.next_kf = k
            nextKf = animations[a].keyframes[kf.next_kf]

            # this is a redundant keyframe if the next one is also before this frame
            if nextKf.frame < frames[a] and kf.next_kf != k:
                continue

            bone = armature.bones[kf.bone_id]

            c1 = kf.element[0]
            c2 = kf.element[len(kf.element) - 1]
            intkf = interpolate_keyframes
            if c1 == "P" and c2 == "X":
                bone.pos.x = intkf(bone.pos.x, kf, nextKf, frames[a], sf[a])
            if c1 == "P" and c2 == "Y":
                bone.pos.y = intkf(bone.pos.y, kf, nextKf, frames[a], sf[a])
            if c1 == "R" and c2 == "n":
                bone.rot = intkf(bone.rot, kf, nextKf, frames[a], sf[a])
            if c1 == "S" and c2 == "X":
                bone.scale.x = intkf(bone.scale.x, kf, nextKf, frames[a], sf[a])
            if c1 == "S" and c2 == "Y":
                bone.scale.y = intkf(bone.scale.y, kf, nextKf, frames[a], sf[a])
            if c1 == "H" and c2 == "n":
                bone.hidden = kf.value == 1

            kf = keyframes[k]
            if not resetMap.get(kf.bone_id):
                resetMap[kf.bone_id] = []
            if not resetMap.get(kf.bone_id) or kf.element not in resetMap[kf.bone_id]:
                resetMap[kf.bone_id].append(kf.element)

    z = Vec2(0, 0)
    for bone in armature.bones:
        reset = []
        if resetMap.get(kf.bone_id):
            reset = resetMap[kf.bone_id]
        if "PositionX" not in reset:
            interpolate(frames[0], sf[0], bone.pos.x, bone.init_pos.x, z, z)
        if "PositionY" not in reset:
            interpolate(frames[0], sf[0], bone.pos.y, bone.init_pos.y, z, z)
        if "Rotation" not in reset:
            interpolate(frames[0], sf[0], bone.rot, bone.init_rot, z, z)
        if "ScaleX" not in reset:
            interpolate(frames[0], sf[0], bone.init_scale.x, bone.init_scale.x, z, z)
        if "ScaleY" not in reset:
            interpolate(frames[0], sf[0], bone.init_scale.y, bone.init_scale.y, z, z)

    return armature.bones


def rotate(point: Vec2, rot: float):
    return Vec2(
        point.x * math.cos(rot) - point.y * math.sin(rot),
        point.x * math.sin(rot) + point.y * math.cos(rot),
    )


# Call this before running inheritance.
def reset_inheritance(bones, og_bones):
    for b in range(len(bones)):
        bones[b].pos.x = og_bones[b].pos.x
        bones[b].pos.y = og_bones[b].pos.y
        bones[b].rot = og_bones[b].rot
        bones[b].scale.x = og_bones[b].scale.x
        bones[b].scale.y = og_bones[b].scale.y

    return bones


def inheritance(bones, ik_rots, src_bones):
    for b in range(len(bones)):
        bone = bones[b]

        if bone.parent_id != -1:
            # inherit parent
            parent = bones[bone.parent_id]

            orbit_rot = parent.rot
            # apply orbital difference, if sway is active
            if len(src_bones) > 0 and bone.phys_sway > 0:
                orbit_rot -= src_bones[b].phys_global_orbit_diff

            bone.rot += orbit_rot
            bone.scale *= parent.scale
            bone.pos *= parent.scale

            bone.pos = rotate(bone.pos, orbit_rot)

            bone.pos += parent.pos

        if bone.id in ik_rots:
            bone.rot = ik_rots[bone.id]

        # apply physics, if armature_bones is provided
        if len(src_bones) > 0:
            if bone.phys_rot_damping > 0:
                bone.rot = src_bones[b].phys_global_rot
            if bone.phys_pos_damping > 0:
                bone.pos.clone(src_bones[b].phys_global_pos)
            if bone.phys_scale_damping > 0:
                bone.scale = src_bones[b].phys_global_scale

    return bones


def magnitude(vec):
    return math.sqrt(vec.x * vec.x + vec.y * vec.y)


def normalize(vec):
    mag = magnitude(vec)
    if mag == 0:
        return Vec2(0, 0)
    return Vec2(vec.x / mag, vec.y / mag)


def shortest_angle_delta(fro, to):
    pi = 3.141592653589793
    tau = pi * 2.0
    delta = to - fro
    while delta > pi:
        delta -= tau
    while delta < -pi:
        delta += tau
    return delta


# simulate physics on the armature, then apply it to constructed bones
def simulate_physics(armature_bones, constructed_bones):
    for b in range(len(armature_bones)):
        s = Vec2(0.3, 0.3)
        e = Vec2(0.6, 0.6)
        arm_bone = armature_bones[b]
        const_bone = constructed_bones[b]
        prev_pos = Vec2(arm_bone.phys_global_pos.x, arm_bone.phys_global_pos.y)

        # interpolate position
        if arm_bone.phys_pos_damping > 0.0 or arm_bone.phys_sway > 0.0:
            phys_pos = arm_bone.phys_global_pos
            damping = Vec2(arm_bone.phys_pos_damping, arm_bone.phys_pos_damping)

            # ratio
            if arm_bone.phys_pos_ratio < 0.0:
                damping.y *= 1.0 - math.abs(arm_bone.phys_pos_ratio)
            elif arm_bone.phys_pos_ratio > 0.0:
                damping.x *= 1.0 - arm_bone.phys_pos_ratio

            phys_pos = arm_bone.phys_global_pos = Vec2(
                interpolate(2.0, damping.x, phys_pos.x, const_bone.pos.x, s, e),
                interpolate(2.0, damping.y, phys_pos.y, const_bone.pos.y, s, e),
            )

        # interpolate scale
        if arm_bone.phys_scale_damping > 0.0:
            phys_scale = arm_bone.phys_global_scale
            damping = Vec2(arm_bone.phys_scale_damping, arm_bone.phys_scale_damping)

            # ratio
            if arm_bone.phys_scale_ratio < 0:
                damping.y *= 1.0 - math.abs(arm_bone.phys_scale_ratio)
            elif arm_bone.phys_scale_ratio > 0.0:
                damping.x *= 1.0 - arm_bone.phys_scale_ratio

            phys_scale.x = interpolate(
                2.0, damping.x, phys_scale.x, const_bone.scale.x, s, e
            )
            phys_scale.y = interpolate(
                2.0, damping.y, phys_scale.y, const_bone.scale.y, s, e
            )

        # interpolate rotation
        if arm_bone.phys_rot_damping > 0.0:
            rot = shortest_angle_delta(arm_bone.phys_global_rot, const_bone.rot)
            arm_bone.phys_global_rot += rot / arm_bone.phys_rot_damping

        # interpolate parent orbit (sway, bounce, etc)
        parent = None
        for bone in constructed_bones:
            if bone.id == const_bone.parent_id:
                parent = bone
                break
        if arm_bone.phys_sway > 0.0 and parent is not None:
            # interpolate to the angle difference between bone and parent
            diff = normalize(const_bone.pos - parent.pos)
            diff_angle = math.atan2(diff.y, diff.x)
            rest_rot = shortest_angle_delta(arm_bone.phys_global_orbit, diff_angle)

            # apply bounce
            if arm_bone.phys_rot_bounce > 0.0 and arm_bone.phys_rot_bounce <= 1:
                bounce = arm_bone.phys_rot_bounce
                rest_rot += arm_bone.phys_global_orbit_vel / (2.0 - bounce)
                arm_bone.phys_global_orbit_vel = rest_rot
            arm_bone.phys_global_orbit += rest_rot / 10.0

            # swing orbit based on position momentum
            vel = normalize(arm_bone.phys_global_pos - prev_pos)
            angle = math.atan2(-vel.y, -vel.x)
            vel_rot = shortest_angle_delta(arm_bone.phys_global_orbit, angle)
            strength = magnitude(arm_bone.phys_global_pos - prev_pos) / 1000.0
            arm_bone.phys_global_orbit += vel_rot * strength * arm_bone.phys_sway

            # apply difference in final angle and orbit
            arm_bone.phys_global_orbit_diff = diff_angle - arm_bone.phys_global_orbit

    return (armature_bones, constructed_bones)


def construct(armature: Armature):
    if armature.constructed_bones is None:
        armature.constructed_bones = copy.deepcopy(armature.bones)
    else:
        armature.constructed_bones.sort(key=lambda prop: prop.id)

    armature.constructed_bones = reset_inheritance(
        armature.constructed_bones, armature.bones
    )
    armature.constructed_bones = inheritance(armature.constructed_bones, {}, {})
    ik_rots = inverse_kinematics(armature.constructed_bones, armature.ik_root_ids)

    armature.constructed_bones = reset_inheritance(
        armature.constructed_bones, armature.bones
    )
    armature.constructed_bones = inheritance(armature.constructed_bones, ik_rots, {})

    (armature.bones, armature.constructed_bones) = simulate_physics(
        armature.bones, armature.constructed_bones
    )

    armature.constructed_bones = reset_inheritance(
        armature.constructed_bones, armature.bones
    )
    armature.constructed_bones = inheritance(
        armature.constructed_bones, ik_rots, armature.bones
    )

    armature.constructed_bones = construct_verts(armature.constructed_bones)

    return armature.constructed_bones


def construct_verts(bones: list[Bone]):
    for b in range(len(bones)):
        if not bones[b].vertices:
            continue

        for v in range(len(bones[b].vertices)):
            bones[b].vertices[v].pos = bones[b].vertices[v].init_pos
            bones[b].vertices[v].pos = inherit_vert(bones[b].vertices[v].pos, bones[b])

        if not bones[b].binds:
            continue

        for bi in range(len(bones[b].binds)):
            boneId = bones[b].binds[bi].bone_id
            if boneId == -1:
                continue
            bindBone = {}
            for bone in bones:
                if bone.id == boneId:
                    bindBone = bone
                    break
            bind = bones[b].binds[bi]
            for v in range(len(bind.verts)):
                id = bind.verts[v].id

                if not bind.is_path:
                    vert: Vertex = bones[b].vertices[id]
                    weight: float = bind.verts[v].weight
                    endpos: Vec2 = inherit_vert(vert.init_pos, bindBone) - vert.pos
                    vert.pos += endpos * weight
                    continue

                binds = bones[b].binds
                prev = bi - 1 if bi > 0 else bi
                next = min(bi + 1, len(binds) - 1)
                prevBone = {}
                nextBone = {}
                for bone in bones:
                    if bone.id == binds[prev].bone_id:
                        prevBone = bone
                    elif bone.id == binds[next].bone_id:
                        nextBone = bone

                prevDir: Vec2 = bindBone.pos - prevBone.pos
                nextDir: Vec2 = nextBone.pos - bindBone.pos
                prevNormal: Vec2 = normalize(Vec2(-prevDir.y, prevDir.x))
                nextNormal: Vec2 = normalize(Vec2(-nextDir.y, nextDir.x))
                average: Vec2 = prevNormal + nextNormal
                normalAngle: float = math.atan2(average.y, average.x)

                vert: Vertex = bones[b].vertices[id]
                vert.pos = vert.init_pos + bindBone.pos
                rotated: Vec2 = rotate(vert.pos - bindBone.pos, normalAngle)
                vert.pos = bindBone.pos + (rotated * bind.verts[v].weight)
                bones[b].vertices[id] = vert

    return bones


def inherit_vert(pos: Vec2, bone: Bone):
    pos *= bone.scale
    pos = rotate(pos, bone.rot)
    pos += bone.pos
    return pos


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

        if family.ik_mode == "FABRIK":
            for i in range(10):
                fabrik(family, bones, root, target)
        else:
            arc_ik(family, bones, root, target)

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
        cw = family.ik_constraint == "Clockwise" and dir > 0
        ccw = family.ik_constraint == "CounterClockwise" and dir < 0
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


def arc_ik(family, bones: list[Bone], root: Vec2, target: Vec2):
    dist = [0.0]

    maxLength: Vec2 = magnitude(
        bones[family.ik_bone_ids[len(family.ik_bone_ids) - 1]].pos - root
    )
    currLength: float = 0.0
    for b in range(1, len(family.ik_bone_ids), 1):
        length: float = magnitude(
            bones[family.ik_bone_ids[b]].pos - bones[family.ik_bone_ids[b - 1]].pos
        )
        currLength += length
        dist.append(currLength / maxLength)

    base: Vec2 = target - root
    baseAngle: float = math.atan2(base.y, base.x)
    baseMag: float = min(magnitude(base), maxLength)
    peak: float = maxLength / baseMag
    valley: float = baseMag / maxLength
    for b in range(1, len(family.ik_bone_ids), 1):
        bones[family.ik_bone_ids[b]].pos = Vec2(
            bones[family.ik_bone_ids[b]].pos.x * valley,
            root.y + (1.0 - peak) * math.sin(dist[b] * 3.14) * baseMag,
        )

        rotated: float = rotate(bones[family.ik_bone_ids[b]].pos - root, baseAngle)
        bones[family.ik_bone_ids[b]].pos = rotated + root


# Flips bone's rotation if either axis of provided scale is negative.
# Returns new bone rotations
def check_bone_flip(bone_rot: float, scale: Vec2):
    either = scale.x < 0 or scale.y < 0
    both = scale.x < 0 and scale.y < 0
    if either and not both:
        bone_rot = -bone_rot
    return bone_rot


def get_bone_texture(bone_tex: str, styles: [Style]):
    for style in styles:
        for tex in style.textures:
            if tex.name == bone_tex:
                return tex
    return False


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


def interpolate_keyframes(field, prev_kf, next_kf, frame, smooth_frame):
    totalFrames = next_kf.frame - prev_kf.frame
    currentFrame = frame - prev_kf.frame
    result = interpolate(
        currentFrame,
        totalFrames,
        prev_kf.value,
        next_kf.value,
        next_kf.start_handle,
        next_kf.end_handle,
    )
    return interpolate(
        currentFrame, smooth_frame, field, result, Vec2(0, 0), Vec2(0, 0)
    )


def interpolate(
    current,
    max,
    start_val,
    end_val,
    start_handle,
    end_handle,
):
    # snapping behavior for None transition preset
    if start_handle.y == 999.0 and end_handle.y == 999:
        return start_val
    if max == 0 or current >= max:
        return end_val

    # solve for time (x axis) with Newton-Raphson
    initial = current / max
    t = initial
    for _ in range(5):
        x = cubic_bezier(t, start_handle.x, end_handle.x)
        dx = cubic_bezier_derivative(t, start_handle.x, end_handle.x)
        if abs(dx) < 1e-5:
            break
        t -= (x - initial) / dx
        if t > 1:
            t = 1
        elif t < 0:
            t = 0

    progress = cubic_bezier(t, start_handle.y, end_handle.y)
    return start_val + (end_val - start_val) * progress


def cubic_bezier(t, p1, p2):
    u = 1.0 - t
    return 3.0 * u * u * t * p1 + 3.0 * u * t * t * p2 + t * t * t


def cubic_bezier_derivative(t, p1, p2):
    u = 1.0 - t
    return 3.0 * u * u * p1 + 6.0 * u * t * (p2 - p1) + 3.0 * t * t * (1.0 - p2)


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
