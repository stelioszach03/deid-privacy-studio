# External synthetic evaluation

This directory contains the fixed evaluation protocol, with [executed results](../../artifacts/external-synthetic-v1-run1/REPORT.md) stored separately from the library's unit fixtures. The detector was unchanged during the evaluation. Results include weak categories and unsupported-label coverage; no accuracy improvement or clinical claim is made.

The protocol, sample and source hashes were recorded locally before execution;
public repository publication followed the run. This is not an external
preregistration or an independently timestamped study registration.

## Reproduce

Use Python 3.11 and a separate environment:

```sh
python3.11 -m venv .venv
.venv/bin/pip install -r requirements-external-eval.lock
mkdir -p /tmp/deid-external
curl --fail --location 'https://raw.githubusercontent.com/data-privacy-stack/presidio-research/6db3769a3388b4075b93ab2229c5e0b9c30137f7/data/synth_dataset_v2.json' --output /tmp/deid-external/dataset.json
.venv/bin/python scripts/evaluate_external.py --dataset /tmp/deid-external/dataset.json --run artifacts/external-synthetic-v1-run1/protocol.json --output /tmp/deid-external/new-run
.venv/bin/python scripts/report_external.py /tmp/deid-external/new-run
```

The recorded protocol validates the exact evaluator/engine/data hashes. It must be run from the corresponding released source, not a later modified detector. Timings can change across machines. The package/model versions are frozen; results include actual model-file hashes. Loading and execution remain local; downloading the public fixture/model does not transmit the fixture to a model service.

Scorer tests require only Python's standard library:

```sh
python3 -m unittest discover -s tests -p test_external_metrics.py -v
python3 scripts/report_external.py artifacts/external-synthetic-v1-run1
```

The source fixture contains synthetic generated values. Its upstream README includes the separate Fake Name Generator CC BY-SA 3.0 US notice; repository code has MIT terms. No dataset text is committed here. Neither license nor synthetic provenance establishes performance on real patient records.
