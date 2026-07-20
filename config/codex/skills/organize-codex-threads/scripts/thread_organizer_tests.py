#!/usr/bin/env python3
"""Regression tests for thread organizer eligibility."""

import unittest

import thread_organizer


class AutomationOriginTests(unittest.TestCase):
    def test_accepts_app_server_automation_metadata(self) -> None:
        self.assertTrue(
            thread_organizer.is_automation_thread(
                {"threadSource": "automation"},
                [{"user_prompt": "Run the job", "model_response": "Done"}],
            )
        )

    def test_accepts_aton_prompt_when_metadata_is_missing(self) -> None:
        self.assertTrue(
            thread_organizer.is_automation_thread(
                {"threadSource": None},
                [
                    {
                        "user_prompt": "Aton automation ID: nightly-job Run it",
                        "model_response": "Done",
                    }
                ],
            )
        )

    def test_rejects_interactive_thread(self) -> None:
        self.assertFalse(
            thread_organizer.is_automation_thread(
                {"threadSource": None},
                [{"user_prompt": "Please rename this", "model_response": "Done"}],
            )
        )


if __name__ == "__main__":
    unittest.main()
