import unittest

from app.repository.transfer_repository import _filter_positions_for_type


class TransferPositionRulesTests(unittest.TestCase):
    def setUp(self):
        self.positions = [
            {"id": 1, "reserva": "complementario", "estado": 1},
            {"id": 2, "reserva": "picking", "estado": 2},
            {"id": 3, "reserva": " Picking ", "estado": 1},
            {"id": 4, "reserva": "abastecimiento", "estado": 1},
        ]

    def test_manual_me_and_mee_allow_complementary_and_picking_positions(self):
        for item_type in ("ME", "MEE"):
            with self.subTest(item_type=item_type):
                result = _filter_positions_for_type(
                    self.positions,
                    item_type,
                    allow_picking=True,
                )
                self.assertEqual([position["id"] for position in result], [1, 2, 3])

    def test_manual_mp_and_pt_allow_supply_and_picking_positions(self):
        for item_type in ("MP", "PT"):
            with self.subTest(item_type=item_type):
                result = _filter_positions_for_type(
                    self.positions,
                    item_type,
                    allow_picking=True,
                )
                self.assertEqual([position["id"] for position in result], [2, 3, 4])

    def test_automatic_me_suggestion_keeps_complementary_rule(self):
        result = _filter_positions_for_type(self.positions, "ME", only_free=True)
        self.assertEqual([position["id"] for position in result], [1])

    def test_automatic_mp_and_pt_suggestion_keeps_supply_rule(self):
        for item_type in ("MP", "PT"):
            with self.subTest(item_type=item_type):
                result = _filter_positions_for_type(
                    self.positions,
                    item_type,
                    only_free=True,
                )
                self.assertEqual([position["id"] for position in result], [4])


if __name__ == "__main__":
    unittest.main()
