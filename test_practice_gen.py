import unittest

import practice_gen as pg


class TestPracticeGen(unittest.TestCase):
    def test_parse_score(self):
        self.assertEqual(pg.parse_score("4/5"), 0.8)
        with self.assertRaises(ValueError):
            pg.parse_score("6/5")
        with self.assertRaises(ValueError):
            pg.parse_score("four")

    def test_difficulty_moves_up_after_high_score(self):
        s = pg.record_score({}, "Alex", "fractions", "5/5", "medium")
        self.assertEqual(pg.pick_difficulty(s, "Alex", "fractions"), "hard")

    def test_difficulty_moves_down_after_low_score(self):
        s = pg.record_score({}, "Alex", "fractions", "1/5", "medium")
        self.assertEqual(pg.pick_difficulty(s, "Alex", "fractions"), "easy")

    def test_new_student_starts_at_medium(self):
        self.assertEqual(pg.pick_difficulty({}, "Sam", "loops"), "medium")

    def test_weak_topics_uses_latest_score(self):
        s = pg.record_score({}, "Alex", "fractions", "1/5")
        s = pg.record_score(s, "Alex", "fractions", "5/5")
        s = pg.record_score(s, "Alex", "decimals", "2/5")
        self.assertEqual(pg.weak_topics(s, "Alex"), ["decimals"])

    def test_parse_problems_handles_wrapped_json(self):
        text = 'Here you go:\n[{"question": "2+2?", "answer": "4", "explanation": "Add."}]'
        problems = pg.parse_problems(text)
        self.assertEqual(problems[0]["answer"], "4")

    def test_parse_problems_rejects_missing_keys(self):
        with self.assertRaises(ValueError):
            pg.parse_problems('[{"question": "2+2?"}]')

    def test_prompt_mentions_weak_topics(self):
        prompt = pg.build_prompt("math", "algebra", "easy", 3, ["fractions"])
        self.assertIn("fractions", prompt)
        self.assertIn("3 easy math", prompt)

    def test_render_worksheet_and_key(self):
        problems = [{"question": "2+2?", "answer": "4", "explanation": "Add."}]
        self.assertIn("**1.** 2+2?", pg.render_worksheet("Alex", "addition", "easy", problems))
        self.assertIn("**1. Answer:** 4", pg.render_answer_key("Alex", "addition", problems))


if __name__ == "__main__":
    unittest.main()
