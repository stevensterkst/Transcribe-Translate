import unittest

from core.text import OllamaTextProvider


class SummaryQualityTests(unittest.TestCase):
    def setUp(self):
        self.provider = OllamaTextProvider("http://127.0.0.1:11434", "llama3.2:1b")

    def test_repeated_template_is_rejected(self):
        transcript = (
            "Le point d'accès juridique explique comment demander au tribunal. "
            "L'avocat et le procureur sont évoqués. Le tribunal doit être contacté."
        )
        bad = """Introduction
* Un avocat est mentionné comme capable de demander au tribunal.
Decision and decision-making
* Un avocat est mentionné comme capable de demander au tribunal.
Voting positions
* Un avocat est mentionné comme capable de demander au tribunal.
Action items
* Un avocat est mentionné comme capable de demander au tribunal.
Questions and questions
* Un avocat est mentionné comme capable de demander au tribunal."""
        self.assertFalse(self.provider._summary_quality_ok(bad, transcript))

    def test_factual_summary_is_accepted(self):
        transcript = (
            "Le point d'accès juridique explique comment demander au tribunal. "
            "L'avocat et le procureur sont évoqués. Le tribunal doit être contacté."
        )
        good = (
            "La conversation porte sur le point d'accès juridique et la manière "
            "de faire une demande au tribunal. Les interlocuteurs évoquent le rôle "
            "d'un avocat et d'un procureur et précisent que la procédure dépend du pays. "
            "Ils discutent aussi de la possibilité d'obtenir une aide juridique gratuite "
            "et du fait que le tribunal compétent doit encore être identifié."
        )
        self.assertTrue(self.provider._summary_quality_ok(good, transcript))


if __name__ == "__main__":
    unittest.main()
