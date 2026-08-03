---
name: validate
description: Run the pre-commit validation checks for the Grant Aerona3 integration (Python syntax, strings.json/translations.json JSON validity and parity). Use before committing or opening a PR, since this repo has no CI or test suite.
---

Run these checks from the repo root and report pass/fail for each — don't stop at the first failure, run all of them and summarize:

1. **Python syntax** — compile every module in the integration:
   ```
   python3 -m py_compile custom_components/grant_aerona3/*.py
   ```
   No output means success; a `SyntaxError` traceback points at the bad file/line.

2. **JSON validity** — `strings.json` and `translations/en.json` must both parse:
   ```
   python3 -c "import json; json.load(open('custom_components/grant_aerona3/strings.json')); json.load(open('custom_components/grant_aerona3/translations/en.json')); print('OK')"
   ```

3. **Translations parity** — the two files must have identical keys (Home Assistant loads `translations/en.json` at runtime, not `strings.json`, so they silently drift if only one is edited):
   ```
   diff <(python3 -c "import json,sys; print(json.dumps(json.load(open('custom_components/grant_aerona3/strings.json')), sort_keys=True, indent=2))") \
        <(python3 -c "import json,sys; print(json.dumps(json.load(open('custom_components/grant_aerona3/translations/en.json')), sort_keys=True, indent=2))")
   ```
   Any diff output means the two files have drifted apart — fix by copying the changed section across, not by picking one file arbitrarily (see the root [CLAUDE.md](../../../CLAUDE.md) for which file HA actually reads at runtime).

If a register or hand-written entity was added or changed, also sanity-check the feature-gating conventions in the root `CLAUDE.md` were followed (register listed in the right `*_REGISTER_FEATURES` dict, unique_id suffix added to `FEATURE_UNIQUE_ID_SUFFIXES` if applicable) — this isn't machine-checkable, so review it by eye.
