# P0-UCLA-FEAS — UCLA_v4 deglitch package: Octave feasibility card

Date: 2026-08-01. Host: Nimue (macOS arm64, Darwin 24.6.0). Author: sub-Fable researcher.
Isolated dir: `/Users/artuskg/marsquake_runs/20260801_ucla_feas/` (all probe artifacts, logs, this card).
Repo consulted read-only: `/Users/artuskg/GitRepos/MarsQuake` (no writes, no git mutations, `data/processed/` and `results/` untouched).
Scope: feasibility only. No full production deglitch was run.

## VERDICT: EXECUTABLE-OCTAVE

The public UCLA_v4 MATLAB deglitch package executes reproducibly on this Mac under GNU
Octave 10.3.0 (conda-forge, osx-arm64) with the Octave Forge `signal` 1.4.7 and `control`
4.2.3 packages, with exactly one code-level MATLAB/Octave incompatibility on the used path
(`ifft(...,'symmetric')` in `MakeGlitch.m`, fixed by a 2-line documented shim that
reproduces the shipped fixtures to machine precision, rel. max diff <= 5.6e-16). The full
per-glitch chain was demonstrated on the pinned probe event S0105a (XB.ELYSE.02.BHU):
MiniSEED read (`rdmseed.m`, ships in archive) -> 2 sps decimation -> STA/LTA detection ->
2 sps glitch fits (12 accepted at cc>0.9) -> 20 sps three-branch least-squares fit
(best cc=0.9931) -> residual replacement -> MiniSEED write (`mkmseed.m`, ships in archive)
-> ObsPy round-trip with exact start time, 24001 samples, and bit-identical data outside
the deglitched window. Positive and adverse controls passed. The harness contract of
`_run_ucla_if_configured` is satisfiable end-to-end; the strict `mps_ucla_verified` rung
additionally requires an attestation decision by the lead (see Harness contract). The
package's cross-channel step `MAIN20SPSReconcile.m` and a full-event run were not
exercised (out of feasibility scope); both use only functions shipped in the archive.

## Archive inventory & data flow

Archive: `/Users/artuskg/GitRepos/MarsQuake/external/seisglitch/MATLAB_ALTERNATIVES/UCLA_v4.zip`
(2.2 MB), extracted to `ucla_v4/UCLA_v4/` in the isolated dir (13 MB, 40 `.m` files, 3530
lines total, plus fixtures). Siblings ISAE_v3.zip / ISAE_v4.zip exist and were not probed.

Ships with everything needed (no external code dependency):
- MiniSEED IO: `rdmseed.m` (1031 lines) and `mkmseed.m` (533 lines) — F. Beauducel's
  pure-MATLAB readers/writers, no MEX. `mkmseed.m:28-35` documents encodings (Steim-1/2,
  int, float; doubles default to IEEE float64).
- Response metadata: `metadata/RESP.XB.ELYSE.02.{BH,MH}{U,V,W}`.
- FIR decimation coefficients: `PFO_div5.txt`, `PFO_div2.txt` (used by `decimeFPGA.m`).
- Sample event: `S0235b_VBB.mseed` (2 h, XB:ELYSE:02:BHU/V/W @ 20 sps, 997 records).
- Parameter fixtures (contents verified by loading, `probe/control1_positive.log` and
  `probe/probe3_s0105a.log`): `Conservative.mat`=0, `cclim.mat`=0.9, `cclim2.mat`,
  `Nlevel.mat`=4, `NLIMspike.mat`=3, `fetch.mat`=1; green functions `green20sps.mat`
  (1x20480), `green2sps.mat` (1x2048), `greenspike.mat` (1x20480).
- Prior-run outputs: `dc.mat` (3 cells, each 142840 doubles) and `aaout3.mat`
  (43/34/37 x 20 rows) — dimensions match S0235b after 3-channel time alignment, i.e.
  these are the authors' own (MATLAB) results for the shipped sample event.
- Inert strays: AppleDouble `._*` files, `MAIN20SPSReconcileNew.m~` backup, ASCII debug
  dumps `junk`, `wminus`, `y` (not loaded by any shipped code path; `load wminus` appears
  only commented out in `greenfitSlope.m:10`).

Data flow (entry point `MAIN.m`):
1. `MAIN.m:24` pins `file='S0235b_VBB.mseed'`; `MAIN.m:26` calls `MakeGlitch('U')` to
   build green functions from RESP poles/zeros (impulse -> transfer function ->
   `ifft(...,'symmetric')` -> FPGA-style FIR decimation 100->20->4->2 sps via
   `decimeFPGA.m`); `MAIN.m:29-47` saves the green + parameter fixtures.
