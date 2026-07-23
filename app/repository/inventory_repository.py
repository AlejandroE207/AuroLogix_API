from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.aux_inv_model import InvAux, InvAuxCont
from app.model.dashboard_model import Summary
from app.model.inventory_model import Inventory
from app.model.picking_model import Picking_items

async def get_positions(db: AsyncSession):
    """Consulta el listado completo de posiciones."""
    # query = text("""
    #              SELECT id, cod_posicion, bodega, estado, reserva
    #              FROM posiciones
    #              ORDER BY id ASC
    #              """)
    query = text("""
                 SELECT id, cod_posicion
                 FROM posiciones
                 ORDER BY id ASC
                 """)
    try:
        result = await db.execute(query)
        return [dict(row) for row in result.mappings().all()]
    except Exception as e:
        print(f"Error al obtener las posiciones: {e}")
        return []


async def create_input_inventory(db: AsyncSession, inventory: Inventory):
    """
    Inserta el registro en inventario.
    Fix: eliminado el 'await db.commit()' — el service maneja la transacción
    completa (motion + inventory + delete_putaway) en un solo commit atómico.
    """
    inventory_data = Inventory()
    query = text("""
                 INSERT INTO inventario (id_posicion, id_item, cantidad, lote, detalles, fecha_vencimiento)
                 VALUES (:id_posicion, :id_item, :cantidad, :lote, :detalles, :fecha_vencimiento)
                 RETURNING id
                 """)
    try:
        result = await db.execute(query, {
            "id_posicion": inventory.id_posicion,
            "id_item": inventory.id_item,
            "cantidad": inventory.cantidad,
            "lote": inventory.lote,
            "detalles": inventory.detalles,
            "fecha_vencimiento": inventory.fecha_vencimiento,
        })
        row = result.mappings().first()
        # Sin commit — el service hace commit de toda la operación al final
        if row:
            inventory_data.id = row["id"]
            inventory_data.result = 1
            inventory_data.message = "Inventario de entrada creado exitosamente"
        else:
            inventory_data.result = 0
            inventory_data.message = "Error al crear el inventario de entrada"
        return inventory_data
    except Exception as e:
        print(f"Error al crear el inventario de entrada: {e}")
        inventory_data.result = 0
        inventory_data.message = "Error al crear el inventario de entrada"
        return inventory_data
    



async def get_position_by_item(db: AsyncSession, id_item:int, lote:str):
    picking_item = Picking_items()
    query = text("""
                 SELECT id_item, id_posicion, lote
                 FROM inventario
                 WHERE id_item = :id_item AND lote = :lote
                 """)
    try:
        result = await db.execute(query, {"id_item": id_item, "lote":lote})
        row = result.mappings().first()
        if row:
            picking_item = Picking_items(**dict(row))
            picking_item.id_posicion_origen = row["id_posicion"]
            picking_item.result = 1
            picking_item.message = "Inventario encontrado"
        else:
            picking_item.result = 0
            picking_item.message = "Inventario no encontrado"
        return picking_item
    except Exception as e:
        print(f"Error al obtener el inventario por item: {e}")
        picking_item.result = 0
        picking_item.message = "Error al obtener el inventario"
        return picking_item


