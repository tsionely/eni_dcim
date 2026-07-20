# Non-contact ledger

Every clean crossing (zero gate clips) with logged dz is a **one-sided** envelope bound:

```
no contact ⇒  h_up < 0.8 − dz
              h_down < 0.8 + dz
```

## Tightest defensible bounds

- **h_up < 0.700** (from `20260716T131137-2ca531c3` dz=+0.100)
- **h_down < 0.719** (from `20260719T200816-f170ead6` dz=-0.081)

Think-tank 4/4 aggregate cite: h_up < 0.79, h_down < 0.71 (grade B_aggregate_cite).

## Provenance table

| flight | fid | dz | h_up < | h_down < | grade | truth source |
|--------|-----|---:|-------:|---------:|:-----:|--------------|
| milestone_first_clean_pass | `20260716T131137-2ca531c3` | +0.100 | 0.700 | 0.900 | A_canonical | miss_map_true_vertical / milestone autopsy (closest STATE crossing vector) |
| phase6h_try15_clean | `20260719T160537-f170ead6` | +0.016 | 0.784 | 0.816 | A_logged | state true_world_dz at closest fresh approach |
| phase6i_slot1_pass | `20260719T200816-f170ead6` | -0.081 | 0.881 | 0.719 | A_logged | state true_world_dz at closest fresh approach |
| phase6i_slot4_pass | `20260719T201851-50f9dcc8` | -0.034 | 0.834 | 0.766 | A_logged | state true_world_dz at closest fresh approach |

## Reading

The milestone pass (+0.100) remains the tightest **upper** archive bound (h_up < 0.70). Lower-tail tightness comes from the most negative clean-crossing dz. Contact-harvest numbers (0.744 / 0.638) are **not** ledger rows — they require clips.

## Deliverables

- `ledger.csv`, `summary.json`, this report
