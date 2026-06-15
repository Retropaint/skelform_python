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
class Visuals:
    tex: str
    # tint: Tint
    vertices: Optional[list[Vertex]]
    indices: Optional[list[int]]
    binds: Optional[list[BoneBind]]
    zindex: int

    init_tex: str
    init_zindex: Optional[int]
    # init_tint: Tint


@dataclass
class InverseKinematics:
    bone_ids: Optional[list[int]]
    mode: Optional[str]
    constraint: Optional[str]
    target_id: Optional[int]
    mimic_target: Optional[bool]

    init_mimic_target: Optional[bool]
    init_constraint: Optional[str]


@dataclass
class Physics:
    global_pos: Optional[Vec2] = field(default_factory=Vec2)
    pos_damping: Optional[float] = 0
    pos_ratio: Optional[float] = 0
    global_rot: Optional[float] = 0
    global_orbit: Optional[float] = 0
    global_orbit_diff: Optional[float] = 0
    global_orbit_vel: Optional[float] = 0
    rot_damping: Optional[float] = 0
    sway: Optional[float] = 0
    rot_bounce: Optional[float] = 0
    global_scale: Optional[Vec2] = field(default_factory=Vec2)
    scale_damping: Optional[float] = 0
    scale_ratio: Optional[float] = 0


@dataclass
class Bone:
    name: str
    id: int
    parent_id: int
    rot: float
    scale: Vec2
    pos: Vec2
    hidden: Optional[bool]

    ik_family_id: int
    visuals_id: int
    physics_id: int

    init_rot: float
    init_scale: Vec2
    init_pos: Vec2
    init_hidden: Optional[bool]


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
    animations: Optional[list[Animation]]
    atlases: list[Atlas]
    styles: list[Style]
    visuals: list[Visuals]
    inverse_kinematics: list[InverseKinematics]
    physics: list[Physics]


def animate(
    armature: Armature, animations: [Animation], frames: [int], smooth_frames: [int]
):
    resetMap = {}
    sf = smooth_frames
    for a in range(len(animations)):
        keyframes = animations[a].keyframes
        for k in range(len(keyframes)):
            kf = keyframes[k]

            if not resetMap.get(kf.bone_id):
                resetMap[kf.bone_id] = []
            if kf.element not in resetMap[kf.bone_id]:
                resetMap[kf.bone_id].append(kf.element)

            if keyframes[k].frame > frames[a]:
                continue

            kf = keyframes[k]

            if kf.next_kf == -1:
                kf.next_kf = k
            nextKf = animations[a].keyframes[kf.next_kf]

            # this is a redundant keyframe if the next one is also before this frame
            if nextKf.frame < frames[a] and kf.next_kf != k:
                continue

            bone: Bone = armature.bones[kf.bone_id]

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

    z = Vec2(0, 0)
    for bone in armature.bones:
        reset = []
        if resetMap.get(bone.id):
            reset = resetMap[bone.id]

        if "PositionX" not in reset:
            bone.pos.x = interpolate(
                frames[0], sf[0], bone.pos.x, bone.init_pos.x, z, z
            )
        if "PositionY" not in reset:
            bone.pos.y = interpolate(
                frames[0], sf[0], bone.pos.y, bone.init_pos.y, z, z
            )
        if "Rotation" not in reset:
            bone.rot = interpolate(frames[0], sf[0], bone.rot, bone.init_rot, z, z)
        if "ScaleX" not in reset:
            bone.scale.x = interpolate(
                frames[0], sf[0], bone.scale.x, bone.init_scale.x, z, z
            )
        if "ScaleY" not in reset:
            bone.scale.y = interpolate(
                frames[0], sf[0], bone.scale.y, bone.init_scale.y, z, z
            )

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