async def update_inventory_quantity(
    db: AsyncSession,
    id_posicion: int,
    id_item: int,
    lote: str,
    cantidad_salida: float,
    commit: bool = True,
):
    """Actualiza la cantidad de inventario después de una salida (picking)."""
    select_query = text("""
                 SELECT id, cantidad
                 FROM inventario
                 WHERE id_posicion = :id_posicion AND id_item = :id_item
                   AND lote IS NOT DISTINCT FROM :lote
                 ORDER BY id
                 LIMIT 1
                 FOR UPDATE
                 """)
    params = {
        "id_posicion": id_posicion,
        "id_item": id_item,
        "lote": lote,
        "cantidad_salida": float(cantidad_salida),
    }
    try:
        result = await db.execute(select_query, params)
        inventory_row = result.mappings().first()
        if not inventory_row or float(inventory_row["cantidad"]) < params["cantidad_salida"]:
            if commit:
                await db.rollback()
            return {
                "result": 0,
                "message": "El inventario asignado no existe o ya no tiene cantidad suficiente",
            }

        remaining_quantity = float(inventory_row["cantidad"]) - params["cantidad_salida"]
        if remaining_quantity == 0:
            result = await db.execute(
                text("""
                     DELETE FROM inventario
                     WHERE id = :id
                     RETURNING id
                     """),
                {"id": inventory_row["id"]},
            )
        else:
            result = await db.execute(
                text("""
                     UPDATE inventario
                     SET cantidad = :cantidad_restante
                     WHERE id = :id
                     RETURNING id
                     """),
                {
                    "id": inventory_row["id"],
                    "cantidad_restante": remaining_quantity,
                },
            )
        updated_row = result.mappings().first()
        if not updated_row:
            if commit:
                await db.rollback()
            return {
                "result": 0,
                "message": "No fue posible actualizar el inventario asignado",
            }
        if commit:
            await db.commit()
        return {
            "result": 1,
            "message": "Inventario actualizado exitosamente",
            "cantidad_restante": remaining_quantity,
        }
    except Exception as e:
        print(f"Error al actualizar el inventario: {e}")
        if commit:
            await db.rollback()
        return {"result": 0, "message": "Error al actualizar el inventario"}
    
    
async def get_inventory_by_position_item_lote(db: AsyncSession, id_posicion: int, id_item: int, lote: str):
    """Busca un registro de inventario existente para una combinación exacta
    de posición + item + lote. Se usa durante la importación masiva desde
    Excel para decidir si se debe sumar cantidad a un registro existente o
    crear uno nuevo."""
    query = text("""
                 SELECT id, id_posicion, id_item, cantidad, lote, detalles, fecha_vencimiento
                 FROM inventario
                 WHERE id_posicion = :id_posicion AND id_item = :id_item
                       AND lote IS NOT DISTINCT FROM :lote
                 """)
    try:
        result = await db.execute(query, {"id_posicion": id_posicion, "id_item": id_item, "lote": lote})
        row = result.mappings().first()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error al buscar el inventario por posición/item/lote: {e}")
        return None


async def increment_inventory_quantity(db: AsyncSession, id_inventario: int, cantidad_sumar: float):
    """Suma `cantidad_sumar` a la cantidad ya existente de un registro de inventario."""
    inventory_data = Inventory()
    query = text("""
                 UPDATE inventario
                 SET cantidad = cantidad + :cantidad_sumar
                 WHERE id = :id
                 RETURNING id, cantidad
                 """)
    try:
        result = await db.execute(query, {"id": id_inventario, "cantidad_sumar": cantidad_sumar})
        row = result.mappings().first()
        await db.commit()
        if row:
            inventory_data.id = row["id"]
            inventory_data.cantidad = row["cantidad"]
            inventory_data.result = 1
            inventory_data.message = "Cantidad de inventario incrementada exitosamente"
        else:
            inventory_data.result = 0
            inventory_data.message = "No se encontró el registro de inventario a incrementar"
        return inventory_data
    except Exception as e:
        print(f"Error al incrementar la cantidad de inventario: {e}")
        await db.rollback()
        inventory_data.result = 0
        inventory_data.message = "Error al incrementar la cantidad de inventario"
        return inventory_data


