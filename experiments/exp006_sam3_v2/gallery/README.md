# glove7 SAM3 v2 Masks

Motion masks on yam_glove7 (30 episode segments, 8,972 frames): SAM2 (exp001) against SAM3 (`sam3_v2`, exp006). Each image overlays both masks on the undistorted head-camera frame:

- green: masked by both;
- cyan: SAM2 only;
- magenta: SAM3 only.

Judge each colour by what the pixels are: everything that moves on its own (hand, arm, glove rig, its cable, a held block) should be masked, and static things should not.

## Mask setups

Both masks are dilated by 8 px before DROID, and masked pixels get zero weight in its bundle adjustment.

- **SAM2** (`facebook/sam2.1-hiera-large`, video propagation): every 30 frames, two objects are prompted with points projected from the ball pose: the glove (ball centre and flange) and the hand (one point on the back of the hand).
- **SAM3** (`facebook/sam3`): the text prompts "hand", "arm" and "cable" give tracked instances. An instance is kept only where it lies within 8 px of the tracked wearer and has not grown to more than 3x its usual size. Every 10 frames, three tracker objects are prompted with points projected from the ball pose: the gripper (ball centre and three points on its body), the hand and forearm (two points), and a held object (a point between the fingertips, used only while the gripper is closed after it was open). The mask is the union of all parts.

## Region audit

In the 60 frames where SAM2 and an earlier SAM3 setup disagreed most, two independent reviewers judged each of the 159 disagreement regions as moving or static and agreed on 154 (97%) (`experiments/audits/2026-11-08_sam3_vs_sam2_regions/`). SAM3's thresholds were tuned on these regions, so the audit favours SAM3.

| measure | SAM2 | SAM3 |
|---|---|---|
| moving regions covered, of 80 (area, % of a frame) | 40 (61%) | 54 (69%) |
| static regions masked, of 74 (area, % of a frame) | 1 (0.2%) | 10 (22%) |
| held block covered, 4 frames | 0–42% | 98–99% |

## All frames

Agreement of SAM3 with SAM2 over all 8,972 frames (agreement, not accuracy): IoU median 0.94 (p10 0.88); on DROID's 1/8 cells median 0.98 (p10 0.89); masked area 7.2% of the frame (SAM2 7.2%).

DROID E3 (motion + tile masks): head rotation error at 1 s, median 0.52 deg with SAM3 and 0.53 deg with SAM2; tracking failure 0.17% and 0.34%.

## Frames

Four frames per segment: two evenly spaced (typical) and the two where SAM3 and SAM2 disagree most (lowest IoU, at least 15 frames apart).

