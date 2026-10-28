# backend/services/tour_generator_legacy.py

[Source](../../../../../backend/services/tour_generator_legacy.py)

Legacy Tour Generator - ARCHIVED (Not for Production Use) =========================================================

| Symbol | Kind | Source line |
|---|---|---|
| `rand` | FunctionDef | [L46](../../../../../backend/services/tour_generator_legacy.py#L46) |
| `rand_int` | FunctionDef | [L51](../../../../../backend/services/tour_generator_legacy.py#L51) |
| `rand_choice` | FunctionDef | [L56](../../../../../backend/services/tour_generator_legacy.py#L56) |
| `normalize_angle` | FunctionDef | [L61](../../../../../backend/services/tour_generator_legacy.py#L61) |
| `Keyframe` | ClassDef | [L75](../../../../../backend/services/tour_generator_legacy.py#L75) |
| `TourProgram` | ClassDef | [L83](../../../../../backend/services/tour_generator_legacy.py#L83) |
| `Camera` | ClassDef | [L94](../../../../../backend/services/tour_generator_legacy.py#L94) |
| `Camera.__init__` | FunctionDef | [L100](../../../../../backend/services/tour_generator_legacy.py#L100) |
| `Camera.reset` | FunctionDef | [L107](../../../../../backend/services/tour_generator_legacy.py#L107) |
| `Camera.state` | FunctionDef | [L115](../../../../../backend/services/tour_generator_legacy.py#L115) |
| `Camera.mark` | FunctionDef | [L119](../../../../../backend/services/tour_generator_legacy.py#L119) |
| `Camera.move_to` | FunctionDef | [L128](../../../../../backend/services/tour_generator_legacy.py#L128) |
| `Camera.hold` | FunctionDef | [L175](../../../../../backend/services/tour_generator_legacy.py#L175) |
| `Camera.get_program` | FunctionDef | [L184](../../../../../backend/services/tour_generator_legacy.py#L184) |
| `Motion` | ClassDef | [L202](../../../../../backend/services/tour_generator_legacy.py#L202) |
| `Motion.survey` | FunctionDef | [L209](../../../../../backend/services/tour_generator_legacy.py#L209) |
| `Motion.glance` | FunctionDef | [L216](../../../../../backend/services/tour_generator_legacy.py#L216) |
| `Motion.examine` | FunctionDef | [L224](../../../../../backend/services/tour_generator_legacy.py#L224) |
| `Motion.skyward` | FunctionDef | [L234](../../../../../backend/services/tour_generator_legacy.py#L234) |
| `Motion.groundward` | FunctionDef | [L242](../../../../../backend/services/tour_generator_legacy.py#L242) |
| `Motion.staged_turn` | FunctionDef | [L250](../../../../../backend/services/tour_generator_legacy.py#L250) |
| `Motion.discover` | FunctionDef | [L257](../../../../../backend/services/tour_generator_legacy.py#L257) |
| `Motion.breathe` | FunctionDef | [L263](../../../../../backend/services/tour_generator_legacy.py#L263) |
| `Motion.settle` | FunctionDef | [L274](../../../../../backend/services/tour_generator_legacy.py#L274) |
| `_reset_direction` | FunctionDef | [L287](../../../../../backend/services/tour_generator_legacy.py#L287) |
| `_update_direction` | FunctionDef | [L292](../../../../../backend/services/tour_generator_legacy.py#L292) |
| `establish_scene` | FunctionDef | [L301](../../../../../backend/services/tour_generator_legacy.py#L301) |
| `generate_creative_sequence` | FunctionDef | [L377](../../../../../backend/services/tour_generator_legacy.py#L377) |
| `execute_beat` | FunctionDef | [L425](../../../../../backend/services/tour_generator_legacy.py#L425) |
| `generate_tour` | FunctionDef | [L525](../../../../../backend/services/tour_generator_legacy.py#L525) |
| `generate_nearby_place_tour` | FunctionDef | [L578](../../../../../backend/services/tour_generator_legacy.py#L578) |
| `get_realtime_sway` | FunctionDef | [L617](../../../../../backend/services/tour_generator_legacy.py#L617) |
| `keyframes_to_tile_sequence` | FunctionDef | [L665](../../../../../backend/services/tour_generator_legacy.py#L665) |
| `program_to_dict` | FunctionDef | [L693](../../../../../backend/services/tour_generator_legacy.py#L693) |
| `dict_to_program` | FunctionDef | [L711](../../../../../backend/services/tour_generator_legacy.py#L711) |