async def count_expiration_alerts(db: AsyncSession):
    summary_aux = Summary()
    query = text("""
                    SELECT 
                        COUNT(*) FILTER (WHERE i.fecha_vencimiento::date < CURRENT_DATE) AS vencidos,
                        COUNT(*) FILTER (WHERE i.fecha_vencimiento::date >= CURRENT_DATE AND i.fecha_vencimiento::date <= CURRENT_DATE + INTERVAL '90 days') AS criticos,
                        COUNT(*) FILTER (WHERE i.fecha_vencimiento::date > CURRENT_DATE + INTERVAL '90 days' AND i.fecha_vencimiento::date <= CURRENT_DATE + INTERVAL '150 days') AS leve
                    FROM inventario AS i;
                 """)
    try:
        result = await db.execute(query)
        row = result.mappings().first()
        if row:
            summary_aux.alertas_vencido = row["vencidos"]
            summary_aux.alertas_vencimiento_leve = row["leve"]
            summary_aux.alertas_vencimiento_critico = row["criticos"]
            summary_aux.result = 1
            summary_aux.message = "Alertas de vencimiento obtenidas exitosamente"
        else:
            summary_aux.result = 0
            summary_aux.message = "Error al obtener las alertas de vencimiento"
        return summary_aux
    except Exception as e:
        print(f"Error al contar las alertas de vencimiento: {e}")
        summary_aux.result = 0
        summary_aux.message = "Error al obtener las alertas de vencimiento"
        return summary_aux
    
async def get_list_piso(db: AsyncSession):
    transfer_data_list = []
    query = text("""
                    SELECT 
                        i.id, i.id_posicion, i.id_item,it.tipo_item, it.descripcion, i.cantidad, it.unidad_medida, i.lote, i.detalles, i.fecha_vencimiento,
                        p.cod_posicion 
                    FROM inventario AS i
                    JOIN posiciones AS p ON i.id_posicion = p.id
                    INNER JOIN items AS it ON i.id_item = it.id
                    WHERE  i.id_posicion = 1329;
                 """)
    try:
        result = await db.execute(query)
        rows = result.mappings().all()
        for row in rows:
            transfer_data_list.append({
                "id": row["id"],
                "id_posicion": row["id_posicion"],
                "cod_posicion": row["cod_posicion"],
                "id_item": row["id_item"],
                "tipo_item": row["tipo_item"],
                "descripcion": row["descripcion"],
                "cantidad": row["cantidad"],
                "unidad_medida": row["unidad_medida"],
                "lote": row["lote"],
                "detalles": row["detalles"],
                "fecha_vencimiento": row["fecha_vencimiento"]
            })
        return transfer_data_list
    except Exception as e:
        print(f"Error al obtener la lista de piso: {e}")
        return []


async def get_list_stored_inventory(db: AsyncSession):
    transfer_data_list = []
    query = text("""
                    SELECT 
                        i.id, i.id_posicion, i.id_item, it.tipo_item, it.descripcion, i.cantidad, it.unidad_medida, i.lote, i.detalles, i.fecha_vencimiento,
                        p.cod_posicion
                    FROM inventario AS i
                    JOIN posiciones AS p ON i.id_posicion = p.id
                    INNER JOIN items AS it ON i.id_item = it.id
                    WHERE i.id_posicion <> 9999
                    ORDER BY p.cod_posicion ASC, it.descripcion ASC, i.lote ASC
                 """)
    try:
        result = await db.execute(query)
        rows = result.mappings().all()
        for row in rows:
            transfer_data_list.append({
                "id": row["id"],
                "id_posicion": row["id_posicion"],
                "cod_posicion": row["cod_posicion"],
                "id_item": row["id_item"],
                "tipo_item": row["tipo_item"],
                "descripcion": row["descripcion"],
                "cantidad": row["cantidad"],
                "unidad_medida": row["unidad_medida"],
                "lote": row["lote"],
                "detalles": row["detalles"],
                "fecha_vencimiento": row["fecha_vencimiento"]
            })
        return transfer_data_list
    except Exception as e:
        print(f"Error al obtener la lista de inventario almacenado: {e}")
        return []


async def get_inventory_consolidated(db: AsyncSession):
    """Obtiene el inventario consolidado por item y lote."""
    query = text("""
                    SELECT
                        i.id_item,
                        it.cod_item,
                        it.descripcion,
                        it.tipo_item,
                        it.unidad_medida,
                        i.lote,
                        SUM(i.cantidad) AS cantidad
                    FROM inventario AS i
                    INNER JOIN items AS it ON i.id_item = it.id
                    GROUP BY
                        i.id_item,
                        it.cod_item,
                        it.descripcion,
                        it.tipo_item,
                        it.unidad_medida,
                        i.lote
                    ORDER BY
                        it.descripcion ASC,
                        i.lote ASC NULLS LAST
                 """)
    try:
        result = await db.execute(query)
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error al obtener el consolidado de inventario: {e}")
        return []
    