2. `MAIN2SPS.m` (detection, 2 sps): `MAIN2SPS.m:8` runs `XseedDataFDS.m`, which calls
   `rdmseed(file,'plot')` and selects channels by fixed columns of `ChannelFullName`
   (`XseedDataFDS.m:19-21`: `out(n,10:15)=='02:BHU'|'02:BHV'|'02:BHW'`) into
   `Data{1..3}`, `times{1..3}` (raw counts, datenum). `funcadjustTimes.m` trims all
   channels to a common time window. `MAIN2SPS.m:45` decimates by 10 to 2 sps
   (`decimate`); `MAIN2SPS.m:59-60` bandpass `butter(2,[0.001 0.4])` + `stalta.m`
   (inverse-filter glitches to Gaussians, STA/LTA ratio; `QuickClean.m` pre-removes big
   glitches; `findmaxs.m` picks peaks above `Nlevel` with green-correlation >0.7);
   `MAIN2SPS.m:62` `funcPeaker` fits up to 4 overlapping glitches per window at 2 sps
   with `fflag=0 -> greenfitSlope` (`funcPeaker.m:9`, `func.m:3`), damped LSQ `mylsq.m`
   (own implementation, `inv(am'*am+damp)*am'*del'`; finite-difference Jacobian
   `deriviti.m`), accepting fits with |cc|>`cclim`. Cross-channel augmentation
   `MAIN20SPSReconcile.m`, then a second `funcPeaker` pass at cclim=0.4.
   Output (session workspace, not files): `aaout` (rows `[cc, I1, t, M, gflag, a...]`),
   `I1P{jk}`, `G1P{jk}`, `Data`, `times`.
3. `MAIN20SPSJuly26.m` (cleaning, 20 sps): consumes the *workspace* of step 2 (its
   `load Conservative` at line 6 loads only the 1x1 flag — verified; `aaout` etc. must
   already exist, confirmed by adverse control B). Per glitch: window
   `N1=I1P*10-120, N2=N1+500` (gflag-dependent, lines 41-49); initial amp/phase from the
   2 sps fit (`PHASE=10*a2sps`, lines 27-32); with shipped `Conservative=0` it fits three
   competing models — `PREP08`->fflag=8 `NSpikeFloatGreenLine` (N glitches + N spikes +
   quadratic line), `PREP03`->fflag=3 `funcConvGaussSpikeThree` (Gaussian convolver),
   `PREP39`->fflag=39 `greenfitExpCSpike20SPS` (double glitch w/ exponential) — takes the
   min-ssq branch (lines 144-147), final polish loop, significance test `testSpikes.m`
   with `NLIMspike`, then replaces the window by residual + straight line
   (lines 199-204), accumulating cleaned `dc{jk}` and fit table `aaout3`; saves
   `aaout3.mat`, `dc.mat` (lines 209-210).
4. `PREPmkmseed.m`: writes corrections (`dc-Data`), cleaned (`dc`), and raw (`Data`)
   channels via `mkmseed(name, data, times, 20)` and concatenates per-channel day files
   with a shell escape `!cat XB.* >temp.mseed` (lines 4-11).

Expected input form (used directly for the probe): multiplexed MiniSEED with
XB.ELYSE.02.BHU/V/W at 20 sps in raw counts. `data/raw/S0105a.mseed` matches exactly
(verified with mars-ic ObsPy: 3 traces XB.ELYSE.02.BH{U,V,W}, 20.0 Hz, int32, 51200
samples each) — no format conversion is needed, only an ObsPy `trim` for the bounded
probe window.

`func.m` dispatches ~30 `fflag` model variants; only 4 exist in the archive
(`greenfitSlope`=0, `funcConvGaussSpikeThree`=3, `NSpikeFloatGreenLine`=8,
`greenfitExpCSpike20SPS`=39) — exactly the 4 used by the shipped path, so the ~25
missing functions are dead branches for this pipeline.

## Dependencies & risks

