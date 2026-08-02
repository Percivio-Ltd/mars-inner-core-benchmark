# Validation Summary

- Inventory: 26/26 events complete
- Benchmark combo: paperfaith / envelope / A / nth_root / 20 s
- Benchmark check [lane=paperfaith/envelope/A/nth_root/win20; audit=current-run-stale-baseline]: pass — current-run audit does not gate on the historical pre-current-run baseline; published-target replication gates remain separate
- Benchmark displaced_ridge [key=displaced_ridge; lane=paperfaith/envelope/A/nth_root/win20; window=550-700s]: t=663.80s, s=-3.64s/deg
- Benchmark published_PKIKP_box [key=published_PKIKP_box; lane=paperfaith/envelope/A/nth_root/win20; window=584-624s]: t=601.95s, s=-6.67s/deg
- Benchmark PKKP_target [key=PKKP_target; lane=paperfaith/envelope/A/nth_root/win20; window=1320-1360s]: t=1341.00s, s=-6.97s/deg
- Delta notation: all validation offsets use explicit Δ versus the named target
- Bootstrap fidelity: methods_robustness_200 (N=200; published-equivalent=False; published N=10000)
- Bootstrap PKiKP: warn — 85% bootstrap robust estimators vs paper target: occupancy argmax Δt=60.00s Δs=2.76s/deg; weighted median Δt=34.60s Δs=2.96s/deg; gaussian fit degenerate_fit=True (slowness:residual_rms_fraction|tri_estimator_inconsistency)
- Bootstrap PKKP: warn — 85% bootstrap robust estimators vs paper target: occupancy argmax Δt=-106.10s Δs=1.04s/deg; weighted median Δt=-52.10s Δs=0.84s/deg; gaussian fit degenerate_fit=True (slowness:residual_rms_fraction)
- Type II distance-stratified artifacts: pass — Type II distance-stratified artifacts are present and structurally valid
- Type III jitter artifacts: pass — Type III jitter artifacts are present and structurally valid
- Deglitch summary [attestation=succeeded_mps_only-by-design; strict_gate=mps_ucla_verified]: fail — deglitch run summary is missing verified MPS+UCLA status for every event; unverified statuses: succeeded_mps_only
- Model profile: pass — generated model has liquid outer core and non-decreasing depths

## Representative event galleries
- S0235b: rel L2 diff = 0.1202 (/Users/artuskg/GitRepos/MarsQuake/results/validation/figures/S0235b_preprocessing_gallery.png)
- S0173a: rel L2 diff = 0.5533 (/Users/artuskg/GitRepos/MarsQuake/results/validation/figures/S0173a_preprocessing_gallery.png)
- S1222a: rel L2 diff = 0.6295 (/Users/artuskg/GitRepos/MarsQuake/results/validation/figures/S1222a_preprocessing_gallery.png)
