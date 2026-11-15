# Evidence Sheet E10

- Censoring: t_end 210.103 rel-s, reason stop_flag
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=9 max residual 0.08 s
- Outcome fields (frozen, copied): {"censor_reason": "stop_flag", "source": "[O] batch5/agg_b5.json gridlock.tasks_completed, gridlock.gt_end_rel_s; censor [P] batch6/s1_scoring_pilots.jsonl", "t_end_rel": 210.1, "tasks_completed": 1, "tasks_total": 25}

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_3 | 28.303 | 210.103 | False | 63f8d1ce:robot_1:backup | - |
| FU2 | conflict | robot_2, robot_4, robot_5 | 67.003 | 210.103 | False | 63f8d1ce:robot_5:escort, 63f8d1ce:robot_5:wait, d5541ff0:robot_2:reverse | - |

### FU1

- Pairs: [['robot_1', 'robot_3']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 13.7 rel-s
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_3'], 'close_and_stopped_from_rel': 28.6, 'until_rel': 210.1}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 56.3, 'to_rel': 210.1, 'duration_s': 153.8, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_3', 'from_rel': 27.8, 'to_rel': 210.1, 'duration_s': 182.3, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 11.404 | safety_stop_span | robot_1 | to 17.05 (1361 lines) |
| 13.5 | gt_submargin | robot_3|box:obstacle_1 | to 14.2 min gap 0.046 m |
| 13.7 | analysis | 63f8d1ce9b56455a980765427f04500d | positive strategy=yield involved=['robot_1', 'robot_5'] yield=robot_5 |
| 13.7 | dispatched | 63f8d1ce9b56455a980765427f04500d | robot_1:yield, robot_5:temporary_wait |
| 16.733 | m4_leg_start | 63f8d1ce:robot_1:backup | backup commanded=1.408 |
| 17.051 | exempt_change | - | robot_1+robot_5 |
| 27.869 | safety_stop_span | robot_3 | to 226.541 (48000 lines) |
| 27.871 | safety_stop_span | robot_1 | to 226.541 (48000 lines) |
| 56.272 | m4_terminal | 63f8d1ce:robot_1:backup | FAILED  moved=1.023 tags=['stalled_clear(no robot or box within 0.05 m)'] deadline=True |
| 61.528 | exempt_change | - | robot_1+robot_2,robot_2+robot_3 |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 28.333 | U:T1_fidelity / episode_gate_pass | 6/88 | 6/88 | 6/88 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |

### FU2

- Pairs: [['robot_2', 'robot_4'], ['robot_4', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 13.7 rel-s
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 68.8, 'until_rel': 210.1}, {'pair': ['robot_4', 'robot_5'], 'close_and_stopped_from_rel': 100.7, 'until_rel': 210.1}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_2', 'from_rel': 98.0, 'to_rel': 210.1, 'duration_s': 112.1, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_4', 'from_rel': 68.7, 'to_rel': 210.1, 'duration_s': 141.4, 'to_censor': True, 'safety_stop_cover_fraction': 0.999}, {'robot': 'robot_5', 'from_rel': 100.5, 'to_rel': 210.1, 'duration_s': 109.6, 'to_censor': True, 'safety_stop_cover_fraction': 0.978}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_2|box:obstacle_2: [66.5, 210.1] -0.0014

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 11.397 | safety_stop_span | robot_5 | to 17.05 (1361 lines) |
| 13.7 | analysis | 63f8d1ce9b56455a980765427f04500d | positive strategy=yield involved=['robot_1', 'robot_5'] yield=robot_5 |
| 13.7 | dispatched | 63f8d1ce9b56455a980765427f04500d | robot_1:yield, robot_5:temporary_wait |
| 14.133 | m1_stale | robot_5 | STALE 0.6 s |
| 17.051 | exempt_change | - | robot_1+robot_5 |
| 19.696 | safety_stop_span | robot_4 | to 62.951 (10553 lines) |
| 19.708 | safety_stop_span | robot_2 | to 61.523 (10206 lines) |
| 21.667 | m1_stale | robot_4 | STALE 1.63 s |
| 60.067 | analysis | d5541ff049c3407b975a81835c246aa8 | positive strategy=reverse involved=['robot_2', 'robot_4'] yield=None |
| 60.067 | dispatched | d5541ff049c3407b975a81835c246aa8 | robot_2:reverse |
| 61.5 | m4_leg_start | d5541ff0:robot_2:reverse | reverse commanded=1.3 |
| 61.528 | exempt_change | - | robot_1+robot_2,robot_2+robot_3 |
| 62.7 | gt_submargin | robot_5|box:obstacle_1 | to 63.8 min gap 0.0301 m |
| 66.5 | gt_contact | robot_2|box:obstacle_2 | to 210.1 min gap -0.0014 m |
| 67.233 | safety_stop_span | robot_4 | to 67.575 (13 lines) |
| 67.235 | safety_stop_span | robot_2 | to 67.576 (13 lines) |
| 68.874 | safety_stop_span | robot_4 | to 226.541 (38010 lines) |
| 68.877 | safety_stop_span | robot_2 | to 226.541 (38010 lines) |
| 97.918 | m4_terminal | d5541ff0:robot_2:reverse | FAILED  moved=0.596 tags=['not_executed(<50%)', 'pinned_on_declared_box:obstacle_2'] deadline=True |
| 102.941 | safety_stop_span | robot_5 | to 226.541 (29756 lines) |
| 102.944 | nav2 | robot_5 | [follow_path] [ActionServer] Aborting handle. |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 67.433 | U:T1_fidelity / episode_gate_pass | 72/237 | 72/237 | 72/237 | True | {'robot': 'robot_4', 'heading_deg': 0, 'distance_m': 0.01} |

## Decisions

### 63f8d1ce9b56455a980765427f04500d at 13.7 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_5'], yield_robot robot_5, crossing_order ['robot_1', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Robot 5 is moving but blocked by Robot 1, which is stopped close to its goal; having Robot 5 yield and back up or step aside allows Robot 1 to clear the narrow passage.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_5'], 'yield_robot': 'robot_5'}}
- Plan verifier: provenance repaired, edits [{'op': 'swap', 'reason': 'yield re-grounded: dispatch yields robot_1, not robot_5 (grounding=node_handoff_regrounded:robot_5->robot_1); swapped roles robot_5 (yield) <-> robot_1 (cross)', 'robot_ids': ['robot_1', 'robot_5']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=node_handoff:robot_1->robot_5', 'grounding=node_handoff_regrounded:robot_5->robot_1', 'grounding=dynamic_arms:lane:x', 'grounding=escort_turn_cap:robot_5:2.35->1.823']
- Actions: [('robot_1', 'yield', {'backup_distance_m': 1.408, 'crossing_order': ['robot_5'], 'passer_escort_distance_m': 1.823, 'passer_robot_id': 'robot_5', 'reason': 'Robot 1 and Robot 5 are in a head-on standoff in a narrow corridor.', 'retreat_choice': 'B'}), ('robot_5', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_1->robot_5', 'grounding=node_handoff_regrounded:robot_5->robot_1'], 'G6_verbatim_contradicted': False}

### d5541ff049c3407b975a81835c246aa8 at 60.067 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_2', 'robot_4'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Both robots 2 and 4 must back straight out along their lanes to resolve the local deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': False, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_2', 'robot_4'], 'involved': ['robot_2', 'robot_4']}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=node_handoff:robot_2->robot_4']
- Actions: [('robot_2', 'reverse', {'backup_distance_m': 1.3})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_2->robot_4'], 'G6_verbatim_contradicted': True, 'G4_robots_dropped': ['robot_4']}

### 3a70abe261d64bccb7fed17613de20c4 at 99.2 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### bbf6c51d73784d9c84b4013f5c7eecc1 at 101.867 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 947ddb112b594c0d94f29a482ab3e1ae at 104.8 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 772bdb6feafc47bfacdb6ef1dd39664d at 107.7 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 4c056f53069c4797a88851b75a24d641 at 110.633 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### affb04b24c664e0ca9f6280ef674a402 at 113.5 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### c2696af6f45b4bf49e5efe61fabed9cb at 116.367 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### c56a595b56b149f485079c25c267fe0f at 119.367 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### e34cdc3271b74208b4964a12b5cd645e at 122.367 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 606ce9d35b6941a094085cfac4d982e7 at 125.267 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 6dd737b0828a4afba54bb2a1a32579e4 at 128.533 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 6e08e9e5c74845df9a344bd96e0f19e2 at 131.467 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 45059268f4a84d0ba93bfb3ea1c2c437 at 134.367 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### bbe5a21cb64e49ab853486e89ba143b0 at 137.567 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 5d0d2b5aa7cd4addae02db3c8a3decf3 at 140.533 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 628540fccfe544f6ac2cf586b47d6ca0 at 143.7 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### c4d1a2fe4d7840529969fec5895dc0b9 at 146.533 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 7e63295eaac04eaba71671d0fab80d45 at 149.467 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### e5ca9f213d7b4e4397f00ce4d67cf316 at 152.333 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 6b4ef7d7054b41faa721918e0f6df841 at 155.167 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### d234e0954960456e8ebc7dda5484d16e at 158.033 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### db80646c286c44dcb9b6261694b52065 at 160.867 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 8ae5d739dbd949a684758b0a2df959f2 at 163.733 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 2ceeb0718454479b8d6707d518e3a384 at 166.5 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### b7e96ad3167d4023864ace9ac6f47e55 at 169.333 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### bb3c2090177742658b89c35d79705da2 at 172.167 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### e9a14b362ec248f6adc16fe3c7bcda96 at 174.867 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### a281052ab33f455884fc67e6a38adc24 at 177.867 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 408ee8a2b0ac401eb80949d4dc2f0972 at 181.133 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 6897dc8f987544358998b4b9cfececa3 at 183.9 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 0ebfeae82b3c49fdac3019a752e65fae at 186.867 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 7e1a2be063784114ab720a6305a0c736 at 190.033 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### dc226a66cfc446fb8b9b5416d18e78b5 at 193.1 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### d539b7a4a6f54cefa275e688b6238da5 at 196.233 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 1d77133378a04d5d83c859019d56297b at 199.133 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 51711e952137461990dab19bce2d18bd at 202.067 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### be869cad9d4c40a7a45f087c0a526008 at 204.933 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### c746b92ca4584235a2d7defef68db80d at 207.9 rel-s (backend_failed)

- Parse: failed, attempts 1, refusal None, error ConnectionError, decision degradations [], terminal stage vlm
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 63f8d1ce:robot_1:backup | backup | 1.408 | 13.7 | 16.733 | 56.272 | FAILED | 1.023 | 0.726 | 0.3041 (obstacle_1) | None (None) | stalled_clear(no robot or box within 0.05 m) | True |
| 63f8d1ce:robot_5:escort | escort | 1.823 | 13.7 | None | None | None | None | None | None (None) | None (None) | escort_not_admitted (no gate_admit line) | False |
| d5541ff0:robot_2:reverse | reverse | 1.3 | 60.067 | 61.5 | 97.918 | FAILED | 0.596 | 0.458 | -0.0014 (obstacle_2) | None (None) | not_executed(<50%); pinned_on_declared_box:obstacle_2 | True |

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

- robot_5 102.944 rel-s: [follow_path] [ActionServer] Aborting handle.

## Safety Latch

- Exempt changes: [{'rel': 17.051, 'pairs': 'robot_1+robot_5'}, {'rel': 56.279, 'pairs': '-'}, {'rel': 61.528, 'pairs': 'robot_1+robot_2,robot_2+robot_3'}, {'rel': 97.97, 'pairs': '-'}]
- Safety-stop spans: robot_5|min_distance_violation: 2 spans; robot_1|min_distance_violation: 2 spans; robot_4|min_distance_violation: 3 spans; robot_2|min_distance_violation: 3 spans; robot_3|min_distance_violation: 1 spans
