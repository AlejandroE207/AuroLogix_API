import unittest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from app.model.picking_model import Picking_items
from app.model.inventory_model import Motion
from app.service import picking_service
from app.repository import inventory_repository


class PickingImportTests(unittest.IsolatedAsyncioTestCase):
    async def test_inventory_output_deletes_row_when_last_units_are_picked(self):
        db = AsyncMock()
        selected_result = MagicMock()
        selected_result.mappings.return_value.first.return_value = {
            "id": 44,
            "cantidad": 2.0,
        }
        deleted_result = MagicMock()
        deleted_result.mappings.return_value.first.return_value = {"id": 44}
        db.execute.side_effect = [selected_result, deleted_result]

        result = await inventory_repository.update_inventory_quantity(
            db, 1119, 1068, "47700", 2.0, commit=False
        )

        self.assertEqual(result["result"], 1)
        self.assertEqual(result["cantidad_restante"], 0)
        self.assertIn("DELETE FROM inventario", str(db.execute.await_args_list[1].args[0]))
        db.commit.assert_not_awaited()
        db.rollback.assert_not_awaited()

    async def test_allocation_prioritizes_requested_lot_then_fefo_alternatives(self):
        requested = [{"id_item": 10, "item_code": "ITEM-1", "cantidad": 7, "lote": "L1"}]
        inventory = {
            10: [
                {"id_posicion": 1, "lote": "L2", "cantidad": 4, "fecha_vencimiento": date(2026, 8, 1)},
                {"id_posicion": 2, "lote": "L1", "cantidad": 2, "fecha_vencimiento": date(2027, 1, 1)},
                {"id_posicion": 3, "lote": "L3", "cantidad": 4, "fecha_vencimiento": date(2026, 7, 20)},
            ]
        }

        tasks, errors = picking_service._allocate_inventory(requested, inventory)

        self.assertEqual(
            [(task["lote"], task["cantidad"]) for task in tasks],
            [("L1", 2), ("L3", 4), ("L2", 1)],
        )
        self.assertEqual(errors, [])

    async def test_allocation_returns_available_tasks_and_reports_remaining_quantity(self):
        requested = [{"id_item": 10, "item_code": "ITEM-1", "cantidad": 5, "lote": "L1"}]
        inventory = {
            10: [
                {"id_posicion": 1, "lote": "L2", "cantidad": 3, "fecha_vencimiento": date(2026, 8, 1)},
            ]
        }

        tasks, errors = picking_service._allocate_inventory(requested, inventory)

        self.assertEqual([(task["lote"], task["cantidad"]) for task in tasks], [("L2", 3)])
        self.assertEqual(errors[0]["faltante"], 2)

    async def test_confirmation_validates_the_task_selected_by_the_user(self):
        db = AsyncMock()
        selected_task = Picking_items(
            id=25,
            id_item=10,
            cantidad=2,
            lote="L1",
            id_posicion_origen=7,
            cod_posicion_origen="R1-N1-P1",
            estado=1,
            result=1,
        )
        with (
            patch.object(
                picking_service.picking_repository,
                "get_task_by_id",
                AsyncMock(return_value=selected_task),
            ) as get_selected_task,
            patch.object(
                picking_service.picking_repository,
                "get_next_task",
                AsyncMock(),
            ) as get_next_task,
        ):
            result = await picking_service.confirm_task(
                db, 25, 3, "POSICION-INCORRECTA", 9
            )

        self.assertEqual(result["result"], 0)
        get_selected_task.assert_awaited_once_with(db, 3, 25)
        get_next_task.assert_not_awaited()

    async def test_confirmation_rolls_back_motion_when_inventory_update_fails(self):
        db = AsyncMock()
        selected_task = Picking_items(
            id=25,
            id_item=10,
            cantidad=1,
            lote="L1",
            id_posicion_origen=7,
            cod_posicion_origen="R1-N1-P1",
            estado=1,
            result=1,
        )
        motion_result = Motion(id=90, result=1)
        with (
            patch.object(
                picking_service.picking_repository,
                "get_task_by_id",
                AsyncMock(return_value=selected_task),
            ),
            patch.object(
                picking_service.motion_repository,
                "create_motion_output",
                AsyncMock(return_value=motion_result),
            ) as create_motion,
            patch.object(
                picking_service.inventory_repository,
                "update_inventory_quantity",
                AsyncMock(return_value={
                    "result": 0,
                    "message": "Inventario insuficiente",
                }),
            ) as update_inventory,
        ):
            result = await picking_service.confirm_task(
                db, 25, 3, "R1-N1-P1", 9
            )

        self.assertEqual(result["result"], 0)
        self.assertIn("Inventario insuficiente", result["message"])
        create_motion.assert_awaited_once()
        self.assertFalse(create_motion.await_args.kwargs["commit"])
        self.assertEqual(update_inventory.await_args.args[4], 1.0)
        self.assertFalse(update_inventory.await_args.kwargs["commit"])
        db.commit.assert_not_awaited()
        db.rollback.assert_awaited_once()

    async def test_import_registers_new_orders_and_reports_existing_ones(self):
        content = (
            "Nro documento;Razon social cliente factura;Referencia;Cantidad;Bodega\n"
            "FAC-NEW;Cliente nuevo;ITEM-1;2;M01\n"
            "FAC-OLD;Cliente anterior;ITEM-1;1;M01\n"
        ).encode()
        db = AsyncMock()

        async def create_orders(_db, orders):
            self.assertEqual([order["codigo"] for order in orders], ["FAC-NEW"])
            self.assertIn("items", orders[0])
            self.assertNotIn("tasks", orders[0])
            return [{"codigo": "FAC-NEW", "order_id": 1, "picking_id": 2}]

        with (
            patch.object(
                picking_service.picking_repository,
                "get_existing_order_codes",
                AsyncMock(return_value={"FAC-OLD"}),
            ),
            patch.object(
                picking_service.picking_repository,
                "get_items_by_codes",
                AsyncMock(return_value={"ITEM-1": {"id": 10}}),
            ),
            patch.object(
                picking_service.picking_repository,
                "create_bulk_pickings",
                AsyncMock(side_effect=create_orders),
            ),
        ):
            result = await picking_service.import_orders_file(db, content, "csv", 7)

        self.assertEqual(result["registered_orders"], ["FAC-NEW"])
        self.assertEqual(
            result["not_registered_orders"],
            [{"codigo": "FAC-OLD", "motivo": "La orden ya existe"}],
        )
        db.commit.assert_awaited_once()

    async def test_picking_without_stock_remains_pending(self):
        db = AsyncMock()
        no_task = Picking_items(result=0)
        details = [{"id_item": 10, "cod_item": "ITEM-1", "cantidad": 3, "lote": ""}]

        with (
            patch.object(
                picking_service.picking_repository,
                "get_next_task",
                AsyncMock(return_value=no_task),
            ),
            patch.object(
                picking_service.picking_repository,
                "count_picking_tasks",
                AsyncMock(return_value=0),
            ),
            patch.object(
                picking_service.picking_repository,
                "get_picking_details",
                AsyncMock(return_value=details),
            ),
            patch.object(
                picking_service.picking_repository,
                "get_inventory_for_items",
                AsyncMock(return_value={}),
            ),
            patch.object(
                picking_service.picking_repository,
                "complete_picking",
                AsyncMock(),
            ) as complete_picking,
        ):
            result = await picking_service.get_next_task(db, 2)

        self.assertTrue(result["awaiting_stock"])
        self.assertEqual(result["missing_inventory"][0]["cantidad_faltante"], 3)
        complete_picking.assert_not_awaited()

    async def test_tasks_are_generated_when_stock_becomes_available(self):
        db = AsyncMock()
        no_task = Picking_items(result=0)
        generated_task = Picking_items(id=99, id_item=10, cantidad=3, result=1)
        details = [{"id_item": 10, "cod_item": "ITEM-1", "cantidad": 3, "lote": "L1"}]
        inventory = {
            10: [{"id_item": 10, "id_posicion": 5, "lote": "L1", "cantidad": 3}]
        }

        with (
            patch.object(
                picking_service.picking_repository,
                "get_next_task",
                AsyncMock(side_effect=[no_task, generated_task]),
            ),
            patch.object(
                picking_service.picking_repository,
                "count_picking_tasks",
                AsyncMock(return_value=0),
            ),
            patch.object(
                picking_service.picking_repository,
                "get_picking_details",
                AsyncMock(return_value=details),
            ),
            patch.object(
                picking_service.picking_repository,
                "get_inventory_for_items",
                AsyncMock(return_value=inventory),
            ),
            patch.object(
                picking_service.picking_repository,
                "insert_picking_tasks",
                AsyncMock(),
            ) as insert_tasks,
        ):
            result = await picking_service.get_next_task(db, 2)

        self.assertEqual(result["task"].id, 99)
        insert_tasks.assert_awaited_once()
        db.commit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