# ****************************** FUNCION DE INVENTARIAR ******************************
async def get_invAux(db: AsyncSession, invAux: InvAux):
    """Consulta el inventario auxiliar por id_posicion, id_item y lote."""
    invAux_data = InvAux()
    query = text("""
                 SELECT id, id_posicion, id_item, lote,
                        fecha AS fecha_vencimiento, estado
                 FROM inv_aux
                 WHERE id_posicion = :id_posicion AND id_item = :id_item AND lote = :lote
                 """)
    try:
        result = await db.execute(query, {"id_posicion": invAux.id_posicion, "id_item": invAux.id_item, "lote": invAux.lote})
        row = result.mappings().first()
        if row:
            invAux_data = InvAux(**dict(row))
            invAux_data.result = 1
            invAux_data.message = "Inventario auxiliar encontrado"
        else:
            invAux_data.result = 2
            invAux_data.message = "Inventario auxiliar no encontrado"
        return invAux_data
    except Exception as e:
        print(f"Error al obtener el inventario auxiliar: {e}")
        invAux_data.result = 0
        invAux_data.message = "Error al obtener el inventario auxiliar"
        return invAux_data


async def get_invAux_by_id(db: AsyncSession, id_invAux: int):
    """Consulta el inventario auxiliar por su identificador."""
    invAux_data = InvAux()
    query = text("""
                 SELECT id, id_posicion, id_item, lote,
                        fecha AS fecha_vencimiento, estado
                 FROM inv_aux
                 WHERE id = :id
                 """)
    try:
        result = await db.execute(query, {"id": id_invAux})
        row = result.mappings().first()
        if row:
            invAux_data = InvAux(**dict(row))
            invAux_data.result = 1
            invAux_data.message = "Inventario auxiliar encontrado"
        else:
            invAux_data.result = 0
            invAux_data.message = "Inventario auxiliar no encontrado"
        return invAux_data
    except Exception as e:
        print(f"Error al obtener el inventario auxiliar por id: {e}")
        invAux_data.result = 0
        invAux_data.message = "Error al obtener el inventario auxiliar"
        return invAux_data
    
async def create_input_invAux(db: AsyncSession, invAux: InvAux):
    """Crea un registro de inventario auxiliar."""
    invAux_data = InvAux()
    query = text("""
                 INSERT INTO inv_aux (id_posicion, id_item, lote, fecha, estado)
                 VALUES (:id_posicion, :id_item, :lote, :fecha, :estado)
                 RETURNING id, id_posicion, id_item, lote,
                           fecha AS fecha_vencimiento, estado
                 """)
    try:
        result = await db.execute(query, {"id_posicion": invAux.id_posicion, "id_item": invAux.id_item, "lote": invAux.lote, "fecha": invAux.fecha_vencimiento, "estado": invAux.estado})
        row = result.mappings().first()
        await db.commit()
        if row:
            invAux_data = InvAux(**dict(row))
            invAux_data.result = 1
            invAux_data.message = "Inventario auxiliar creado exitosamente"
        else:
            invAux_data.result = 0
            invAux_data.message = "Error al crear el inventario auxiliar"
        return invAux_data
    except Exception as e:
        print(f"Error al crear el inventario auxiliar: {e}")
        await db.rollback()
        invAux_data.result = 0
        invAux_data.message = "Error al crear el inventario auxiliar"
        return invAux_data
    

