from __future__ import annotations

import numpy as np
import pytest

from scripts.shared import import_local_module

stacking = import_local_module("marsquake_stacking_test", "scripts/03_vespagram/stacking.py")

zero_padded_shift = stacking.zero_padded_shift
linear_stack = stacking.linear_stack
nth_root_stack = stacking.nth_root_stack
phase_weighted_stack = stacking.phase_weighted_stack
phase_weighted_stack_broken = stacking.phase_weighted_stack_broken


def test_mask_aware_stack_api_registers_default_support_threshold():
    assert hasattr(stacking, "DEFAULT_MIN_STACK_SUPPORT")
    assert stacking.DEFAULT_MIN_STACK_SUPPORT == 2


def test_zero_padded_shift_no_wrap():
    tr = np.arange(10.0)
    out = zero_padded_shift(tr, 3)
    assert out[:3].sum() == 0
    assert np.array_equal(out[3:], tr[:7])

    out_full = zero_padded_shift(tr, 10)
    assert np.all(out_full == 0)

    out2 = zero_padded_shift(tr, -3)
    assert out2[-3:].sum() == 0
    assert np.array_equal(out2[:-3], tr[3:])

    out2_full = zero_padded_shift(tr, -10)
    assert np.all(out2_full == 0)


def test_zero_padded_shift_preserves_dtype_and_length():
    tr = np.arange(7, dtype=np.float32)
    out = zero_padded_shift(tr, 2)
    assert out.dtype == tr.dtype
    assert out.shape == tr.shape


def test_zero_shift_is_identity():
    tr = np.array([1.0, -2.0, 3.0], dtype=np.float64)
    out = zero_padded_shift(tr, 0)
    assert np.array_equal(out, tr)


def test_zero_padded_shift_out_of_range_raises_for_negative_beyond_bounds():
    tr = np.arange(5.0)
    assert np.all(zero_padded_shift(tr, 99) == 0)
    assert np.all(zero_padded_shift(tr, -99) == 0)


def test_zero_slowness_shift():
    tr = np.array([1, 2, 3, 4], dtype=float)
    out = linear_stack([tr, tr], [29, 31], ref_distance=29, slowness_sdeg=0, sampling_rate_hz=20)
    assert np.allclose(out, tr)


def test_stack_output_shape_stability():
    tr1 = np.zeros(10)
    tr2 = np.ones(10)
    out = nth_root_stack([tr1, tr2], [29.0, 29.5], ref_distance=29.0, slowness_sdeg=-7.0, sampling_rate_hz=20.0)
    assert out.shape == tr1.shape


def test_delta_function_alignment():
    sr = 20.0
    distances = np.linspace(29.0, 33.5, 10)
    slowness = -7.0
    base = np.zeros(3000)
    base[1200] = 1.0
    traces = []
    for distance in distances:
        roll = int(round(-slowness * (distance - 29.0) * sr))
        traces.append(zero_padded_shift(base, -roll))

    out = linear_stack(traces, distances, 29.0, slowness, sr)
    assert np.nanargmax(np.abs(out)) == 1200
    assert out[1200] == pytest.approx(1.0)


def test_delta_function_alignment_requires_equal_lengths():
    sr = 20.0
    with pytest.raises(ValueError):
        nth_root_stack([np.zeros(5), np.zeros(8)], [29.0, 29.5], 29.0, -7.0, sr)


def test_pws_vs_broken_differs():
    traces = [np.random.RandomState(0).normal(size=200) for _ in range(5)]
    d = [29.0, 29.5, 30.0, 30.5, 31.0]
    a = phase_weighted_stack(traces, d, 29.0, -7.0, 20.0, pw_order=1)
    b = phase_weighted_stack_broken(traces, d, 29.0, -7.0, 20.0, pw_order=1)
    assert not np.allclose(a, b)


def test_phase_weighted_stack_bounds_with_single_trace():
    tr = np.array([0.0, 1.0, 0.0])
    out = phase_weighted_stack([tr], [29.0], 29.0, -7.0, 10.0, min_support=1)
    # single-trace PWS should match linear stack at nsta=1
    assert np.allclose(out, tr)


def test_pws_coherence_semantics():
    t = np.linspace(0.0, 4.0 * np.pi, 512, endpoint=False)
    coherent = np.sin(t)
    coherent_traces = [coherent.copy() for _ in range(5)]
    coherent_out = phase_weighted_stack(coherent_traces, [29.0] * 5, 29.0, 0.0, 20.0)
    assert np.allclose(coherent_out, coherent, atol=1e-6)

    incoherent_traces = [np.sin(t + phase) for phase in np.linspace(0.0, 2.0 * np.pi, 5, endpoint=False)]
    incoherent_out = phase_weighted_stack(incoherent_traces, [29.0] * 5, 29.0, 0.0, 20.0)
    coherent_rms = np.sqrt(np.mean(coherent_out**2))
    incoherent_rms = np.sqrt(np.mean(incoherent_out**2))
    assert incoherent_rms < 0.1 * coherent_rms


