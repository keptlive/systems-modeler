"""Narrow provenance and independent mathematical checks; no fidelity claim."""
import hashlib
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PhysicalSourceReviewTests(unittest.TestCase):
    def test_review_preserves_non_metadata_fields(self):
        review = json.loads((ROOT / "operations/physical-source-reconciliation-v14.json").read_text())
        for item in review["models"]:
            with self.subTest(model=item["file"]):
                raw = (ROOT / item["file"]).read_bytes()
                if hashlib.sha256(raw).hexdigest() != item["after_sha256"]:
                    chain = json.loads((ROOT / "operations/model-revision-chain-v17.json").read_text())
                    revision = next(row for row in chain["models"] if row["file"] == item["file"])
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), revision["after_sha256"])
                    self.assertEqual(revision["before_sha256"], item["after_sha256"])
                    raw = revision["before_text"].encode()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), item["after_sha256"])
                after = json.loads(raw)
                for key in ("source", "reference", "description"):
                    after.pop(key, None)
                canonical = json.dumps(after, sort_keys=True, separators=(",", ":")).encode()
                self.assertEqual(hashlib.sha256(canonical).hexdigest(), item["before_non_metadata_sha256"])

    def test_greenshields_capacity(self):
        # q=vf*rho*(1-rho/jam); q'=0 at jam/2 and q''<0.
        vf, jam = 60.0, 150.0
        critical = jam / 2
        flux = lambda rho: vf * rho * (1 - rho / jam)
        self.assertEqual(flux(critical), vf * jam / 4)
        self.assertGreater(flux(critical), flux(critical - 1))
        self.assertGreater(flux(critical), flux(critical + 1))

    def test_weak_allee_has_no_positive_intrinsic_threshold(self):
        r, A, K = 0.5, 20.0, 500.0
        for N in (1e-8, 0.1, 1, A / 2, A, 100, 499):
            self.assertGreater(r * N / (A + N) * (1 - N / K), 0)

    def test_bz_defaults_stiffness(self):
        derivative = 2 * 2 - 1e6 * 1 * 2 + 10 * 1 - 2000 * 1 * 1
        self.assertEqual(derivative, -2001986)
        self.assertLess(1 + 0.01 * derivative, 0)


if __name__ == "__main__":
    unittest.main()