async def create_input_invAuxCont(db: AsyncSession, invAuxCont: InvAuxCont):
    """Crea un registro de inventario auxiliar de conteo"""
    invAuxCont_data = InvAuxCont()
    query = text("""
                INSERT INTO inv_conteo (id_inv_aux, num_cont, cantidad, fecha, id_usuario)
                VALUES (:id_inv_aux, :num_cont, :cantidad, :fecha, :id_usuario)
                RETURNING id, id_inv_aux AS "id_invAux",
                          num_cont AS "numCont", cantidad, fecha, id_usuario
             """)
    try:
        result = await db.execute(query, {"id_inv_aux": invAuxCont.id_invAux, "num_cont": invAuxCont.numCont, "cantidad": invAuxCont.cantidad, "fecha": invAuxCont.fecha, "id_usuario": invAuxCont.id_usuario})
        row = result.mappings().first()
        await db.commit()
        if row:
            invAuxCont_data = InvAuxCont(**dict(row))
            invAuxCont_data.result = 1
            invAuxCont_data.message = "Inventario auxiliar de conteo creado exitosamente"
        else:
            invAuxCont_data.result = 0
            invAuxCont_data.message = "Error al crear el inventario auxiliar de conteo"
        return invAuxCont_data
    except Exception as e:
        print(f"Error al crear el inventario auxiliar de conteo: {e}")
        await db.rollback()
        invAuxCont_data.result = 0
        invAuxCont_data.message = "Error al crear el inventario auxiliar de conteo"
        return invAuxCont_data
    
async def get_invAuxCont(db: AsyncSession, id_invAux:int):
    """Consulta el inventario auxiliar de conteo por id_inv_aux."""
    invAuxCont_data = InvAuxCont()
    query = text("""
                 SELECT id, id_inv_aux AS "id_invAux",
                        num_cont AS "numCont", cantidad, fecha, id_usuario
                 FROM inv_conteo
                 WHERE id_inv_aux = :id_inv_aux
                 ORDER BY num_cont DESC
                 LIMIT 1
                 """)
    try:
        result = await db.execute(query, {"id_inv_aux": id_invAux})
        row = result.mappings().first()
        if row:
            invAuxCont_data = InvAuxCont(**dict(row))
            invAuxCont_data.result = 1
            invAuxCont_data.message = "Inventario auxiliar de conteo encontrado"
        else:
            invAuxCont_data.result = 0
            invAuxCont_data.message = "Inventario auxiliar de conteo no encontrado"
        return invAuxCont_data
    except Exception as e:
        print(f"Error al obtener el inventario auxiliar de conteo: {e}")
        invAuxCont_data.result = 0
        invAuxCont_data.message = "Error al obtener el inventario auxiliar de conteo"
        return invAuxCont_data
    
async def update_input_invAux(db: AsyncSession, invAux: InvAux):
    """Actualiza el estado del inventario auxiliar."""
    invAux_data = InvAux()
    query = text("""
                 UPDATE inv_aux
                 SET estado = :estado
                 WHERE id = :id
                 RETURNING id, id_posicion, id_item, lote,
                           fecha AS fecha_vencimiento, estado
                 """)
    try:
        result = await db.execute(query, {"id": invAux.id, "estado": invAux.estado})
        row = result.mappings().first()
        await db.commit()
        if row:
            invAux_data = InvAux(**dict(row))
            invAux_data.result = 1
            invAux_data.message = "Inventario auxiliar actualizado exitosamente"
        else:
            invAux_data.result = 0
            invAux_data.message = "Error al actualizar el inventario auxiliar"
        return invAux_data
    except Exception as e:
        print(f"Error al actualizar el inventario auxiliar: {e}")
        await db.rollback()
        invAux_data.result = 0
        invAux_data.message = "Error al actualizar el inventario auxiliar"
        return invAux_data
    