MATLAB-toolbox surface (all resolved by Octave Forge `signal`):
- `butter`, `filtfilt` (`MAIN2SPS.m:59`, `stalta.m:6,29`, `PREP08.m:82-83`,
  `FindPrecursors.m`), `decimate` (`MAIN2SPS.m:45`), `xcorr` (`SampleFraction.m:12`),
  `xcov` (`TruncateXcov.m:5`). Everything else is core (fft/ifft, conv, corrcoef,
  detrend, datestr/datenum/datetick, cellfun-free loops). No MEX, no `webread`, no
  Wavelet/Optimization toolbox use (`mylsq.m` is hand-rolled damped LSQ).

Octave environment (fresh, reproducible):
- `micromamba create -y -n octave-ucla -c conda-forge octave` -> Octave 10.3.0 osx-arm64.
- conda-forge has NO `octave-signal`/`octave-control` for osx-arm64 (verified:
  `micromamba search -c conda-forge 'octave-*'` returns only fuzzy-logic-toolkit, onsas,
  splines).
- Packaging defect found: the conda-forge Octave binary carries NUL-padded build-prefix
  replacements in `mkoctfile`'s embedded `FFLAGS`, `CXXFLAGS`, `FLIBS` (verified:
  `mkoctfile-10.3.0 -p FFLAGS | cat -v` ends in a run of `^@`), a dead CI path for `F77`
  (`/Users/runner/miniforge3/...`), and `-fopenmp` in `XTRA_CXXFLAGS` (unsupported by
  Apple clang). Consequence: `pkg install -forge` fails out of the box ("no input files"
  from compilers — the embedded NUL truncates the constructed compile command).
- Fix (recorded verbatim in `octave_pkg_install_round3.log` invocation): install
  conda-forge `c-compiler cxx-compiler fortran-compiler` into the env, then run
  `pkg install -forge control signal` with environment overrides
  `F77/FC/CC/CXX` -> env compilers, clean `FFLAGS='-fPIC -O2 -std=legacy -fexceptions'`,
  `CXXFLAGS='-fPIC -O2 -stdlib=libc++'`, `CFLAGS='-fPIC -O2'`, and a NUL-stripped
  `FLIBS` pointing at the env gcc runtime. Result: control 4.2.3 + signal 1.4.7 build
  and load; `butter/filtfilt/decimate/xcorr/xcov` all verified working.
- Note: Octave Forge packages install to `~/.local/share/octave/api-v60/packages/`
  (Octave's per-user location; outside the isolated dir but part of the Octave env, as
  permitted). Homebrew was not used.

MATLAB/Octave incompatibilities found on the used path:
1. `ifft(X,'symmetric')` (`MakeGlitch.m:35-36`): Octave 10 rejects the flag
   ("invalid conversion from string to real scalar", control1d). A naive
   `real(ifft(X))` is NOT equivalent (MATLAB discards the unmodified upper
   half-spectrum; the code only fills bins 1..NS/2+1) — demonstrated: naive shim gives
   corr 0.008 vs shipped `green20sps` (probe5). Correct 2-line shim: conjugate-mirror
   the lower half (`tf(NF+1:NS)=conj(tf(NF-1:-1:2))`) then `real(ifft(tf))` —
   reproduces all three shipped green fixtures to rel. max diff <= 5.6e-16,
   corr 1.000000000 (probe5b). This simultaneously verifies the fixtures' provenance:
   they are exactly `MakeGlitch('U')` on the shipped RESP.XB.ELYSE.02.BHU.
2. None other encountered: rdmseed/mkmseed, cell/struct code, `save`/`load` of the
   v7 .mat fixtures, graphics (`figure/plot/pause` headless via gnuplot toolkit,
   warnings only), all ran unmodified.

Latent package defects (not Octave-specific; noted for the lead, none blocks the probe):
- `MakeGlitch.m:2` hardcodes `DIRNAME='~/Box Sync/INSIGHT/GLITCH_LIB/'` although the
  RESP files ship in the archive — out-of-the-box `MAIN.m` fails at `read_resp_v2`
  (adverse control A). Not needed at all if the shipped green fixtures are used.
- `MAIN2SPS.m:35` calls `ConvertTo20sps` (freq==10 branch) — function absent from the
  archive; harmless for 20 sps input.
- `QuickClean.m:4` `start=I2(1)` crashes if no sample exceeds 3*std (very quiet data).
- `PREPmkmseed.m:9` `out(53:58)` extracts the event name by absolute pwd character
  positions — fragile; a production runner should name outputs itself.
- `XseedDataFDS.m` calls `rdmseed(file,'plot')`; plot mode is unnecessary overhead
  (probe called `rdmseed(file)` directly).
