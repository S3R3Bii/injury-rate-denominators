import sys, unittest
from pathlib import Path
from fractions import Fraction

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from project_source import classify, number, integer
from metrics import rate, posterior, fixed12, zero_upper
from exercise import answer


def row():
    return dict(
        ID="1",
        establishment_ID="9",
        year_filing_for="2025",
        naics_code="311111",
        size="21",
        annual_average_employees="10",
        no_injuries_illnesses="1",
        total_hours_worked="200000",
        total_deaths="0",
        total_dafw_cases="1",
        total_djtr_cases="0",
        total_other_cases="1",
        total_injuries="2",
        total_skin_disorders="0",
        total_respiratory_conditions="0",
        total_poisonings="0",
        total_hearing_loss="0",
        total_other_illnesses="0",
    )


def state(r):
    return classify(r, set(), set())[0]


class SourceTests(unittest.TestCase):
    def test_maximum_size_not_annual_average(self):
        r = row()
        self.assertEqual(state(r), "eligible")
        r["size"] = "3"
        r["annual_average_employees"] = "50"
        self.assertEqual(state(r), "other_size")

    def test_all_fixed_size_codes(self):
        for token, label in [
            ("21", "20-99"),
            ("22", "100-249"),
            ("2", "20-249 unsplit"),
        ]:
            r = row()
            r["size"] = token
            self.assertEqual(classify(r, set(), set())[1][1], label)

    def test_unknown_counts_not_zero(self):
        for token in ["", "nan", "Infinity", "-1", "0.5"]:
            r = row()
            r["total_deaths"] = token
            self.assertEqual(state(r), "unknown_counts")

    def test_two_totals_must_reconcile(self):
        r = row()
        r["total_injuries"] = "3"
        self.assertEqual(state(r), "inconsistent_counts")

    def test_documented_no_injury_code_two(self):
        r = row()
        for k in ["total_dafw_cases", "total_other_cases", "total_injuries"]:
            r[k] = "0"
        r["no_injuries_illnesses"] = "2"
        self.assertEqual(state(r), "eligible")

    def test_flag_zero_not_assumed_false(self):
        r = row()
        r["no_injuries_illnesses"] = "0"
        self.assertEqual(state(r), "unknown_flag")

    def test_contradictory_no_injury_flag(self):
        r = row()
        r["no_injuries_illnesses"] = "2"
        self.assertEqual(state(r), "inconsistent_flag")

    def test_zero_count_with_had_injury_flag(self):
        r = row()
        for k in ["total_dafw_cases", "total_other_cases", "total_injuries"]:
            r[k] = "0"
        self.assertEqual(state(r), "inconsistent_flag")

    def test_zero_negative_exposure(self):
        for token in ["0", "-1"]:
            r = row()
            r["total_hours_worked"] = token
            self.assertEqual(state(r), "nonpositive_exposure")

    def test_unknown_exposure(self):
        for token in ["", "NaN", "inf", "unknown"]:
            r = row()
            r["total_hours_worked"] = token
            self.assertEqual(state(r), "unknown_exposure")

    def test_fractional_exposure_exact(self):
        r = row()
        r["total_hours_worked"] = "200000.5"
        self.assertEqual(classify(r, set(), set())[1][-1], "400001/2")

    def test_whole_record_duplicate_group(self):
        for case in ["1", "9"]:
            r = row()
            r["total_dafw_cases"] = case
            self.assertEqual(
                classify(r, {("1", "2025")}, set())[0], "duplicate_identity"
            )

    def test_whole_establishment_duplicate_group(self):
        for rid in ["1", "2"]:
            r = row()
            r["ID"] = rid
            self.assertEqual(
                classify(r, set(), {("9", "2025")})[0], "duplicate_identity"
            )

    def test_missing_identity_before_invalid_values(self):
        r = row()
        r["ID"] = ""
        r["total_hours_worked"] = ""
        self.assertEqual(state(r), "missing_identity")

    def test_fixed_year(self):
        for token in ["2024", "2026", ""]:
            r = row()
            r["year_filing_for"] = token
            self.assertEqual(state(r), "wrong_year")

    def test_malformed_and_other_industry(self):
        for token, expected in [
            ("31", "malformed_industry"),
            ("31111x", "malformed_industry"),
            ("541111", "other_industry"),
        ]:
            r = row()
            r["naics_code"] = token
            self.assertEqual(state(r), expected)

    def test_source_integer_semantics(self):
        self.assertEqual(integer("1.0"), 1)
        self.assertIsNone(integer("1.1"))
        self.assertIsNone(number("NaN"))