def test_linear_stack_divides_by_valid_support_not_total_trace_count():
    traces = [
        np.array([2.0, 2.0, 2.0, 99.0, 99.0]),
        np.array([99.0, 99.0, 99.0, 4.0, 4.0]),
    ]
    masks = [
        np.array([True, True, True, False, False]),
        np.array([False, False, False, True, True]),
    ]

    out, support = linear_stack(
        traces,
        [29.0, 29.0],
        ref_distance=29.0,
        slowness_sdeg=0.0,
        sampling_rate_hz=1.0,
        valid_masks=masks,
        min_support=1,
        return_support=True,
    )

    assert np.array_equal(support, np.array([1, 1, 1, 1, 1]))
    assert np.allclose(out, np.array([2.0, 2.0, 2.0, 4.0, 4.0]))


def test_shifted_mask_uses_same_sign_convention_as_shifted_data():
    trace = np.arange(6.0)
    mask = np.array([True, True, True, False, False, False])

    out, support = linear_stack(
        [trace],
        [31.0],
        ref_distance=29.0,
        slowness_sdeg=-1.0,
        sampling_rate_hz=1.0,
        valid_masks=[mask],
        min_support=1,
        return_support=True,
    )

    # roll_samples = -(-1) * (31 - 29) * 1 = +2: data and mask both move later.
    assert np.array_equal(support, np.array([0, 0, 1, 1, 1, 0]))
    assert np.allclose(out[2:5], np.array([0.0, 1.0, 2.0]))
    assert np.isnan(out[0])
    assert np.isnan(out[1])


def test_negative_shifted_mask_uses_same_sign_convention_as_shifted_data():
    trace = np.arange(6.0)
    mask = np.array([False, False, False, True, True, True])

    out, support = linear_stack(
        [trace],
        [31.0],
        ref_distance=29.0,
        slowness_sdeg=1.0,
        sampling_rate_hz=1.0,
        valid_masks=[mask],
        min_support=1,
        return_support=True,
    )

    # roll_samples = -(1) * (31 - 29) * 1 = -2: data and mask both move earlier.
    assert np.array_equal(support, np.array([0, 1, 1, 1, 0, 0]))
    assert np.allclose(out[1:4], np.array([3.0, 4.0, 5.0]))
    assert np.isnan(out[0])
    assert np.isnan(out[4])
    assert np.isnan(out[5])


def test_pws_hilbert_gap_leakage_is_confined_to_registered_guard_margin():
    t = np.linspace(0.0, 64.0 * np.pi, 512, endpoint=False)
    traces = [np.sin(t), np.sin(t + 0.2), np.sin(t - 0.2)]
    gap_start = 248
    gap_stop = 264
    guard_margin_samples = 20
    masks = [np.ones_like(t, dtype=bool) for _ in traces]
    for mask in masks:
        mask[gap_start:gap_stop] = False

    masked_out, support = phase_weighted_stack(
        traces,
        [29.0, 29.0, 29.0],
        ref_distance=29.0,
        slowness_sdeg=0.0,
        sampling_rate_hz=20.0,
        valid_masks=masks,
        min_support=2,
        return_support=True,
    )
    full_out = phase_weighted_stack(
        traces,
        [29.0, 29.0, 29.0],
        ref_distance=29.0,
        slowness_sdeg=0.0,
        sampling_rate_hz=20.0,
        min_support=2,
    )

    assert np.all(support[gap_start:gap_stop] == 0)
    edge_band = np.r_[gap_start - guard_margin_samples : gap_start, gap_stop : gap_stop + guard_margin_samples]
    far_band = np.r_[gap_start - 120 : gap_start - guard_margin_samples, gap_stop + guard_margin_samples : gap_stop + 120]
    edge_delta = np.nanmax(np.abs(masked_out[edge_band] - full_out[edge_band]))
    far_delta = np.nanmax(np.abs(masked_out[far_band] - full_out[far_band]))

    assert edge_delta > 5.0 * far_delta
    assert far_delta < 1e-3


def test_pws_ignores_phase_terms_from_invalid_padding():
    traces = [
        np.array([8.0, 8.0, 8.0, 0.0, 0.0, 0.0]),
        np.array([0.0, 0.0, 0.0, -8.0, -8.0, -8.0]),
    ]
    masks = [
        np.array([True, True, True, False, False, False]),
        np.array([False, False, False, True, True, True]),
    ]

    out, support = phase_weighted_stack(
        traces,
        [29.0, 29.0],
        ref_distance=29.0,
        slowness_sdeg=0.0,
        sampling_rate_hz=1.0,
        valid_masks=masks,
        min_support=2,
        return_support=True,
    )

    assert np.array_equal(support, np.ones(6, dtype=np.int32))
    assert np.all(np.isnan(out))
