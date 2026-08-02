# Units and Conventions

- **Slowness:** `s/°`
- **Distance:** degrees
- **Time:** seconds relative to direct `P` arrival
- **Reference distance:** `29.0°`
- **Source depth:** `33 km`
- **Mars radius:** `3389.5 km`
- **Shift convention (SINGLE SOURCE OF TRUTH):**

```
roll_samples = int(round(-slowness_sdeg * (distance_deg - ref_distance_deg) * sampling_rate_hz))
```

- **Rotation:** UVW → ZNE using nominal SEIS VBB azimuth/dip:
  - UV azimuth `135.0`, dip `-29.3`
  - VV azimuth `15.0`, dip `-29.3`
  - WV azimuth `255.0`, dip `-29.3`
- **Filter:** Butterworth bandpass, 4 corners, zero-phase, `0.2–0.8 Hz`
- **Polarization filter:** Production public M-K operator `montalbetti_kanasewich_1970` with `5 s` windows and `90%` overlap; the principal-axis/DOP projection is retained only as a labeled ablation, and compatibility artifacts still use the legacy `paperfaith` mode name
- **Filter bank:** Half-octave zero-phase bands with center frequencies from `1/16 Hz` to `2 Hz`, followed by the public MK-style polarization filter and `5 s` envelope smoothing
- **FDPA diagnostic:** Compact public Gaussian-windowed frequency-shift diagnostic with three-component spectra, `3 x 3` cross-spectral covariance, `90%` overlapping windows, DOP threshold `0.6`, azimuth, inclination, and VRM-HRM products
- **Normalization:** z-score within variant windows
  - `A`: `400–800 s`
  - `B`: `1100–1500 s`
  - `C`: `-100–2200 s`
- **Envelope:** absolute analytic amplitude via `obspy.signal.filter.envelope`, then smoothed by a `5 s` boxcar (`np.convolve`)
