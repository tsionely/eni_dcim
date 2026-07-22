# Pooled collision geometry — race-week fixtures (engineering notes)

Scope: `C:\Users\tsion\Projects\eni_dcim\fixtures` — series r1, r1-alt, r1b, r1c, r1d, r1e, r1f (56 fixtures).
Conversion: last detection `rel_pose` → `true_world_dz` (`aigp.planning.approach`, PYTHONPATH=src). `+true_world_dz` = gate below aircraft (we are HIGH).

## Grinding timeouts (separate class)

- **r1c-B-run4**: 18551 collision events, env_hits=18551, abort=`flight timeout`, duration=120.00025729998015s, threat_levels={1: 18551}, impulse p50/p95/max=0.09536376595497131/0.12106698751449585/0.856329619884491, collision_ids=[1002]
- **r1f-B-run8**: 18661 collision events, env_hits=18661, abort=`flight timeout`, duration=120.00399050000124s, threat_levels={1: 18661}, impulse p50/p95/max=0.09427504986524582/0.12132567912340164/0.708536684513092, collision_ids=[1002]

Both are sustained **environment** scrapes at `threat_level=1` (below the abort threshold of 2), so Safety never trips — the wall-clock / max-duration timeout ends the flight. They are NOT gate-clip budgets and NOT single hard impacts.

Sampled grinding hit_class histogram: `{'env_NEAR_gate_LATERAL_likely_pillar_or_side_struct': 1, 'env_NO_GATE_IN_VIEW': 42, 'env_FAR_STRUCTURE_or_hangar': 2}`
Sampled range_z median/min/max: 24.761733847876474 / 3.8573521716479875 / 29.55739532785364
Sampled true_world_dz median: -11.910749146729257; phases={'approach': 1, 'recover': 43, 'search': 1}

## Aborting collisions — hit class cluster

One row per flight: the last collision at/before FSM `ABORTED` (excludes grinding timeouts).