def inheritance(bones, ik_rots, physics):
    for b in range(len(bones)):
        bone = bones[b]

        if bone.parent_id != -1:
            # inherit parent
            parent = bones[bone.parent_id]

            orbit_rot = parent.rot
            # apply orbital difference, if sway is active
            if bone.physics_id != -1 and len(physics) > 0:
                phys = physics[bone.physics_id]
                if phys.sway > 0:
                    orbit_rot -= phys.global_orbit_diff

            bone.rot += orbit_rot
            bone.scale *= parent.scale
            bone.pos *= parent.scale

            bone.pos = rotate(bone.pos, orbit_rot)

            bone.pos += parent.pos

        if bone.id in ik_rots:
            bone.rot = ik_rots[bone.id]

        # apply physics, if armature_bones is provided
        if bone.physics_id != -1 and len(physics) > 0:
            phys = physics[bone.physics_id]
            if phys.rot_damping > 0:
                bone.rot = phys.global_rot
            if phys.pos_damping > 0:
                bone.pos.clone(phys.global_pos)
            if phys.scale_damping > 0:
                bone.scale = phys.global_scale

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
def simulate_physics(constructed_bones: list[Bone], physics: list[Physics]):
    for b in range(len(constructed_bones)):
        if constructed_bones[b].physics_id == -1:
            continue
        const_bone: Bone = constructed_bones[b]
        phys: Physics = physics[const_bone.physics_id]
        if not phys:
            continue
        s = Vec2(0.3, 0.3)
        e = Vec2(0.6, 0.6)
        prev_pos = Vec2(phys.global_pos.x, phys.global_pos.y)

        # interpolate position
        if phys.pos_damping > 0.0 or phys.sway > 0.0:
            damping = Vec2(phys.pos_damping, phys.pos_damping)

            # ratio
            if phys.pos_ratio < 0.0:
                damping.y *= 1.0 - math.abs(phys.pos_ratio)
            elif phys.pos_ratio > 0.0:
                damping.x *= 1.0 - phys.pos_ratio

            phys.global_pos = Vec2(
                interpolate(2.0, damping.x, phys.global_pos.x, const_bone.pos.x, s, e),
                interpolate(2.0, damping.y, phys.global_pos.y, const_bone.pos.y, s, e),
            )

        # interpolate scale
        if phys.scale_damping > 0.0:
            phys_scale = phys.global_scale
            damping = Vec2(phys.scale_damping, phys.scale_damping)

            # ratio
            if phys.scale_ratio < 0:
                damping.y *= 1.0 - math.abs(phys.scale_ratio)
            elif phys.scale_ratio > 0.0:
                damping.x *= 1.0 - phys.scale_ratio

            phys_scale.x = interpolate(
                2.0, damping.x, phys_scale.x, const_bone.scale.x, s, e
            )
            phys_scale.y = interpolate(
                2.0, damping.y, phys_scale.y, const_bone.scale.y, s, e
            )

        # interpolate rotation
        if phys.rot_damping > 0.0:
            rot = shortest_angle_delta(phys.global_rot, const_bone.rot)
            phys.global_rot += rot / phys.rot_damping

        # interpolate parent orbit (sway, bounce, etc)
        parent = None
        for bone in constructed_bones:
            if bone.id == const_bone.parent_id:
                parent = bone
                break
        if phys.sway > 0.0 and parent is not None:
            # interpolate to the angle difference between bone and parent
            diff = normalize(const_bone.pos - parent.pos)
            diff_angle = math.atan2(diff.y, diff.x)
            rest_rot = shortest_angle_delta(phys.global_orbit, diff_angle)

            # apply bounce
            if phys.rot_bounce > 0.0 and phys.rot_bounce <= 1:
                bounce = phys.rot_bounce
                rest_rot += phys.global_orbit_vel / (2.0 - bounce)
                phys.global_orbit_vel = rest_rot
            phys.global_orbit += rest_rot / 10.0

            # swing orbit based on position momentum
            vel = normalize(phys.global_pos - prev_pos)
            angle = math.atan2(-vel.y, -vel.x)
            vel_rot = shortest_angle_delta(phys.global_orbit, angle)
            strength = magnitude(phys.global_pos - prev_pos) / 1000.0
            phys.global_orbit += vel_rot * strength * phys.sway

            # apply difference in final angle and orbit
            phys.global_orbit_diff = diff_angle - phys.global_orbit

    return (constructed_bones, physics)