- Interactive burden: `MAIN20SPSJuly26.m` has `pause(1)` per glitch (line 177) and
  per-fit figures; `stalta.m` pauses 3 s per channel. Headless-tolerable (gnuplot
  offscreen) but a production runner should neutralize `pause`/plots for speed.

## Probe evidence (exact commands + key output)

All logs live under `/Users/artuskg/marsquake_runs/20260801_ucla_feas/` (probe scripts in
`probe/`). Environment creation logs: `octave_env_create.log`,
`octave_pkg_install.log` (round 1, failure evidence), `octave_pkg_install_round2.log`
(failure evidence), `octave_pkg_install_round3.log` (success).

1. Unzip + inventory:
   `unzip -o -q .../UCLA_v4.zip -d ucla_v4` (file list in § Archive inventory).
2. Harness contract read: `scripts/02_preprocess/deglitch_mps_ucla.py` lines 29-51,
   200-314, 372-460 (details in § Harness contract).
3. Positive control 1 — `probe/control1_positive.m` ->
   `micromamba run -n octave-ucla octave --no-gui --norc control1_positive.m`
   (`probe/control1_positive.log`, exit 0):
   - trivial computation OK (det=-2, linear solve residual <1e-12);
   - all 11 .mat fixtures load with expected types/sizes;
   - `rdmseed` on shipped `S0235b_VBB.mseed`: 997 blocks, `XB:ELYSE:02:BHU/V/W`,
     npts 143076/143094/142855 @ 20 sps;
   - `ifft(...,'symmetric')` fails (incompatibility #1, expected);
   - offscreen `figure`+`plot` OK (gnuplot toolkit).
4. Adverse control — `probe/control2_adverse.m` (`probe/control2_adverse.log`, exit 0,
   all three failed VISIBLY, no silent no-op):
   - A `MakeGlitch('U')` from pristine archive: `fgetl: invalid stream number = -1`
     (missing hardcoded Box Sync path);
   - B `MAIN20SPSJuly26` without prior-stage workspace: `'aaout' undefined near line 8`;
   - C `rdmseed` on nonexistent file: `File ... does not exist.`
5. Input conversion (mars-ic ObsPy, no installs): trim first 1200 s of
   `data/raw/S0105a.mseed` (copied into `probe/` first) ->
   `probe/S0105a_window.mseed` (3 x 24001 int32 @ 20 Hz).
6. Main probe — `probe/probe3_s0105a.m` (`probe/probe3_s0105a.log`, exit 0), BHU only,
   mirrors the shipped code path line-for-line (deviations: `pflag=0` i.e. plots off;
   single channel; first glitch; Conservative==1 subpath):
   - fixtures: cclim=0.9 Nlevel=4 NLIMspike=3 Conservative(shipped)=0;
   - `rdmseed` reads the ObsPy-written window (npts=24001, counts -10939..);
   - `stalta`+`findmaxs`: 14 candidate peaks at 2 sps;
   - `funcPeaker`: 12 accepted glitch rows with cc>0.9 (best 0.981);
   - 20 sps window N1=1610 N2=2110, gflag=1; `PREP08`+6x`mylsq`: ssq=1.49182e6;
     `testSpikes` + final `func`: cc=0.9922;
   - replacement modifies 498/501 window samples, max |delta| 440.7 counts;
   - `mkmseed` writes `XB.ELYSE.02.BHU.2019.073` (196608 bytes).
7. ObsPy round-trip check — `probe/roundtrip_check.py`
   (`probe/roundtrip_check.log`, exit 0, "ROUNDTRIP OK"): read-back id
   XB.ELYSE.02.BHU, 20 Hz, 24001 samples float64, start-time delta 0.0 s vs input;
   inside window max|diff|=440.7 counts (498/501 changed); outside window
   max|diff| = 0 counts (bit-identical).
8. Default-branch probe — `probe/probe4_conservative0.m`
   (`probe/probe4_conservative0.log`, exit 0): full shipped Conservative=0 inner loop on
   the same glitch: fflag=8 ssq=1.49182e6, fflag=3 ssq=1.32082e6, fflag=39
   ssq=1.44725e6; best branch fflag=3; final polish cc=0.9931; replacement 499/501
   samples, max 421.2 counts.
9. Green-function regeneration — `probe/MakeGlitch_shim.m` (3-line documented shim:
   renamed function, DIRNAME -> archive metadata dir, conjugate-mirror ifft emulation):
   naive-shim failure evidence in `probe/probe5_makeglitch.log` (corr 0.008/0.042/1.0);
   correct shim in `probe/probe5b_makeglitch.log`: rel-maxdiff 5.6e-16 / 4.49e-16 /
   2.35e-16, corr 1.000000000 for green20sps/green2sps/greenspike vs shipped fixtures.
10. Shipped-reference check: `dc.mat` cells are 142840 doubles each and `aaout3.mat`
    cells are 43/34/37 x 20 — consistent with a completed authors' MATLAB run on the
    shipped S0235b sample (basis for the proposed equivalence run below).

Numerical caveat (honest limitation): `mylsq.m` uses `inv()` on finite-difference normal
equations; cross-platform (MATLAB vs Octave / BLAS) bit-identity is NOT expected —
equivalence must be judged by tolerance on cleaned waveforms/fit tables, which is exactly
what the proposed S0235b discriminating run measures.

## Controls

- Positive: trivial known-true computation; 11/11 fixture loads; rdmseed on the shipped
  sample; offscreen graphics — all passed (evidence item 3).
- Adverse: three deliberately broken invocations (missing RESP path, missing prior-stage
  workspace, missing input file) all failed loudly with distinct errors; no silent
  no-op observed anywhere (evidence item 4).
- Provenance control: regenerated greens match shipped fixtures to machine precision
  (evidence item 9) — the strongest available no-MATLAB check that the Octave port
  computes what the authors' MATLAB computed for the deterministic generation stage.

## Harness contract (`scripts/02_preprocess/deglitch_mps_ucla.py`, read-only)

Contract extracted from `_run_ucla_if_configured` (lines 372-460) and helpers:
- `ucla_command`: string (shlex-split) or list (line 207-215); placeholders `{input}`,
  `{output}`, `{work_dir}` substituted per part (392-402); executed with
  `cwd=work_event_dir` (403). `{input}` is the CURRENT `output_path`, i.e. the
  MPS-deglitched file — the UCLA stage chains after MPS, it does not see the raw file
  (388-394; MPS backup `<stem>_mps_before_ucla<suffix>` is made and restored on failure,
  389-391, 405-418).
- Expected output: `{output}` = `work_event_dir/<stem>_ucla<suffix>` must exist after a
  zero return code, else `failed_missing_ucla_output` (416-424). On success it is copied
  over `output_path` (436).
- Optional sidecar `{output}.ucla.json` (426): to reach `mps_ucla_verified` (the only
  status in `DEFAULT_ALLOWED_DEGLITCH_STATUSES`, line 40) it must carry
  `verification_status: "mps_ucla_verified"` PLUS non-empty `algorithm`,
  `parameters_sha256`, and hash evidence `expected_output_sha256` (or
  `fixture_output_sha256`/`verification_fixture_sha256`) equal to the actual sha256 of
  the written output (282-304, 438-448). Attestation without complete evidence ->
  `sidecar_attested_not_independently_verified`; no attestation -> `ucla_unverified`;
  no command configured -> `blocked_missing_ucla_runner` (379-386).

Exact invocation that wires the demonstrated route (runner script to be built in a
follow-up card; every stage it needs was individually demonstrated by probes 3-5):

```json
"ucla_command": ["/Users/artuskg/marsquake_runs/20260801_ucla_feas/runner/run_ucla_octave.sh",
                 "{input}", "{output}", "{work_dir}"]
```

`run_ucla_octave.sh` (spec, ~30 lines shell + ~120 lines Octave driver):
1. `set -euo pipefail`; args IN/OUT/WORKDIR.
2. `micromamba run -n octave-ucla octave --no-gui --norc ucla_driver.m` with IN/OUT via
   environment; driver: `addpath` archive dir; `rdmseed(IN)`; select 02:BHU/V/W
   (XseedDataFDS logic); `funcadjustTimes`; MAIN2SPS body (all 3 channels incl.
   `MAIN20SPSReconcile`); MAIN20SPSJuly26 body (`pause`/plots neutralized);
   `mkmseed` per channel into WORKDIR; concatenate to OUT (byte concatenation of
   MiniSEED files, as `PREPmkmseed.m:7` does with `!cat`).
3. Sidecar: write `OUT.ucla.json` with `algorithm` ("UCLA_v4 MAIN2SPS+MAIN20SPSJuly26,
  octave-10.3.0, signal-1.4.7"), `parameters_sha256` (sha256 over the fixture set +
  driver), `expected_output_sha256` = `shasum -a 256 OUT`.
- Encoding note: input int32/Steim, UCLA output float64 (mkmseed default for double) —
  ObsPy reads both; deglitched samples are inherently non-integer.
- Every element of the ladder up to and including `mps_ucla_verified` is mechanically
  satisfiable today. HOWEVER: `expected_output_sha256` computed by the runner over its
  own output is self-attestation. Whether `verification_status: mps_ucla_verified` may
  be claimed should, scientifically, be gated on the S0235b equivalence run below —
  this is a lead decision, flagged in Open questions, not taken here.

## Cheapest discriminating next run + stop condition

Run the Octave pipeline on the archive's own `S0235b_VBB.mseed` (3 channels, full
MAIN2SPS -> MAIN20SPSReconcile -> MAIN20SPSJuly26 chain with shipped fixtures,
Conservative=0) and compare the resulting `dc{}`/`aaout3{}` against the SHIPPED
`dc.mat`/`aaout3.mat` — which are the authors' own MATLAB outputs for that event
(dimension-verified above). This discriminates MATLAB-vs-Octave numerical equivalence of
the entire algorithm on the authors' reference event with zero MATLAB access, and
simultaneously exercises the one untested step (`MAIN20SPSReconcile`). Cost: one
finite Octave run (estimated minutes-scale; 2 h of 3-channel data, ~40 glitches/channel)
plus a small comparison script.
Stop condition: per-channel comparison table (n glitches found vs 43/34/37; waveform
max/rms deviation of `dc` vs shipped `dc.mat`; fit-table row matching) — declare
equivalent/not-equivalent against a preregistered tolerance chosen by the lead
(suggested starting point: rms(dc_octave - dc_matlab) << rms(Data - dc_matlab), i.e.
port noise well below the physical correction, plus glitch-count agreement).
If equivalent: build `run_ucla_octave.sh`, wire `ucla_command`, and decide the
attestation policy for `mps_ucla_verified` on the one-event subset (S0105a).
If not equivalent: the divergence localizes to a specific stage (each stage is
individually probed here), and the verdict downgrades to EXECUTABLE-MATLAB-ONLY for
strict attestation purposes.

