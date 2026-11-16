# Config selection criteria (fixed before running improvement configs I1/I2 and before any test run)

Written: 2026-11-16, after dev runs A0 (dense) and A1 (hybrid), before I1/I2 were run. Test has not been run.

Candidates: A0, A1, I1, I2 (all `gpt-4.1-mini`, temperature 0.01, top_k 3, max 3 searches, dev split, 17 questions).

1. **Hard requirements** (otherwise the config is not eligible):
   - 0 provider/system errors on dev.
   - Abstention on unanswerable dev questions = 2/2, with no unsupported claims.
2. **Primary metric:** mean grounded answer score /2 on the 15 answerable dev questions (manual labels, rule in `results/agent-dev-*/reviews.json`).
   - A more complex config replaces a simpler one only if its mean is higher by **≥ 0.10** (at least 2 grade points over 15 questions). Smaller differences count as a tie, because one label can move the mean by 0.07.
3. **Tie-breaks, in order:**
   1. fewer false abstentions on answerable questions;
   2. higher citation validity (supported citations / all citations);
   3. higher agent Context Evidence Rate (gold evidence in the final context / 15);
   4. lower cost per question;
   5. lower median time per question.
   6. If still tied: the simpler config (fewer changes from A0).
**Addendum (after I1/I2 dev runs, still before any test run):** a third improvement, **I3** (I2 + later searches return only unseen chunks), was added after I1/I2 showed that rewording alone could not reach d07's gold chunk (it sat at rank 4-9 under the same three chunks for every wording). The criteria above were applied to A0, A1, I1, I2, I3 unchanged. Result: see `results/frozen_config.json` (I3 chosen on tie-break 3).

4. **Test protocol:** after selection, freeze the config (record it in `results/frozen_config.json`), then run **A0 (baseline)** and **the chosen config** on test once each with `--confirm-frozen`. No changes after seeing test results.
