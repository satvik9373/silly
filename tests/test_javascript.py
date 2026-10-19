"""Syntax checks for the embedded UI modules using the installed Node runtime."""
from pathlib import Path
import re
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'), 'Node is optional for UI syntax checks')
class JavaScriptTests(unittest.TestCase):
    def test_embedded_scripts_parse(self):
        root = Path(__file__).resolve().parents[1]
        files = list((root / 'ui').glob('*.html')) + list((root / 'tests').glob('*.html'))
        for path in files:
            for attrs, code in re.findall(r'<script([^>]*)>(.*?)</script>', path.read_text(encoding='utf-8'), re.S):
                if 'text/plain' in attrs or 'src=' in attrs:
                    continue
                with self.subTest(file=path.name):
                    p = subprocess.run(['node', '--check', '--input-type=module'], input=code, capture_output=True, text=True, encoding='utf-8')
                    self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == '__main__':
    unittest.main()
