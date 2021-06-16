# Data review statistics

Powers https://protosaur.dev/data-steward-stats/.

Expects to find a file named `bugzilla_api_key` containing, well, a Bugzilla API key, in its current working directory.

Running this looks something like:

```sh
python render.py
gsutil -q cp result.html gs://data-steward-stats/index.html
```
