"""Require immutable action refs; Dependabot maintains version updates."""
import pathlib
import re
import sys

errors = []
for path in sorted(pathlib.Path('.github/workflows').glob('*.y*ml')):
    for number, line in enumerate(path.read_text().splitlines(), 1):
        match = re.match(r"\s*(?:-\s*)?uses:\s*[\"']?([^\s\"'#]+)", line)
        if not match or match[1].startswith('./'):
            continue
        action = match[1]
        if action.startswith('docker://'):
            valid = bool(re.search(r'@sha256:[0-9a-f]{64}$', action))
        else:
            valid = bool(re.search(r'@[0-9a-f]{40}$', action))
        if not valid:
            errors.append(f'{path}:{number}: unpinned action: {action}')
if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
print('All external actions are pinned to immutable revisions.')
