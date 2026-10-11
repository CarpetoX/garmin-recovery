"""Black-box git publishing regressions, using fake git; no network or credentials."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / 'sync_publish.sh'
FAKE_GIT = '''#!/bin/sh
printf '%s\\n' "$*" >> "$FAKE_GIT_LOG"
case "$*" in
  'diff --cached --quiet') exit "${FAKE_DIFF:-0}" ;;
  'pull --rebase origin main') exit "${FAKE_PULL:-0}" ;;
  'push origin HEAD:main')
    count=0
    if [ -f "$FAKE_PUSH_COUNT" ]; then read -r count < "$FAKE_PUSH_COUNT"; fi
    count=$((count+1))
    printf '%s\\n' "$count" > "$FAKE_PUSH_COUNT"
    [ "$count" -gt "${FAKE_PUSH_FAILS:-0}" ]
    exit $? ;;
esac
exit 0
'''


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name, source in [('git', FAKE_GIT), ('sleep', '#!/bin/sh\nexit 0\n')]:
            p = self.root / name
            p.write_text(source, encoding='utf-8')
            p.chmod(0o755)
        self.log = self.root / 'commands.txt'
        self.env = {**os.environ, 'PATH': str(self.root) + os.pathsep + os.environ.get('PATH', ''),
                    'FAKE_GIT_LOG': str(self.log),
                    'FAKE_PUSH_COUNT': str(self.root / 'push_count')}

    def run_script(self, **kwargs):
        out = subprocess.run(['bash', str(SCRIPT)], cwd=self.root,
                             capture_output=True, text=True,
                             env={**self.env, **kwargs}, timeout=8)
        calls = self.log.read_text(encoding='utf-8').splitlines()
        return out, calls

    def test_unchanged_skip_commit_and_push(self):
        out, calls = self.run_script(FAKE_DIFF='0')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertFalse(any(s.startswith('commit ') or s.startswith('push ') for s in calls))

    def test_successful_push(self):
        out, calls = self.run_script(FAKE_DIFF='1')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('commit -m Actualizar recuperación y análisis profesional', calls)
        self.assertEqual(calls.count('push origin HEAD:main'), 1)

    def test_pull_conflict_aborts(self):
        out, calls = self.run_script(FAKE_DIFF='1', FAKE_PULL='1')
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('rebase --abort', calls)
        self.assertFalse(any(s.startswith('push ') for s in calls))

    def test_retries_then_success(self):
        out, calls = self.run_script(FAKE_DIFF='1', FAKE_PUSH_FAILS='2')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(calls.count('push origin HEAD:main'), 3)

    def test_five_failed_pushes_fail(self):
        out, calls = self.run_script(FAKE_DIFF='1', FAKE_PUSH_FAILS='5')
        self.assertNotEqual(out.returncode, 0)
        self.assertEqual(calls.count('push origin HEAD:main'), 5)


if __name__ == '__main__':
    unittest.main()
