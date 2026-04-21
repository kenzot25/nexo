# Troubleshooting

## Install and environment

### `python` command not found
Use `python3` and run:

```bash
make setup
```

### `pytest` missing
Use local environment commands:

```bash
make setup
make t
```

## Doctor failures

### `skill-installed` or `skill-version` fails

```bash
nexo install
nexo doctor
```

### `claude-md` or `pretool-hook` fails

```bash
nexo claude install
nexo doctor
```

## Graph output issues

### No graph found
Run:

```bash
nexo update .
```

### Query returns little context
- Use a more specific question.
- Try `--dfs` mode.
- Increase `--budget`.

## Test workflow

```bash
make t
make r CMD="python -m pytest tests/test_export.py -q"
```
