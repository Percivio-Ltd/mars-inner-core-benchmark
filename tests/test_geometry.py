from __future__ import annotations

from scripts.shared import import_local_module

stacking = import_local_module("marsquake_geometry_test", "scripts/03_vespagram/stacking.py")
zero_padded_shifted_stack_index = stacking.zero_padded_shifted_stack_index
import numpy as np


def test_geometry_sign_example():
    roll = zero_padded_shifted_stack_index([31.0], 29.0, -7.0, 20.0)
    assert int(round(280)) == roll


def test_zero_shift_at_ref():
    assert zero_padded_shifted_stack_index([29.0], 29.0, -7.0, 20.0) == 0


def test_zero_slowness():
    assert zero_padded_shifted_stack_index([31.0], 29.0, 0.0, 20.0) == 0


def test_distance_vector_keeps_array_shape():
    distances = np.array([29.0, 29.5, 30.0, 31.0])
    rolls = zero_padded_shifted_stack_index(distances, 29.0, -7.0, 20.0)
    assert np.allclose(rolls, np.array([0, 70, 140, 280]))


def test_roll_direction_is_forward_for_negative_slowness_far_distance():
    distance = [31.0]
    assert zero_padded_shifted_stack_index(distance, 29.0, -7.0, 20.0) > 0
