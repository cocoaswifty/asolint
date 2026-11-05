"""asolint 的離線測試（不打網路，全部使用 fixture）。"""

import unittest

import asolint


def sample_app(**overrides):
    app = {
        "trackId": 6443918070,
        "trackName": "Habit Tracker - HabitKit",
        "sellerName": "Sebastian Roehl",
        "primaryGenreName": "Productivity",
        "country": "tw",
        "trackViewUrl": "https://apps.apple.com/tw/app/id6443918070",
        "averageUserRating": 4.93617,
        "userRatingCount": 47,
        "languageCodesISO2A": ["EN", "JA", "KO", "FR"],
        "screenshotUrls": ["a", "b", "c", "d", "e"],
        "ipadScreenshotUrls": [],
        "description": "Big life changes do not start big.\nThey start small.\nLine three.\nLine four.",
        "currentVersionReleaseDate": "2026-11-04T06:26:47Z",
    }
    app.update(overrides)
    return app


class ParseAppIdTests(unittest.TestCase):
    def test_url(self):
        self.assertEqual(
            asolint.parse_app_id("https://apps.apple.com/tw/app/x/id6443918070?uo=4"),
            "6443918070",
        )

    def test_bare_id(self):
        self.assertEqual(asolint.parse_app_id("123456789"), "123456789")

    def test_invalid(self):
        with self.assertRaises(ValueError):
            asolint.parse_app_id("not-an-app")


class AnalyzeTests(unittest.TestCase):
    def test_missing_chinese_flagged(self):
        result = asolint.analyze(sample_app(), ["ZH", "JA", "KO"])
        self.assertEqual(result["missing_targets"], ["ZH"])
        titles = [f["title"] for f in result["findings"]]
        self.assertTrue(any("中文" in t for t in titles))

    def test_covered_languages_not_flagged_high(self):
        app = sample_app(languageCodesISO2A=["ZH", "EN"])
        result = asolint.analyze(app, ["ZH"])
        self.assertEqual(result["missing_targets"], [])
        high = [f for f in result["findings"] if f["severity"] == "high"]
        self.assertEqual(high, [])

    def test_few_screenshots_are_high(self):
        app = sample_app(screenshotUrls=["a"])
        result = asolint.analyze(app, ["ZH"])
        high_titles = [f["title"] for f in result["findings"] if f["severity"] == "high"]
        self.assertTrue(any("截圖" in t for t in high_titles))

    def test_score_bounds(self):
        app = sample_app(
            languageCodesISO2A=[], screenshotUrls=[], ipadScreenshotUrls=[],
            userRatingCount=0, averageUserRating=None,
        )
        result = asolint.analyze(app, ["ZH", "JA", "KO", "EN"])
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    def test_render_markdown_marks_hypothesis(self):
        result = asolint.analyze(sample_app(), ["ZH"])
        md = asolint.render_markdown(result)
        self.assertIn("待驗證", md)
        self.assertIn("HabitKit", md)


if __name__ == "__main__":
    unittest.main()
