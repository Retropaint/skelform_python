import zipfile
import json
import sys
from typing import List
from types import SimpleNamespace
import math

sys.path.append("../../skelform_python")

import skelform_python


def new_bone(id, x, y):
    return SimpleNamespace(id=id, pos=SimpleNamespace(x=x, y=y))


def setup_armature():
    armature = SimpleNamespace(bones=[], ik_families=[])

    armature.bones.append(new_bone(0, 0, 150))
    armature.bones.append(new_bone(1, 0, 0))
    armature.bones.append(new_bone(2, 50, 0))
    armature.bones.append(new_bone(3, 100, 0))

    armature.ik_families.append(
        SimpleNamespace(target_id=0, constraint="Clockwise", bone_ids=[1, 2, 3])
    )

    return armature


def forward_reaching(bones, ik_families):
    for family in ik_families:
        if family.target_id == -1:
            continue
        next_pos = bones[family.target_id].pos
        next_length = 0
        for i in range(len(family.bone_ids) - 1, -1, -1):
            length = skelform_python.Vec2(0, 0)
            if i != len(family.bone_ids) - 1:
                length = skelform_python.normalize(
                    skelform_python.vec_sub(next_pos, bones[family.bone_ids[i]].pos)
                )
                length.x *= next_length
                length.y *= next_length

            if i != 0:
                next_bone = bones[family.bone_ids[i - 1]]
                next_length = skelform_python.magnitude(
                    skelform_python.vec_sub(
                        bones[family.bone_ids[i]].pos, next_bone.pos
                    )
                )

            bones[family.bone_ids[i]].pos = skelform_python.vec_sub(next_pos, length)
            next_pos = bones[family.bone_ids[i]].pos
            print(f"{next_pos.x:.2f}", f"{next_pos.y:.2f}")


def backward_reaching(bones, ik_families, root):
    for family in ik_families:
        base_line = skelform_python.normalize(
            skelform_python.vec_sub(bones[family.target_id].pos, root)
        )
        base_angle = math.atan2(base_line.y, base_line.x)
        if family.target_id == -1:
            continue
        next_pos = root
        next_length = 0
        for i in range(len(family.bone_ids)):
            length = skelform_python.Vec2(0, 0)
            if i != 0:
                length = skelform_python.normalize(
                    skelform_python.vec_sub(next_pos, bones[family.bone_ids[i]].pos)
                )
                length.x *= next_length
                length.y *= next_length

            if i != len(family.bone_ids) - 1:
                next_bone = bones[family.bone_ids[i + 1]]
                next_length = skelform_python.magnitude(
                    skelform_python.vec_sub(
                        bones[family.bone_ids[i]].pos, next_bone.pos
                    )
                )

            bones[family.bone_ids[i]].pos = skelform_python.vec_sub(next_pos, length)

            if i != 0 and i != len(family.bone_ids) - 1 and family.constraint != "None":
                joint_line = skelform_python.normalize(
                    skelform_python.vec_sub(next_pos, bones[family.bone_ids[i]].pos)
                )
                joint_angle = math.atan2(joint_line.y, joint_line.x) - base_angle

                constraint_min = 0
                constraint_max = 0
                if family.constraint == "Clockwise":
                    constraint_min = -3.14
                else:
                    constraint_max = 3.14

                if joint_angle > constraint_max or joint_angle < constraint_min:
                    push_angle = -joint_angle * 2
                    new_point = skelform_python.rotate(
                        skelform_python.vec_sub(
                            bones[family.bone_ids[i]].pos, next_pos
                        ),
                        push_angle,
                    )
                    bones[family.bone_ids[i]].pos = skelform_python.vec_add(
                        new_point, next_pos
                    )

            next_pos = bones[family.bone_ids[i]].pos
            print(f"{next_pos.x:.2f}", f"{next_pos.y:.2f}")


def rotations(bones, ik_families):
    for family in ik_families:
        end_bone = bones[family.bone_ids[-1]].pos
        tip_pos = end_bone
        for i in range(len(family.bone_ids) - 1, -1, -1):
            dir = skelform_python.vec_sub(tip_pos, bones[family.bone_ids[i]].pos)
            tip_pos = bones[family.bone_ids[i]].pos
            angle = math.atan2(dir.y, dir.x)
            print(f"{angle:.2f}", f"{angle * 180 / 3.14:.2f}")


armature = setup_armature()

root = armature.bones[armature.ik_families[0].bone_ids[0]].pos

print()
print("forward reaching:")
forward_reaching(armature.bones, armature.ik_families)
print()

print("backward reaching:")
backward_reaching(armature.bones, armature.ik_families, root)
print()

print("rotations:")
rotations(armature.bones, armature.ik_families)