class RateTests(unittest.TestCase):
    def test_rate_unit_and_exact_hours(self):
        self.assertEqual(rate(2, 200000), 2)
        self.assertEqual(rate(1, 400000), Fraction(1, 2))
        self.assertEqual(rate(2, "400001/2"), Fraction(800000, 400001))

    def test_zero_count_retained(self):
        self.assertEqual(rate(0, 20000), 0)

    def test_invalid_count_and_denominator(self):
        for k, h in [(-1, 10), ("1/2", 10), (1, 0), (1, -10), (True, 10), (1, True)]:
            with self.assertRaises(ValueError):
                rate(k, h)

    def test_all_prior_strengths(self):
        self.assertEqual(posterior(2, 200000, 4, "1/10"), Fraction(24, 11))
        self.assertEqual(posterior(2, 200000, 4, 1), 3)
        self.assertEqual(posterior(2, 200000, 4, 10), Fraction(42, 11))

    def test_prior_interpolation_and_exposure(self):
        self.assertLess(posterior(10, 200000, 4, 1), 10)
        self.assertGreater(posterior(0, 200000, 4, 1), 0)
        self.assertLess(
            abs(posterior(100, 2000000, 4, 1) - 10),
            abs(posterior(10, 200000, 4, 1) - 10),
        )

    def test_exact_two_times_tie(self):
        self.assertFalse(rate(8, 200000) > 2 * 4)
        self.assertTrue(rate(9, 200000) > 8)
        self.assertFalse(posterior(9, 200000, 4, 1) > 8)

    def test_unavailable_zero_pooled_prior(self):
        for mu in [0, -1]:
            with self.assertRaises(ValueError):
                posterior(0, 1, mu, 1)

    def test_unsupported_strength_or_boolean(self):
        for b in [0, 2, True]:
            with self.assertRaises(ValueError):
                posterior(1, 200000, 4, b)

    def test_half_even_precision_and_poisson_zero_bound(self):
        self.assertEqual(fixed12(Fraction(1, 2000000000000)), "0.000000000000")
        self.assertEqual(fixed12(Fraction(3, 2000000000000)), "0.000000000002")
        self.assertEqual(zero_upper(200000), "2.995732273554")


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.r = dict(
            purpose="reported_stratum_account",
            denominator="reported_positive_hours",
            industry="31",
            size_class="20-99",
        )
        self.a = [
            dict(
                industry="31",
                size_class="20-99",
                eligible_records="2",
                unavailable_records="1",
                total_cases="3",
                total_hours="400000",
                pooled_raw_rate="3/2",
            )
        ]

    def test_qualified_current_account(self):
        a = answer(self.r, self.a)
        self.assertEqual(a["status"], "ACCEPTED_QUALIFIED")
        self.assertEqual(a["reported_rate_per100FTE"], "3/2")
        self.assertEqual(a["workplace_safety"], "UNESTABLISHED")

    def test_safety_legal_worker_and_forecast_rejected(self):
        for purpose in [
            "workplace_safety_ranking",
            "legal_fault",
            "worker_eligibility",
            "future_risk",
        ]:
            self.assertEqual(
                answer(dict(self.r, purpose=purpose), self.a)["status"], "REJECTED"
            )

    def test_denominator_substitution_rejected(self):
        self.assertEqual(
            answer(dict(self.r, denominator="employee_count"), self.a)["status"],
            "REJECTED",
        )

    def test_empty_unknown_and_duplicate_strata_rejected(self):
        self.assertEqual(answer(self.r, [])["status"], "REJECTED")
        self.assertEqual(answer(self.r, self.a * 2)["status"], "REJECTED")
        self.a[0]["eligible_records"] = "0"
        self.assertEqual(answer(self.r, self.a)["status"], "REJECTED")

    def test_nonmapping_input_rejected(self):
        self.assertEqual(answer(None, self.a)["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
