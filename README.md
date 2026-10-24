# Power Analysis Dashboard

**Live app:** https://poweranalyse.streamlit.app

This dashboard answers one question: **with the money we have, how big does an effect need to be before our experiment can reliably detect it?** It compares two designs:

- **2-way experiment:** control vs one treatment.
- **4-way experiment (2x2):** two treatments, A and B, crossed into four groups: control, A only, B only, and A + B.

All of the statistics live in [`power_calc.py`](power_calc.py), and the formulas are explained in plain English in [`METHODOLOGY.md`](METHODOLOGY.md).

---

## Key terms

| Term | What it means |
|---|---|
| **Significance (e.g. 95%)** | How sure we want to be before calling a result real. 95% means we accept a 5% chance (α = 0.05) of a "significant" result when there is actually no effect. |
| **Power (e.g. 80%)** | If an effect of a given size is real, the chance that our test detects it. At 80% power we still miss a real effect 1 time in 5. |
| **MDE (minimum detectable effect)** | The smallest true effect we would detect with the chosen power. **Smaller is better.** Effects smaller than the MDE could be real, but the study will probably miss them and report "no effect". |
| **SD units** | The MDE divided by the outcome's standard deviation, which makes outcomes on different scales comparable. A rough guide: 0.2 SD is small, 0.5 SD is medium and 0.8 SD is large. Many attitude and messaging interventions move outcomes by roughly 0.1–0.3 SD. |
| **pp (percentage points)** | The unit for binary outcomes. Going from 30% to 40% is a 10 pp effect. |
| **False positive** | A test that comes out significant purely by chance, when the treatment actually does nothing. |

---

## Step 1: Budget (sidebar)

| Input | Default | Notes |
|---|---|---|
| Budget | $800 | Total participant payments. |
| Rate per person per hour | $15 | |
| Duration per person | 30 min | Include **everything** a participant does: questionnaire, game, and any pre-test session. A separate 15-minute pre-test means entering 45 minutes. |

**Participants we can afford** = budget ÷ (rate × duration in hours), **rounded down** so we never overspend. With the defaults: $800 ÷ $7.50 = 106.7, so **106 participants**.

Everything else follows from this number. Doubling the budget does *not* halve the MDE: the MDE shrinks with the square root of the sample, so it takes **4× the budget to halve the MDE**.

---

## Step 2: Enter the question assumptions

Each question (outcome) needs:

- **Type:** *Continuous* for scales and scores, *Binary* for yes/no outcomes such as "took the action".
- **Estimated average:** the expected mean in the control group. For binary questions, enter a rate between 0 and 1 (e.g. 0.30 for 30%).
- **Estimated standard deviation:** how spread out responses are. Take it from pilot data, a previous wave, or published studies using the same scale. For binary questions it is filled in automatically from the rate.

> **The SD drives the MDE in raw units, so getting it right matters most.** For continuous outcomes the average does not change the MDE; it is only used to express the MDE as a percentage of the mean. For binary outcomes the rate does matter: rates near 50% are the hardest to move detectably.

The 4-way tab has a **"Use same question inputs as the 2-way experiment"** checkbox, so you only enter assumptions once.

---

## Step 3: Read the 2-way tab

### What is compared
There is one comparison per question: **treatment vs control**, with participants split equally (106 becomes 53 / 53).

### Key results panel
- **Participants per group:** e.g. `53 / 53`.
- **MDE per question:** e.g. `0.82 pts (0.54 SD)`, or `25 pp` for a binary question.
- **At least one false positive:** the chance of a fluke significant result across all questions.

### How to interpret it
Ask the team that owns each outcome: *"Is it realistic that our treatment moves this outcome by at least the MDE?"*
- **Yes, and we'd expect more:** the design is adequately powered for that outcome.
- **No, we expect smaller effects:** the study will probably return a null even if the treatment works. Increase the budget, shorten the session, or treat the study as a pilot.
- **"Not achievable" (shown in red):** no realistic effect reaches the target power at this budget.

**Worked example (defaults, SD = 1.5 on a 1–7 scale):** MDE ≈ 0.82 points (0.54 SD). We would reliably detect the treatment moving the average from 4.2 to about 5.0, but not from 4.2 to 4.5. For a binary outcome with a 30% baseline, the MDE is about 25 pp: we would detect 30% → 55%, but not 30% → 40%.

---

## Step 4: Read the 4-way (2x2) tab

### The four groups
| Group | Gets treatment A? | Gets treatment B? |
|---|---|---|
| Control | No | No |
| Variant 1 | Yes | No |
| Variant 2 | No | Yes |
| Variant 3 | Yes | Yes |

The same 106 people are split four ways (`27 / 27 / 26 / 26`).

