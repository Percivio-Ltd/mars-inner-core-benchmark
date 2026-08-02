from __future__ import annotations

from pathlib import Path

from obspy.taup import TauPyModel, taup_create


def test_taup_smoke_model_from_generated_nd(tmp_path):
    nd = tmp_path / "sample.nd"
    nd.write_text(
        """0.0 4.5 2.6 3.3
3000.0 5.0 2.9 3.3
outer-core
3389.5 5.0 2.8 4.0
inner-core
3389.5 7.0 4.0 6.5
"""
    )
    # Build a temporary TauP cache once to verify we can load from its serialized form.
    taup_create.build_taup_model(filename=str(nd), output_folder=str(tmp_path))
    model_npz = tmp_path / "sample.npz"
    assert model_npz.exists()

    # Build a minimal TauP model and ensure interface is loadable.
    # build_taup_model API is exercised indirectly by this smoke path in the pipeline scripts.
    model = TauPyModel(model=str(model_npz))
    assert model is not None