| label | kind | phase | impulse | range_z | true_dz | center_xy | gate# | hit_class | abort |
|---|---|---|---:|---:|---:|---|---:|---|---|
| r1-A-run1 | gate | recover | 0.023258432745933533 | None | None | [None,None] | 0 | `gate_OPENING_or_UNSPECIFIED` | gate clip budget exceeded (11) |
| r1-A-run2 | environment | search | 2.3435258865356445 | 15.825019632934486 | 10.815282315132913 | [195.77450079787747,335.79184451266843] | 0 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=2.0) |
| r1-A-run3 | gate | recover | 0.07961777597665787 | 0.6634260446562944 | 0.49947954253207877 | [333.66979173618773,469.8427859354623] | 0 | `gate_TOP_bar` | gate clip budget exceeded (11) |
| r1-A-run4 | environment | recover | 4.991565227508545 | 4.587371299614336 | 1.0632671093266717 | [276.6535249970589,169.7920985753282] | 0 | `env_NEAR_STRUCTURE_unspecified` | environment collision (impulse=5.0) |
| r1-A-run5 | environment | search | 1.3023239374160767 | None | None | [None,None] | 0 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=1.3) |
| r1-B-run6 | environment | search | 6.265804767608643 | None | None | [None,None] | 0 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=6.3) |
| r1-B-run7 | environment | recover | 3.89359712600708 | 0.7906557342243864 | -0.2903038769135362 | [309.75,149.5] | 0 | `env_NEAR_STRUCTURE_unspecified` | environment collision (impulse=13.4) |
| r1-B-run8 | environment | recover | 0.05232176184654236 | 0.5030858445976215 | -0.37200404314200236 | [319.5,112.25] | 0 | `env_NEAR_STRUCTURE_unspecified` | environment collision (impulse=1.0) |
| r1-B-run9 | environment | search | 1.7076070308685303 | None | None | [None,None] | 0 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=1.7) |
| r1-B-run10 | environment | search | 5.618348121643066 | None | None | [None,None] | 0 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=5.6) |
| r1-alt-A-run1 | environment | search | 2.673454761505127 | 3.1080568979852785 | 1.712018418142849 | [1227.8661420580531,184.5222065991496] | 0 | `env_NEAR_gate_HIGH_likely_banner_or_top_environs` | environment collision (impulse=2.7) |
| r1-alt-B-run2 | environment | commit | 4.101321697235107 | 1.068456321604083 | 0.1282118467263892 | [-265.43958120132277,-313.7113779225029] | 1 | `env_NEAR_gate_LATERAL_likely_pillar_or_side_struct` | environment collision (impulse=4.1) |
| r1-alt-A-run3 | environment | recover | 1.930890440940857 | 19.761599382175593 | -1.116610101660295 | [330.0,313.5] | 0 | `env_FAR_STRUCTURE_or_hangar` | environment collision (impulse=1.9) |
| r1-alt-B-run4 | environment | search | 3.3880374431610107 | None | None | [None,None] | 0 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=3.4) |
| r1-alt-A-run5 | environment | search | 4.844047546386719 | 10.60212073306525 | 0.010778934110003163 | [175.38205270238115,279.5661919319633] | 1 | `env_MID_STRUCTURE_intergate` | environment collision (impulse=4.8) |
| r1-alt-B-run6 | environment | recover | 3.9137213230133057 | None | None | [None,None] | 0 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=2.0) |
| r1-alt-A-run7 | environment | recover | 1.4330722093582153 | 1.7119464917255394 | 1.8943958125811164 | [273.0608648070546,509.95908698957794] | 0 | `env_NEAR_gate_HIGH_likely_banner_or_top_environs` | environment collision (impulse=1.4) |
| r1-alt-B-run8 | environment | search | 1.4551098346710205 | 6.501332531161974 | -1.3301967340615541 | [458.0,258.25] | 0 | `env_MID_STRUCTURE_intergate` | environment collision (impulse=1.5) |
| r1-alt-A-run9 | environment | approach | 6.4048686027526855 | 1.753519614057446 | -1.5434171496801052 | [112.5,108.25] | 0 | `env_NEAR_gate_LOW_likely_floor_or_bottom` | environment collision (impulse=6.4) |
| r1-alt-B-run10 | environment | recover | 1.9548451900482178 | 12.118049339372954 | 5.004981590873928 | [138.02282820113302,160.74280899418738] | 1 | `env_FAR_STRUCTURE_or_hangar` | environment collision (impulse=2.0) |
| r1b-A-run1 | environment | recover | 3.211886167526245 | None | None | [None,None] | 0 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=3.2) |
| r1b-B-run2 | environment | recover | 2.7334887981414795 | None | None | [None,None] | 0 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=2.7) |
| r1b-A-run3 | environment | align | 5.083582878112793 | 0.6656686016560388 | -0.6323004935125119 | [399.5,101.0] | 0 | `env_NEAR_gate_LOW_likely_floor_or_bottom` | environment collision (impulse=5.1) |
| r1b-B-run4 | environment | approach | 8.838188171386719 | 2.4192259726494614 | -1.3118413524921848 | [327.0514088955457,-171.64907849351] | 0 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=8.8) |
| r1b-A-run5 | gate | recover | 0.07601366192102432 | None | None | [None,None] | 0 | `gate_OPENING_or_UNSPECIFIED` | gate clip budget exceeded (11) |
| r1b-B-run6 | environment | recover | 4.206220626831055 | 21.584775623706555 | 10.465084823555983 | [354.6115015808754,197.38686868571298] | 0 | `env_FAR_STRUCTURE_or_hangar` | environment collision (impulse=4.2) |
| r1b-A-run7 | environment | commit | 1.2074652910232544 | 2.47369720579649 | 0.03374481909425908 | [114.03997392445709,-388.1992986596621] | 0 | `env_NEAR_STRUCTURE_unspecified` | environment collision (impulse=1.2) |
| r1b-B-run8 | environment | search | 8.568672180175781 | None | None | [None,None] | 0 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=8.6) |
| r1b-A-run9 | environment | retreat | 3.5206756591796875 | 2.7034756635399453 | -1.0309792914297333 | [289.25,157.0] | 0 | `env_NEAR_gate_LOW_likely_floor_or_bottom` | environment collision (impulse=3.5) |
| r1b-B-run10 | environment | approach | 1.1686694622039795 | 20.568759365208166 | -9.788736339229876 | [211.75,324.5] | 0 | `env_FAR_STRUCTURE_or_hangar` | environment collision (impulse=1.2) |
| r1c-A-run1 | gate | recover | 0.005622840020805597 | 1.2319559007357201 | 0.46480144285215685 | [196.0,165.75] | 0 | `gate_TOP_bar` | gate clip budget exceeded (11) |
| r1c-B-run2 | environment | align | 6.316865921020508 | 0.8038966124582876 | -0.7415162009521152 | [455.25679881459354,88.40172818349065] | 0 | `env_NEAR_gate_LOW_likely_floor_or_bottom` | environment collision (impulse=6.3) |
| r1c-A-run3 | environment | recover | 1.6686608791351318 | None | None | [None,None] | 0 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=1.7) |
| r1c-A-run5 | environment | search | 1.0779671669006348 | None | None | [None,None] | 1 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=1.1) |
| r1c-B-run6 | environment | recover | 1.29123854637146 | 0.646660458393091 | -0.3461946343864155 | [320.25,75.25] | 0 | `env_NEAR_STRUCTURE_unspecified` | environment collision (impulse=1.3) |
| r1d-B-run1 | environment | recover | 1.3160514831542969 | 1.622857841798215 | -0.26298895231525843 | [509.8731002807617,228.86407279968262] | 0 | `env_NEAR_STRUCTURE_unspecified` | environment collision (impulse=1.3) |
| r1d-B-run2 | environment | commit | 8.551071166992188 | 1.6424564576959544 | -1.9684338457149742 | [457.2040481567383,57.8431396484375] | 0 | `env_NEAR_gate_LOW_likely_floor_or_bottom` | environment collision (impulse=8.6) |
| r1d-B-run3 | gate | recover | 0.08089068531990051 | 5.448058703873071 | 5.569445959295401 | [157.9365868725858,302.55889975528237] | 0 | `gate_TOP_bar` | gate clip budget exceeded (11) |
| r1d-B-run4 | environment | recover | 11.804844856262207 | 0.49112038463799856 | -0.1727856572389036 | [325.472246750697,-348.2206500592454] | 1 | `env_NEAR_STRUCTURE_unspecified` | environment collision (impulse=11.8) |
| r1d-B-run5 | environment | commit | 3.5826220512390137 | 3.2808950240009565 | 0.2673636485271407 | [279.0,210.0] | 0 | `env_NEAR_STRUCTURE_unspecified` | environment collision (impulse=3.6) |
| r1e-B-run1 | environment | recover | 1.3737475872039795 | 4.228448336879979 | -0.2484946370741461 | [311.25,211.5] | 0 | `env_NEAR_STRUCTURE_unspecified` | environment collision (impulse=1.4) |
| r1e-B-run2 | environment | search | 11.05701732635498 | None | None | [None,None] | 0 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=11.1) |
| r1e-B-run3 | gate | recover | 0.03172812610864639 | 0.5054484820694813 | -0.49251632445611915 | [319.5,122.5] | 0 | `gate_BOTTOM_bar` | gate clip budget exceeded (11) |
| r1e-B-run4 | environment | recover | 1.6115951538085938 | None | None | [None,None] | 0 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=1.6) |
| r1e-B-run5 | environment | search | 1.0191057920455933 | 19.792836371631203 | -1.6606244464373263 | [67.4522291244214,161.77287250716745] | 0 | `env_FAR_STRUCTURE_or_hangar` | environment collision (impulse=1.0) |
| r1f-A-run1 | environment | approach | 9.561712265014648 | 0.481998375160221 | -0.6400082219855645 | [345.75,95.25] | 0 | `env_NEAR_gate_LOW_likely_floor_or_bottom` | environment collision (impulse=9.6) |
| r1f-B-run2 | environment | search | 4.2374491691589355 | 36.47008298965901 | 9.739252999150676 | [500.0,351.75] | 0 | `env_FAR_STRUCTURE_or_hangar` | environment collision (impulse=4.2) |
| r1f-A-run3 | environment | search | 3.6659231185913086 | None | None | [None,None] | 0 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=3.7) |
| r1f-B-run4 | environment | approach | 2.2782599925994873 | -0.5476025780760788 | 0.16811957592875812 | [752.7311776364601,792.54202422868] | 0 | `env_NEAR_gate_LATERAL_likely_pillar_or_side_struct` | environment collision (impulse=2.3) |
| r1f-A-run5 | gate | recover | 0.07986031472682953 | 1.2316713642893429 | 0.2007935652360338 | [449.5,179.5] | 0 | `gate_OPENING_or_UNSPECIFIED` | gate clip budget exceeded (11) |
| r1f-B-run6 | environment | commit | 7.2914252281188965 | 0.9186207602623634 | 0.2199433071032565 | [422.0,94.25] | 0 | `env_NEAR_STRUCTURE_unspecified` | environment collision (impulse=7.3) |
| r1f-A-run7 | environment | search | 1.5399420261383057 | None | None | [None,None] | 0 | `env_NO_GATE_IN_VIEW` | environment collision (impulse=1.5) |
| r1f-A-run9 | gate | recover | 0.13244351744651794 | 0.5656608805395708 | 0.33121816792082215 | [319.65775716607226,154.12164960902425] | 0 | `gate_OPENING_or_UNSPECIFIED` | gate clip budget exceeded (11) |
| r1f-B-run10 | environment | approach | 7.339892387390137 | 8.07283617254283 | -1.446467047800736 | [170.64813295835287,253.5888832612128] | 0 | `env_MID_STRUCTURE_intergate` | environment collision (impulse=7.3) |

