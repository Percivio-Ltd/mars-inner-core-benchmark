# Publication assessment — Paper 0 program state (lead, 2026-07-26)

Operator-requested record of the lead's unbiased publication-facing
assessment, written after § A.4 completion, two independent completion
reviews (gpt-5.6 formal review; Codex adversarial audit with clean-tree
reruns), and the fail-closed chain-repair cycle. This is an assessment,
not a registered scientific artifact; the registered record remains
`papers/Paper0/Paper0.md` and `CONTINUITY-paper0.md`.

## Bottom line

We hold one genuinely publishable result: a rigorous, independently
audited public-data non-reproduction of a high-profile Nature claim. Its
best home is a standalone reproducibility paper (Seismica first choice;
GJI/SRL alternatives), with an optional short Matters Arising derivative.
The rigor apparatus is unusually strong; the scientific novelty is
moderate; the impact case rests on the Mars inner-core claim being
recent, prominent, and now demonstrably fragile under public
reconstruction.

## What we have, stated coldly

Under a provenance-gated public reimplementation: the published PKiKP
pair is never the global maximum under either tested polarization
operator; a stronger, kinematically unexplained ridge sits ~58 s away;
the 602-vs-662 branch competition flips with the inclusion of one or two
events out of 23; audited alignment error cannot explain the offset; and
the published coordinates sit where the reference model predicts PKiKP
while the dominant competing feature matches no computed branch. Two
independent reviews forced the wording down to what the evidence
supports; that narrowed wording is the publishable claim: a
current-provenance non-agreement plus internal fragility — not a
refutation.

## The deflationary reading (write the paper as if a referee holds it)

Our pipeline is not the authors' pipeline (`succeeded_mps_only` deglitch
lane, public MK-style operator, our alignment, N=200 methods-robustness
bootstrap). "Failed to reproduce" could mean "public approximation
insufficient," not "claim fragile." Two defenses are already in hand and
should be the paper's spine:

1. The invariant across both operators is that the published pair is
   subordinate — the operators disagree on the winner but agree on that.
2. The composition sensitivity is internal to our own pipeline: even
   granting every approximation, the detection competes with a stronger
   feature whose identity depends on which events are stacked.

The second point generalizes into the most citable idea:
model-conditioned peak selection in low-SNR vespagram stacks — the peak
is found where the model says to look while a stronger unexplained
feature sits nearby.

## Channels, ranked by expected value

1. Standalone reproducibility paper — Seismica (replication-friendly)
   or GJI/SRL. Preregistered criteria, outcome-blind amendments,
   provenance chains, fail-closed machinery, hashed manifests, and two
   independent audits make this close to a model submission for the
   genre. EarthArXiv preprint immediately regardless.
2. Nature Matters Arising — higher risk, narrower payoff (~1,200 words,
   author rebuttal on pipeline fidelity is the likely response). Viable
   after or alongside the standalone, referencing it for depth.
3. Methods companion (benchmark protocol: registered criteria, adverse
   controls, identity verification) — real but secondary; much can live
   in the main paper's SI.
4. Paper 1 / Track B — potential, not achievement, until unparked;
   not assessable from its current state.

## Cheapest additions that most raise the ceiling

- Leave-one-out event influence on the branch competition (registered as
  CARD_P0-LOO-INFLUENCE in this directory).
- One headline significance statement — rank/background-quantile/power
  framing of published pair vs competing ridge (registered as
  CARD_P0-SIG-STATEMENT in this directory).
- UCLA deglitch-lane feasibility on a subset (`UCLA_v4.zip` MATLAB
  source is in the pinned checkout; Octave feasibility unknown) — closes
  the most likely rebuttal; bounded experiment, possibly a dead end.
- Zenodo capsule of the already-hashed artifact set — near-zero marginal
  work given the S3/manifest discipline.

## What not to oversell

The achievement so far is rigor applied to a robustness question, not
new physics. If the original detection survives (in-house deglitching
and the exact operator could legitimately suppress our ridge), this work
still stands as the careful public-data robustness analysis of record.
That is the correct framing to write toward, and the one most likely to
pass both referees and the original authors.
