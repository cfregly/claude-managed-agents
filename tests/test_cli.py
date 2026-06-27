import contextlib
import io
import os
import unittest
from unittest.mock import patch

import run


class CliTests(unittest.TestCase):
    def test_bad_flag_is_rejected_before_key_check(self):
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as e:
                run.main(["--definitely-not-real"])
        self.assertEqual(e.exception.code, 2)

    def test_cleanup_flag_still_parses(self):
        args = run.parse_args(["--cleanup"])
        self.assertTrue(args.cleanup)

    def test_compare_mode_parses_without_key_check(self):
        args = run.parse_args(["compare", "--providers", "managed,self-managed"])
        self.assertEqual(args.command, "compare")
        self.assertEqual(args.providers, "managed,self-managed")

    def test_missing_key_still_fails_fast_for_valid_args(self):
        with patch.dict(os.environ, {"PYTHON_DOTENV_DISABLED": "1"}, clear=True):
            self.assertEqual(run.main([]), 1)

    def test_compare_dry_run_does_not_require_key(self):
        with patch.dict(os.environ, {"PYTHON_DOTENV_DISABLED": "1"}, clear=True), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run.main(["compare", "--providers", "managed"]), 0)


if __name__ == "__main__":
    unittest.main()