Abort hit_class counts: `{'gate_OPENING_or_UNSPECIFIED': 4, 'env_NO_GATE_IN_VIEW': 17, 'gate_TOP_bar': 3, 'env_NEAR_STRUCTURE_unspecified': 10, 'env_NEAR_gate_HIGH_likely_banner_or_top_environs': 2, 'env_NEAR_gate_LATERAL_likely_pillar_or_side_struct': 2, 'env_FAR_STRUCTURE_or_hangar': 6, 'env_MID_STRUCTURE_intergate': 3, 'env_NEAR_gate_LOW_likely_floor_or_bottom': 6, 'gate_BOTTOM_bar': 1}`

## Interpretation (engineering)

- **Gate clips (1001):** classify by true-world vertical + image row. Positive `true_world_dz` + high image (small y) → TOP bar / banner; negative → BOTTOM bar; extreme u / center_x → SIDE.
- **Env hits (1002) with a near gate in view:** often inter-gate structure (pillar / parked aircraft / hangar steel) while still locked or recently locked; far range → hangar/far structure.
- **Env with no detection:** blind contact — strongest signal of obstacle outside the perception FOV during search/recover.
- **Grinding class (r1c-B4, r1f-B8):** continuous threat-1 env contacts; geometry from samples says what they were pressed against while the timeout clock ran.

## Deliverables

- `collision_events.csv` — all mined collision rows (+ grinding samples)
- `abort_collisions.csv` — killing hit per non-grinding flight
- `flight_summaries.csv`
- `summary.json`

