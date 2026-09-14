"""A parametric 6-DOF robot arm: 11 parts, 15 instances, 1 assembly.

    from robot_arm.params import ArmParams
    from robot_arm.assembly import build_assembly
    from robot_arm.verify import run

    assert run().ok
    arm = build_assembly(ArmParams(upper_len=420.0))
"""

from .params import ArmParams, DEFAULT

__all__ = ["ArmParams", "DEFAULT", "params", "parts", "assembly", "verify"]
