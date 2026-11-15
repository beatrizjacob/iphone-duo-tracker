import unittest
from mac_monitor import classify, URL

class MacMonitorTests(unittest.TestCase):
    def test_exact_url(self):
        self.assertIn("128-gb-de-memoria", URL)
        self.assertIn("m5-max", URL)
    def test_no_stock_claim_from_marketing(self):
        html = "<h1>Mac Studio M5 Max with 128 GB de memoria</h1><button>Comprar</button>"
        self.assertEqual(classify(html)[0], "unknown")
    def test_exact_offer_stock(self):
        html = """<h1>Mac Studio M5 Max 128 GB de memoria</h1>
        <script type="application/ld+json">{"@type":"Product","name":"Mac Studio M5 Max 128 GB","offers":{"availability":"https://schema.org/InStock"}}</script>"""
        self.assertEqual(classify(html)[0], "available")
    def test_wrong_variant_not_available(self):
        html = """<h1>Mac Studio M5 Max 128 GB de memoria</h1>
        <script type="application/ld+json">{"@type":"Product","name":"Mac Studio M5 Max 64 GB","offers":{"availability":"https://schema.org/InStock"}}</script>"""
        self.assertEqual(classify(html)[0], "unknown")
if __name__ == "__main__":
    unittest.main()
