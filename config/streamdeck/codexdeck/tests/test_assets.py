import unittest
from pathlib import Path

from PIL import Image
from PIL import ImageChops
from PIL import ImageSequence


ASSETS = Path(__file__).parents[1] / "assets"


class AnimatedAssetTest(unittest.TestCase):
    def assert_animation(self, name, expected_frames, expected_duration):
        with Image.open(ASSETS / name) as image:
            self.assertEqual(image.size, (72, 72))
            self.assertEqual(image.n_frames, expected_frames)
            frames = [frame.convert("RGB") for frame in ImageSequence.Iterator(image)]
            durations = {
                frame.info.get("duration")
                for frame in ImageSequence.Iterator(image)
            }
        self.assertEqual(durations, {expected_duration})
        self.assertIsNotNone(
            ImageChops.difference(frames[0], frames[len(frames) // 2]).getbbox()
        )

    def test_active_animation_is_a_slow_four_second_loop(self):
        self.assert_animation("codex-active.gif", 16, 250)

    def test_working_animation_is_a_fast_circulating_loop(self):
        self.assert_animation("codex-working.gif", 12, 120)

    def test_done_animation_is_a_one_second_double_pulse(self):
        self.assert_animation("codex-done.gif", 8, 120)


if __name__ == "__main__":
    unittest.main()