def construct(armature: Armature):
    if armature.constructed_bones is None:
        armature.constructed_bones = copy.deepcopy(armature.bones)
    else:
        armature.constructed_bones.sort(key=lambda prop: prop.id)

    armature.constructed_bones = reset_inheritance(
        armature.constructed_bones, armature.bones
    )
    armature.constructed_bones = inheritance(armature.constructed_bones, {}, [])
    ik_rots = inverse_kinematics(
        armature.constructed_bones, armature.inverse_kinematics
    )

    armature.constructed_bones = reset_inheritance(
        armature.constructed_bones, armature.bones
    )
    armature.constructed_bones = inheritance(armature.constructed_bones, ik_rots, [])

    (armature.constructed_bones, armature.physics) = simulate_physics(
        armature.constructed_bones, armature.physics
    )

    armature.constructed_bones = reset_inheritance(
        armature.constructed_bones, armature.bones
    )
    armature.constructed_bones = inheritance(
        armature.constructed_bones, ik_rots, armature.physics
    )

    armature.constructed_bones = construct_verts(
        armature.constructed_bones, armature.visuals
    )

    return armature.constructed_bones


def construct_verts(bones: list[Bone], visuals: list[Visuals]):
    for b in range(len(bones)):
        if bones[b].visuals_id == -1:
            continue
        visual = visuals[bones[b].visuals_id]

        if not visual.vertices:
            continue

        for v in range(len(visual.vertices)):
            visual.vertices[v].pos = visual.vertices[v].init_pos
            visual.vertices[v].pos = inherit_vert(visual.vertices[v].pos, bones[b])

        if not visual.binds:
            continue

        for bi in range(len(visual.binds)):
            boneId = visual.binds[bi].bone_id
            if boneId == -1:
                continue
            bindBone: Bone
            for bone in bones:
                if bone.id == boneId:
                    bindBone = bone
                    break
            bind = visual.binds[bi]
            for v in range(len(bind.verts)):
                id = bind.verts[v].id

                if not bind.is_path:
                    vert: Vertex = visual.vertices[id]
                    weight: float = bind.verts[v].weight
                    endpos: Vec2 = inherit_vert(vert.init_pos, bindBone) - vert.pos
                    vert.pos += endpos * weight
                    continue

                binds = visual.binds
                prev = bi - 1 if bi > 0 else bi
                next = min(bi + 1, len(binds) - 1)
                prevBone: Bone
                nextBone: Bone
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

                vert = visual.vertices[id]
                vert.pos = vert.init_pos + bindBone.pos
                rotated: Vec2 = rotate(vert.pos - bindBone.pos, normalAngle)
                vert.pos = bindBone.pos + (rotated * bind.verts[v].weight)
                visual.vertices[id] = vert

    return bones


def inherit_vert(pos: Vec2, bone: Bone):
    pos *= bone.scale
    pos = rotate(pos, bone.rot)
    pos += bone.pos
    return pos


def inverse_kinematics(bones: list[Bone], inverse_kinematics: list[InverseKinematics]):
    ik_rots = {}

    for family in inverse_kinematics:
        if not family.target_id or family.target_id == -1 or not family.bone_ids:
            continue

        root = copy.deepcopy(bones[family.bone_ids[0]].pos)
        target = copy.deepcopy(bones[family.target_id].pos)

        if family.mode == "FABRIK":
            for i in range(10):
                fabrik(family, bones, root, target)
        else:
            arc_ik(family, bones, root, target)

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


def fabrik(family: InverseKinematics, bones: list[Bone], root: Vec2, target: Vec2):
    if not family.target_id or not family.bone_ids:
        return

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


def arc_ik(family: InverseKinematics, bones: list[Bone], root: Vec2, target: Vec2):
    dist = [0.0]

    maxLength: Vec2 = magnitude(
        bones[family.bone_ids[len(family.bone_ids) - 1]].pos - root
    )
    currLength: float = 0.0
    for b in range(1, len(family.bone_ids), 1):
        length: float = magnitude(
            bones[family.bone_ids[b]].pos - bones[family.bone_ids[b - 1]].pos
        )
        currLength += length
        dist.append(currLength / maxLength)

    base: Vec2 = target - root
    baseAngle: float = math.atan2(base.y, base.x)
    baseMag: float = min(magnitude(base), maxLength)
    peak: float = maxLength / baseMag
    valley: float = baseMag / maxLength
    for b in range(1, len(family.bone_ids), 1):
        bones[family.bone_ids[b]].pos = Vec2(
            bones[family.bone_ids[b]].pos.x * valley,
            root.y + (1.0 - peak) * math.sin(dist[b] * 3.14) * baseMag,
        )

        rotated: float = rotate(bones[family.bone_ids[b]].pos - root, baseAngle)
        bones[family.bone_ids[b]].pos = rotated + root


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