## Open questions (for the lead — not decided here)

1. Attestation semantics: is runner-side self-attested `expected_output_sha256`
   acceptable for `mps_ucla_verified`, or is that status reserved until the S0235b
   MATLAB-reference equivalence run passes? (Recommended: the latter.)
2. Chaining semantics: the harness feeds the MPS-deglitched file as `{input}` to the
   UCLA stage (deglitch_mps_ucla.py:388-394). Is UCLA-on-MPS-output the intended
   science, or should the UCLA route run on raw data in a separate lane?
3. `MAIN20SPSReconcile` (cross-channel candidate sharing, cclim=0.4 second pass):
   include in the production one-event run as shipped, or hold fixed? (It changes which
   glitches are removed; shipped default includes it.)
4. `Conservative` flag: shipped fixture is 0 (three-model competition). Keep 0?
5. Green functions: use shipped fixtures (now provenance-verified) or regenerate per
   channel from RESP via the shimmed MakeGlitch ('U' greens are used for all three
   channels in the shipped flow, `MAIN.m:26-27`)?
6. Whole-trace vs event-window deglitching for the Paper 0 lane (UCLA operates on
   whatever `{input}` window the harness provides; probe used 20 min).

## Deviations from shipped behavior in the probes (full list)

- `pflag=0` (no per-fit plots) in probe3/4; shipped `MAIN2SPS.m:61` uses `pflag=1`.
  Visual only; the accept/reject logic does not read `pflag`.
- Probes ran BHU only, first detected glitch only; `MAIN20SPSReconcile` skipped
  (3-channel step, requires all channels).
- probe3 forced the `Conservative==1` subpath; probe4 then ran the shipped
  `Conservative=0` three-branch path on the same glitch (both work).
- `rdmseed` called without `'plot'` option (XseedDataFDS uses `'plot'`).
- `MakeGlitch_shim.m`: 3 changed lines (function name; DIRNAME -> archive metadata dir;
  conjugate-mirror + `real(ifft(...))` emulation of `'symmetric'`), diff shown in
  session log; original archive files untouched.
- Probe drove the per-glitch loop from `aa` directly (single channel) instead of the
  `I1P/G1P/a1P` cell repackaging (`MAIN20SPSJuly26.m:8-12` / `MAIN2SPS.m:67-68`) — same
  values by construction (aa columns 2/5/6+ per `funcPeaker.m:92`).
