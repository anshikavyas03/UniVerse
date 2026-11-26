import unittest

from app.services.voice.speech_text import to_spoken_text

SYMBOLS = "*#_`|~[]"


class SpokenTextTests(unittest.TestCase):
    def assertNoMarkdown(self, spoken: str) -> None:
        for symbol in SYMBOLS:
            self.assertNotIn(symbol, spoken)

    def test_bold_and_bullets_become_plain_sentences(self):
        spoken = to_spoken_text("**Shared rooms**\n* 2-seater: ₹90,000 per year\n* 4-seater: ₹70,000 per year")
        self.assertEqual(spoken, "Shared rooms. 2-seater: ₹90,000 per year. 4-seater: ₹70,000 per year.")

    def test_headings_links_and_numbered_lists(self):
        spoken = to_spoken_text("## Hostel fees\n1. Read the [fee notice](https://example.edu/fees)\n2) Pay before 5 July")
        self.assertEqual(spoken, "Hostel fees. Read the fee notice. Pay before 5 July.")

    def test_escaped_markdown_and_italics(self):
        spoken = to_spoken_text("The \\*security\\* amount is *refundable* and _one-time_.")
        self.assertEqual(spoken, "The security amount is refundable and one-time.")

    def test_hindi_uses_danda_between_items(self):
        spoken = to_spoken_text("**हॉस्टल शुल्क**\n- 2 सीटर: ₹90,000\n- 4 सीटर: ₹70,000", "hi")
        self.assertEqual(spoken, "हॉस्टल शुल्क। 2 सीटर: ₹90,000। 4 सीटर: ₹70,000।")

    def test_table_rows_code_urls_and_emoji(self):
        spoken = to_spoken_text("| Room | Fee |\n|---|---|\n| Single | 1,20,000 |\n✅ Visit https://example.edu now `today`")
        self.assertEqual(spoken, "Room, Fee. Single, 1,20,000. Visit now today.")

    def test_snake_case_words_and_hyphen_ranges_are_kept(self):
        self.assertEqual(to_spoken_text("Pay 5 - 6 lakh via fee_portal"), "Pay 5 - 6 lakh via fee_portal.")

    def test_no_markdown_symbols_survive(self):
        messy = "# Title\n**Bold** and *it* with `code`, [link](http://x.y), ~~gone~~\n> quote\n---\n* item"
        self.assertNoMarkdown(to_spoken_text(messy))

    def test_empty_or_symbol_only_text_returns_empty(self):
        self.assertEqual(to_spoken_text("***\n---\n##"), "")


if __name__ == "__main__":
    unittest.main()
