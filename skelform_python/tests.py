import zipfile
import json
import sys
from typing import List
from types import SimpleNamespace

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
        SimpleNamespace(target_id=0, constraint="None", bone_ids=[1, 2, 3])
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


armature = setup_armature()

print()
print("forward reaching:")
forward_reaching(armature.bones, armature.ik_families)
print()
