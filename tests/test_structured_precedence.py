"""Regressions for structured values mislabelled by statistical NER."""
import unittest
from unittest.mock import patch
from app.deid import recognizers as r


class StructuredPrecedenceTests(unittest.TestCase):
    def detect(self, text, predictions):
        entities = [r.Entity(text.index(value), text.index(value) + len(value),
                             value, label, 'spacy') for value, label in predictions]
        with patch.object(r, '_spacy_entities', return_value=entities):
            return [(e.text, e.label, e.detector) for e in r.detect_entities(text)]

    def test_numeric_dates_override_person_predictions(self):
        for value in ('03/19/2024', '12-31-2025', '2026-10-09'):
            with self.subTest(value=value):
                self.assertEqual(self.detect('Discharged ' + value, [(value, 'PERSON')]),
                                 [(value, 'DATE', 'regex')])

    def test_full_street_overrides_partial_person_and_numeric_ner(self):
        text = 'Mailing address 218 Larkspur Lane, Denver, 80218.'
        self.assertEqual(self.detect(text, [('Larkspur Lane', 'PERSON'),
                                           ('Denver', 'GPE'), ('80218', 'DATE')]),
                         [('218 Larkspur Lane', 'US_STREET', 'regex'),
                          ('Denver', 'GPE', 'spacy'), ('80218', 'ZIP_US', 'regex')])

    def test_distinct_names_survive_structured_rule_precedence(self):
        text = 'Avery Chen visited on 2025-12-31.'
        self.assertEqual(self.detect(text, [('Avery Chen', 'PERSON')]),
                         [('Avery Chen', 'PERSON', 'spacy'), ('2025-12-31', 'DATE', 'regex')])

    def test_contextual_field_name_is_not_an_organization(self):
        text = 'SSN on file 412-88-7735.'
        self.assertEqual(self.detect(text, [('SSN', 'ORG')]),
                         [('412-88-7735', 'SSN', 'regex')])

    def test_same_acronym_without_field_context_is_preserved(self):
        text = 'SSN announced a project.'
        self.assertEqual(self.detect(text, [('SSN', 'ORG')]), [('SSN', 'ORG', 'spacy')])

    def test_email_priority_over_structured_fragments_is_preserved(self):
        text = 'Contact patient80218@example.com.'
        self.assertEqual(self.detect(text, [('patient80218', 'PERSON')]),
                         [('patient80218@example.com', 'EMAIL', 'regex')])

    def test_offsets_after_emoji_and_multiline_text(self):
        text = '😀\nAddress: 42 Cedar Road\nZIP: 02139'
        result = self.detect(text, [('Cedar Road', 'PERSON'), ('02139', 'DATE')])
        self.assertEqual(result, [('42 Cedar Road', 'US_STREET', 'regex'),
                                  ('02139', 'ZIP_US', 'regex')])


if __name__ == '__main__':
    unittest.main()