async def get_invAuxCont_by_numCont(db, id_invAux, number):
    """Consulta el inventario auxiliar de conteo por id_inv_aux y num_cont."""
    invAuxCont_data = InvAuxCont()
    query = text("""
                 SELECT id, id_inv_aux AS "id_invAux",
                        num_cont AS "numCont", cantidad, fecha, id_usuario
                 FROM inv_conteo
                 WHERE id_inv_aux = :id_inv_aux AND num_cont = :num_cont
                 """)
    try:
        result = await db.execute(query, {"id_inv_aux": id_invAux, "num_cont": number})
        row = result.mappings().first()
        if row:
            invAuxCont_data = InvAuxCont(**dict(row))
            invAuxCont_data.result = 1
            invAuxCont_data.message = "Inventario auxiliar de conteo encontrado"
        else:
            invAuxCont_data.result = 0
            invAuxCont_data.message = "Inventario auxiliar de conteo no encontrado"
        return invAuxCont_data
    except Exception as e:
        print(f"Error al obtener el inventario auxiliar de conteo por num_cont: {e}")
        invAuxCont_data.result = 0
        invAuxCont_data.message = "Error al obtener el inventario auxiliar de conteo"
        return invAuxCont_data  
    

async def list_inv_aux_pending(db: AsyncSession):
    """Obtiene los inventarios auxiliares pendientes con todos sus conteos."""
    query = text("""
                    SELECT 
                        ia.id,
                        ia.id_posicion,
                        ia.id_item,
                        p.cod_posicion,
                        ia.estado,
                        it.cod_item,
                        it.descripcion,
                        ia.lote,
                        ia.fecha,
                        it.tipo_item,
                        it.unidad_medida,
                        ic.id AS id_conteo, ic.num_cont, ic.cantidad AS cantidad_conteo,
                        ic.fecha AS fecha_conteo, ic.id_usuario
                    FROM inv_aux AS ia
                    LEFT JOIN posiciones AS p ON ia.id_posicion = p.id
                    LEFT JOIN items AS it ON ia.id_item = it.id
                    LEFT JOIN inv_conteo AS ic ON ic.id_inv_aux = ia.id
                    WHERE ia.estado IN (1, 2, 3, 4, 6)
                    ORDER BY
                        ia.estado ASC,
                        p.cod_posicion ASC NULLS LAST,
                        it.descripcion ASC,
                        ia.lote ASC,
                        ic.num_cont ASC
                 """)
    try:
        result = await db.execute(query)
        rows = result.mappings().all()

        pending_by_id = {}
        for row in rows:
            inv_aux = pending_by_id.setdefault(
                row["id"],
                {
                    "id": row["id"],
                    "id_posicion": row["id_posicion"],
                    "cod_posicion": row["cod_posicion"],
                    "id_item": row["id_item"],
                    "tipo_item": row["tipo_item"],
                    "descripcion": row["descripcion"],
                    "unidad_medida": row["unidad_medida"],
                    "lote": row["lote"],
                    "fecha": row["fecha"],
                    "estado": row["estado"],
                    "conteo_1": None,
                    "conteo_2": None,
                    "conteos_adicionales": [],
                },
            )

            if row["id_conteo"] is None:
                continue

            conteo = {
                "id": row["id_conteo"],
                "num_cont": row["num_cont"],
                "cantidad": row["cantidad_conteo"],
                "fecha": row["fecha_conteo"],
                "id_usuario": row["id_usuario"],
            }

            if row["num_cont"] == 1:
                inv_aux["conteo_1"] = conteo
            elif row["num_cont"] == 2:
                inv_aux["conteo_2"] = conteo
            else:
                inv_aux["conteos_adicionales"].append(conteo)

        return list(pending_by_id.values())
    except Exception as e:
        print(f"Error al obtener la lista de inventario auxiliar pendiente: {e}")
        return []


async def get_next_numCont(db: AsyncSession, id_invAux: int):
    """Obtiene el siguiente número de conteo para un inventario auxiliar específico."""
    query = text("""
                 SELECT COALESCE(MAX(num_cont), 0) + 1 AS next_num_cont
                 FROM inv_conteo
                 WHERE id_inv_aux = :id_inv_aux
                 """)
    try:
        result = await db.execute(query, {"id_inv_aux": id_invAux})
        row = result.mappings().first()
        if row:
            return row["next_num_cont"]
        else:
            return 1  # Si no hay registros, el siguiente número de conteo es 1
    except Exception as e:
        print(f"Error al obtener el siguiente número de conteo: {e}")
        return 1  # En caso de error, retornar 1 como valor por defecto