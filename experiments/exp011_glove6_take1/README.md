# exp011_glove6_take1 (failed; superseded by exp012_glove6_take1)

glove6 take 1 with the configuration of exp010 (DA2 + Bsession vs DA3 metric + K, Bnet). The run
stopped in its first GPU step: `sam3_v2` raised `ep00: no frame with a ball pose to prompt from`.
ep00 is the take's 1.8 s false start (noted in `data/raw/README.md`). Its 180 frames have no ball
pose and no tile pose. Every other episode has ball poses in 50-91% of its frames.

The framework refuses a changed config for an experiment that has already run. The same
configuration without ep00 is therefore `exp012_glove6_take1`. `run.json` here is the record of the
failed attempt.