[ep00](#ep00) · [ep01](#ep01) · [ep02](#ep02) · [ep03](#ep03) · [ep04](#ep04) · [ep05](#ep05) · [ep06](#ep06) · [ep07](#ep07) · [ep08](#ep08) · [ep09](#ep09) · [ep10](#ep10) · [ep11](#ep11) · [ep12](#ep12) · [ep13](#ep13) · [ep14](#ep14) · [ep15](#ep15) · [ep16](#ep16) · [ep17](#ep17) · [ep18](#ep18) · [ep19](#ep19) · [ep20](#ep20) · [ep21](#ep21) · [ep22](#ep22) · [ep23](#ep23) · [ep24](#ep24) · [ep25](#ep25) · [ep26](#ep26) · [ep27](#ep27) · [ep28](#ep28) · [ep29](#ep29)

### ep00

![ep00 frame 75](img/ep00_000075.jpg)

ep00, frame 75, typical: IoU 0.92

![ep00 frame 226](img/ep00_000226.jpg)

ep00, frame 226, typical: IoU 0.96

![ep00 frame 180](img/ep00_000180.jpg)

ep00, frame 180, most different: IoU 0.59

![ep00 frame 20](img/ep00_000020.jpg)

ep00, frame 20, most different: IoU 0.63

### ep01

![ep01 frame 74](img/ep01_000074.jpg)

ep01, frame 74, typical: IoU 0.92

![ep01 frame 223](img/ep01_000223.jpg)

ep01, frame 223, typical: IoU 0.96

![ep01 frame 20](img/ep01_000020.jpg)

ep01, frame 20, most different: IoU 0.87

![ep01 frame 38](img/ep01_000038.jpg)

ep01, frame 38, most different: IoU 0.89

### ep02

![ep02 frame 69](img/ep02_000069.jpg)

ep02, frame 69, typical: IoU 0.95

![ep02 frame 208](img/ep02_000208.jpg)

ep02, frame 208, typical: IoU 0.95

![ep02 frame 270](img/ep02_000270.jpg)

ep02, frame 270, most different: IoU 0.90

![ep02 frame 90](img/ep02_000090.jpg)

ep02, frame 90, most different: IoU 0.91

### ep03

![ep03 frame 67](img/ep03_000067.jpg)

ep03, frame 67, typical: IoU 0.94

![ep03 frame 202](img/ep03_000202.jpg)

ep03, frame 202, typical: IoU 0.94

![ep03 frame 234](img/ep03_000234.jpg)

ep03, frame 234, most different: IoU 0.93

![ep03 frame 40](img/ep03_000040.jpg)

ep03, frame 40, most different: IoU 0.93

### ep04

![ep04 frame 78](img/ep04_000078.jpg)

ep04, frame 78, typical: IoU 0.97

![ep04 frame 234](img/ep04_000234.jpg)

ep04, frame 234, typical: IoU 0.97

![ep04 frame 303](img/ep04_000303.jpg)

ep04, frame 303, most different: IoU 0.44

![ep04 frame 270](img/ep04_000270.jpg)

ep04, frame 270, most different: IoU 0.51

### ep05

![ep05 frame 77](img/ep05_000077.jpg)

ep05, frame 77, typical: IoU 0.93

![ep05 frame 232](img/ep05_000232.jpg)

ep05, frame 232, typical: IoU 0.96

![ep05 frame 130](img/ep05_000130.jpg)

ep05, frame 130, most different: IoU 0.83

![ep05 frame 160](img/ep05_000160.jpg)

ep05, frame 160, most different: IoU 0.84

### ep06

![ep06 frame 64](img/ep06_000064.jpg)

ep06, frame 64, typical: IoU 0.92

![ep06 frame 194](img/ep06_000194.jpg)

ep06, frame 194, typical: IoU 0.92

![ep06 frame 240](img/ep06_000240.jpg)

ep06, frame 240, most different: IoU 0.51

![ep06 frame 40](img/ep06_000040.jpg)

ep06, frame 40, most different: IoU 0.61

### ep07

![ep07 frame 65](img/ep07_000065.jpg)

ep07, frame 65, typical: IoU 0.92

![ep07 frame 195](img/ep07_000195.jpg)

ep07, frame 195, typical: IoU 0.95

![ep07 frame 249](img/ep07_000249.jpg)

ep07, frame 249, most different: IoU 0.83

![ep07 frame 150](img/ep07_000150.jpg)

ep07, frame 150, most different: IoU 0.86

### ep08

![ep08 frame 60](img/ep08_000060.jpg)

ep08, frame 60, typical: IoU 0.91

![ep08 frame 182](img/ep08_000182.jpg)

ep08, frame 182, typical: IoU 0.93

![ep08 frame 220](img/ep08_000220.jpg)

ep08, frame 220, most different: IoU 0.55

![ep08 frame 240](img/ep08_000240.jpg)

ep08, frame 240, most different: IoU 0.62

### ep09

![ep09 frame 75](img/ep09_000075.jpg)

ep09, frame 75, typical: IoU 0.93

![ep09 frame 227](img/ep09_000227.jpg)

ep09, frame 227, typical: IoU 0.93

![ep09 frame 300](img/ep09_000300.jpg)

ep09, frame 300, most different: IoU 0.41

![ep09 frame 180](img/ep09_000180.jpg)

ep09, frame 180, most different: IoU 0.45

### ep10

![ep10 frame 80](img/ep10_000080.jpg)

ep10, frame 80, typical: IoU 0.95

![ep10 frame 241](img/ep10_000241.jpg)

ep10, frame 241, typical: IoU 0.96

![ep10 frame 290](img/ep10_000290.jpg)

ep10, frame 290, most different: IoU 0.63

![ep10 frame 305](img/ep10_000305.jpg)

ep10, frame 305, most different: IoU 0.70

### ep11

![ep11 frame 68](img/ep11_000068.jpg)

ep11, frame 68, typical: IoU 0.91

![ep11 frame 204](img/ep11_000204.jpg)

ep11, frame 204, typical: IoU 0.95

![ep11 frame 252](img/ep11_000252.jpg)

ep11, frame 252, most different: IoU 0.64

![ep11 frame 270](img/ep11_000270.jpg)

ep11, frame 270, most different: IoU 0.66

### ep12

![ep12 frame 73](img/ep12_000073.jpg)

ep12, frame 73, typical: IoU 0.89

![ep12 frame 219](img/ep12_000219.jpg)

ep12, frame 219, typical: IoU 0.92

![ep12 frame 166](img/ep12_000166.jpg)

ep12, frame 166, most different: IoU 0.54

![ep12 frame 104](img/ep12_000104.jpg)

ep12, frame 104, most different: IoU 0.61

### ep13

![ep13 frame 70](img/ep13_000070.jpg)

ep13, frame 70, typical: IoU 0.95

![ep13 frame 212](img/ep13_000212.jpg)

ep13, frame 212, typical: IoU 0.96

![ep13 frame 20](img/ep13_000020.jpg)

ep13, frame 20, most different: IoU 0.00

![ep13 frame 270](img/ep13_000270.jpg)

ep13, frame 270, most different: IoU 0.59

### ep14

![ep14 frame 77](img/ep14_000077.jpg)

ep14, frame 77, typical: IoU 0.96

![ep14 frame 231](img/ep14_000231.jpg)

ep14, frame 231, typical: IoU 0.92

![ep14 frame 283](img/ep14_000283.jpg)

ep14, frame 283, most different: IoU 0.31

![ep14 frame 265](img/ep14_000265.jpg)

ep14, frame 265, most different: IoU 0.51

### ep15

![ep15 frame 78](img/ep15_000078.jpg)

ep15, frame 78, typical: IoU 0.93

![ep15 frame 234](img/ep15_000234.jpg)

ep15, frame 234, typical: IoU 0.92

![ep15 frame 270](img/ep15_000270.jpg)

ep15, frame 270, most different: IoU 0.50

![ep15 frame 300](img/ep15_000300.jpg)

ep15, frame 300, most different: IoU 0.72

### ep16

![ep16 frame 77](img/ep16_000077.jpg)

ep16, frame 77, typical: IoU 0.96

![ep16 frame 231](img/ep16_000231.jpg)

ep16, frame 231, typical: IoU 0.97

![ep16 frame 300](img/ep16_000300.jpg)

ep16, frame 300, most different: IoU 0.68

![ep16 frame 169](img/ep16_000169.jpg)

ep16, frame 169, most different: IoU 0.85

### ep17

![ep17 frame 74](img/ep17_000074.jpg)

ep17, frame 74, typical: IoU 0.94

![ep17 frame 223](img/ep17_000223.jpg)

ep17, frame 223, typical: IoU 0.95

![ep17 frame 50](img/ep17_000050.jpg)

ep17, frame 50, most different: IoU 0.21

![ep17 frame 270](img/ep17_000270.jpg)

ep17, frame 270, most different: IoU 0.38

### ep18

![ep18 frame 87](img/ep18_000087.jpg)

ep18, frame 87, typical: IoU 0.95

![ep18 frame 261](img/ep18_000261.jpg)

ep18, frame 261, typical: IoU 0.88

![ep18 frame 330](img/ep18_000330.jpg)

ep18, frame 330, most different: IoU 0.63

![ep18 frame 300](img/ep18_000300.jpg)

ep18, frame 300, most different: IoU 0.83

### ep19

![ep19 frame 73](img/ep19_000073.jpg)

ep19, frame 73, typical: IoU 0.94

![ep19 frame 219](img/ep19_000219.jpg)

ep19, frame 219, typical: IoU 0.95

![ep19 frame 291](img/ep19_000291.jpg)

ep19, frame 291, most different: IoU 0.38

![ep19 frame 271](img/ep19_000271.jpg)

ep19, frame 271, most different: IoU 0.43

### ep20

![ep20 frame 77](img/ep20_000077.jpg)

ep20, frame 77, typical: IoU 0.95

![ep20 frame 233](img/ep20_000233.jpg)

ep20, frame 233, typical: IoU 0.87

![ep20 frame 184](img/ep20_000184.jpg)

ep20, frame 184, most different: IoU 0.47

![ep20 frame 169](img/ep20_000169.jpg)

ep20, frame 169, most different: IoU 0.57

### ep21

![ep21 frame 77](img/ep21_000077.jpg)

ep21, frame 77, typical: IoU 0.84

![ep21 frame 231](img/ep21_000231.jpg)

ep21, frame 231, typical: IoU 0.96

![ep21 frame 60](img/ep21_000060.jpg)

ep21, frame 60, most different: IoU 0.11

![ep21 frame 290](img/ep21_000290.jpg)

ep21, frame 290, most different: IoU 0.47

### ep22

![ep22 frame 84](img/ep22_000084.jpg)

ep22, frame 84, typical: IoU 0.93

![ep22 frame 253](img/ep22_000253.jpg)

ep22, frame 253, typical: IoU 0.93

![ep22 frame 320](img/ep22_000320.jpg)

ep22, frame 320, most different: IoU 0.38

![ep22 frame 337](img/ep22_000337.jpg)

ep22, frame 337, most different: IoU 0.45

### ep23

![ep23 frame 79](img/ep23_000079.jpg)

ep23, frame 79, typical: IoU 0.94

![ep23 frame 237](img/ep23_000237.jpg)

ep23, frame 237, typical: IoU 0.91

![ep23 frame 120](img/ep23_000120.jpg)

ep23, frame 120, most different: IoU 0.73

![ep23 frame 300](img/ep23_000300.jpg)

ep23, frame 300, most different: IoU 0.89

### ep24

![ep24 frame 82](img/ep24_000082.jpg)

ep24, frame 82, typical: IoU 0.93

![ep24 frame 248](img/ep24_000248.jpg)

ep24, frame 248, typical: IoU 0.94

![ep24 frame 8](img/ep24_000008.jpg)

ep24, frame 8, most different: IoU 0.89

![ep24 frame 150](img/ep24_000150.jpg)

ep24, frame 150, most different: IoU 0.89

### ep25

![ep25 frame 73](img/ep25_000073.jpg)

ep25, frame 73, typical: IoU 0.95

![ep25 frame 219](img/ep25_000219.jpg)

ep25, frame 219, typical: IoU 0.95

![ep25 frame 286](img/ep25_000286.jpg)

ep25, frame 286, most different: IoU 0.37

![ep25 frame 120](img/ep25_000120.jpg)

ep25, frame 120, most different: IoU 0.62

### ep26

![ep26 frame 73](img/ep26_000073.jpg)

ep26, frame 73, typical: IoU 0.75

![ep26 frame 220](img/ep26_000220.jpg)

ep26, frame 220, typical: IoU 0.94

![ep26 frame 180](img/ep26_000180.jpg)

ep26, frame 180, most different: IoU 0.69

![ep26 frame 150](img/ep26_000150.jpg)

ep26, frame 150, most different: IoU 0.77

### ep27

![ep27 frame 76](img/ep27_000076.jpg)

ep27, frame 76, typical: IoU 0.95

![ep27 frame 229](img/ep27_000229.jpg)

ep27, frame 229, typical: IoU 0.95

![ep27 frame 262](img/ep27_000262.jpg)

ep27, frame 262, most different: IoU 0.64

![ep27 frame 150](img/ep27_000150.jpg)

ep27, frame 150, most different: IoU 0.90

### ep28

![ep28 frame 76](img/ep28_000076.jpg)

ep28, frame 76, typical: IoU 0.96

![ep28 frame 230](img/ep28_000230.jpg)

ep28, frame 230, typical: IoU 0.95

![ep28 frame 290](img/ep28_000290.jpg)

ep28, frame 290, most different: IoU 0.49

![ep28 frame 306](img/ep28_000306.jpg)

ep28, frame 306, most different: IoU 0.87

### ep29

![ep29 frame 73](img/ep29_000073.jpg)

ep29, frame 73, typical: IoU 0.96

![ep29 frame 220](img/ep29_000220.jpg)

ep29, frame 220, typical: IoU 0.96

![ep29 frame 19](img/ep29_000019.jpg)

ep29, frame 19, most different: IoU 0.49

![ep29 frame 180](img/ep29_000180.jpg)

ep29, frame 180, most different: IoU 0.89

---

Made by `make_gallery.py` from the cached masks (keys sam2 `86471818888012b6`, sam3 `93ead78627ecc88e`).
