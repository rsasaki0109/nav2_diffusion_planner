# Model Card: <model_name>

> Copy this template to `model_zoo/<model_name>.md` (or alongside the artifact)
> and fill every section. A model is not accepted into the Model Zoo without a
> completed card and a passing benchmark run (docs/architecture.md section 5.5).

## Summary

- **Model family:** diffusion / flow / consistency / transformer / world_model
- **Task:** local trajectory proposal for Nav2 Controller (Mode A) / Planner (Mode B)
- **Robot kinematics:** diff / omni / ackermann / generic
- **Inputs:** e.g. local costmap, odometry, global path snippet, local goal (camera optional)
- **Output:** trajectory candidates / subgoals / velocity sequence
- **Runtime / precision:** onnx fp16 / tensorrt int8 / pytorch fp32
- **Manifest:** link to the `*.yaml` manifest (section 5.4)

## Intended use

What scenarios and robots this model is for (ODD: indoor/outdoor, floor type, max
speed, sensor suite, human density, lighting).

## Out-of-scope / limitations

Conditions under which the model must NOT be used. Be specific and honest — these
become runtime guards and reviewer expectations.

## Training data

Datasets, sim/real split, robot types, how labels were generated, known biases.

## Benchmark results

Reference the benchmark suite version and report the headline metrics
(docs/benchmarking.md sections 9.4 and 9.6): success rate, collisions,
min clearance, time/path efficiency, smoothness, latency p95/p99, and the
safety-first overall score. Compare against MPPI / RPP baselines on the same
scenarios (default and tuned).

## Safety

- Safety-gate rejection rate and fallback rate observed in evaluation.
- Failure cases (include the ones that look bad — section 14).
- Hardware EStop / ODD assumptions for real-robot use.

## Reproducibility

Seeds, config files, commit hash, and how to re-run the evaluation.

## License

Model / data / code licenses, stated separately.