### Choose which comparisons you will test
The **"Comparisons you will test"** selector controls both which MDEs are shown and how many tests are counted for false positives. Choose only what you will actually analyse and report.

| Comparison | Question it answers | Who it uses | MDE (defaults, SD 1.5) |
|---|---|---|---|
| **Main effect of A** (or B) | Does A work, averaged over whether people also got B? | All 4 groups (A vs not-A) | ≈ 0.82, **same as the 2-way** |
| **Each variant vs control** | Does this specific arm beat control? | Only 2 groups | ≈ 1.16 (≈ 1.4× the 2-way) |
| **Interaction (A x B)** | Does getting both do more (or less) than the two separate effects added together? | All 4 groups, but a difference of differences | ≈ 1.63 (≈ 2× the 2-way) |

### How to interpret it
- **Main effects come almost free.** Testing two treatments in a 2x2 costs nothing extra in MDE, *as long as A and B don't interfere with each other*. That's why a 2x2 can be attractive on a fixed budget.
- **That assumption is the catch.** If A works differently depending on whether people also get B, the main effect becomes a blend that is hard to interpret, and to show that, you need the interaction, which has twice the MDE.
- **Arm-by-arm comparisons cost more.** If stakeholders will ask "did Variant 1 beat control?", you need the variant-vs-control MDE, which is about 1.4× larger.

**Choosing between designs:**
| If the team... | Then |
|---|---|
| Wants two treatments, expects them to act independently, and will report main effects | **4-way (2x2)**: same MDE as the 2-way, with a second treatment for free |
| Needs each arm compared with control, or expects A and B to interact | **2-way**, unless the larger MDEs in the 4-way tab are still realistic |
| Expects effects smaller than the 2-way MDE | Neither design will detect them: increase the budget or treat this as a pilot |

---

## Step 5: The false-positive panel (both tabs)

This panel assumes **no treatment has a real effect** and asks how likely it is that some tests come out significant anyway.

| Metric | Formula | 3 tests, 95% |
|---|---|---|
| **No false positives** | (1 − α)^k | 85.7% |
| **At least one false positive** | 1 − (1 − α)^k | **14.3%** |
| **All tests false positive** | α^k | 0.0125% (essentially zero) |

Here *k* = total tests = number of questions × comparisons per question. The 2-way tab has 1 comparison per question. In the 4-way tab it depends on your selection; "Each variant vs control" counts as 3.

**"At least one false positive" is the number to watch.** It grows with every test you add: 14.3% for 3 tests, and 26.5% for the 4-way design with both main effects on 3 questions (6 tests). With many tests, some significant results are likely to be flukes.

### The Bonferroni toggle
Turning on **"Correct for multiple tests (Bonferroni)"** tests each comparison at α ÷ k instead of α, which keeps "at least one false positive" at or below about 5%.

**The trade-off: every MDE gets larger.**

| Defaults, SD 1.5 | Toggle off | Toggle on |
|---|---|---|
| 2-way, 3 tests: at least one FP | 14.3% | 4.9% |
| 2-way MDE | 0.82 | 0.94 |
| 4-way, both main effects, 6 tests: at least one FP | 26.5% | 4.9% |
| 4-way main-effect MDE | 0.82 | 1.01 |

Use it when any single significant result would be acted on by itself. You can leave it off when results are judged together, for example when you'd only act if several outcomes move in the same direction, but be explicit about that decision.

---

## A 2-minute checklist for the design team

1. **Budget:** confirm the budget, rate and **total** minutes per person (including any pre-test).
2. **Assumptions:** get each team's average and SD (or baseline rate) for each question.
3. **Smallest worthwhile effect:** ask each team for the smallest effect that would matter to them.
4. **2-way tab:** is every MDE at or below the smallest worthwhile effect?
5. **4-way tab:** select the comparisons you'd actually report. Are those MDEs still at or below the smallest worthwhile effects?
6. **False positives:** decide whether to correct (Bonferroni toggle), then recheck the MDEs.
7. **Decide:** choose the 2x2 only if step 5 passes; otherwise run the 2-way design, or raise the budget.

---

## Assumptions and limitations

- **Calculation method:** two-sided tests using a normal approximation, with equal-sized groups.
- **Binary outcomes:** the SD is taken at the baseline rate, which is slightly optimistic, so the true MDE is a little larger.
- **Attrition:** none is assumed. If you expect dropouts, the real MDEs will be larger.
- **Pre-test:** no adjustment for a pre-test is applied. A pre-test only enters through its cost (add its minutes to the duration).
- **4-way main effects:** these assume A and B don't interact.
- **False-positive probabilities:** these treat tests as independent. Outcomes from the same people are usually correlated, so treat them as approximate.

---

## Running locally

```bash
pip install -r requirements.txt
pytest                  # checks the formulas against known values
streamlit run app.py
```