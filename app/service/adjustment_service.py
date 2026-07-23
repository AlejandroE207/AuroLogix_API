from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repository import adjustment_repository

# Tipos de movimiento para ajustes (deben existir en la tabla tipo_movimientos)
MOTION_AJUSTE_POSITIVO = 4
MOTION_AJUSTE_NEGATIVO = 5

# Tipos de ajuste registrados en inventario_ajustes
AJUSTE_MODIFICACION = "MODIFICACION"
AJUSTE_FUSION = "FUSION"
AJUSTE_ELIMINACION = "ELIMINACION"


def _normalize_lote(lote):
    """Trata cadenas vacias o de solo espacios como NULL, igual que el resto del sistema."""
    if lote is None:
        return None
    lote = str(lote).strip()
    return lote if lote else None


def _dates_equal(a, b):
    """Compara fechas de vencimiento tolerando None y diferencias de tipo date/datetime."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    a_date = a.date() if isinstance(a, datetime) else a
    b_date = b.date() if isinstance(b, datetime) else b
    return a_date == b_date


async def get_inventory_by_position(db: AsyncSession, id_posicion: int):
    """Lista los registros de inventario de una posicion para la pantalla de edicion."""
    return await adjustment_repository.get_inventory_by_position(db, id_posicion)


async def update_position_inventory(db: AsyncSession, id_inventario: int, id_item: int,
                                    lote: str, cantidad: float, fecha_vencimiento: datetime,
                                    motivo: str, id_usuario: int):
    """Actualiza un registro de inventario de una posicion dejando trazabilidad completa.

    Reglas:
    - Todo cambio queda registrado en inventario_ajustes (valores anteriores y nuevos,
      motivo obligatorio, usuario y fecha).
    - Los cambios que afectan cantidades tambien generan movimientos de ajuste
      (tipo 4 = ajuste positivo, tipo 5 = ajuste negativo) para que el kardex de
      movimientos siga cuadrando con el inventario.
    - Si el cambio de item/lote colisiona con otro registro existente en la misma
      posicion (mismo item + lote), se FUSIONA sumando la cantidad al registro
      existente y el registro editado desaparece (el trigger de la BD elimina
      filas con cantidad 0).
    - Toda la operacion es atomica: un solo commit al final.
    """
    # ---------- Validaciones ----------
    motivo = (motivo or "").strip()
    if not motivo:
        return {"result": 0, "message": "El motivo del ajuste es obligatorio"}

    if cantidad is None or cantidad < 0:
        return {"result": 0, "message": "La cantidad no puede ser negativa"}

    current = await adjustment_repository.get_inventory_record(db, id_inventario)
    if not current:
        return {"result": 0, "message": "El registro de inventario no existe"}

    lote = _normalize_lote(lote)
    lote_anterior = _normalize_lote(current["lote"])

    item_changed = id_item != current["id_item"]
    if item_changed and not await adjustment_repository.item_exists(db, id_item):
        return {"result": 0, "message": "El item indicado no existe"}

    lote_changed = lote != lote_anterior
    cantidad_anterior = float(current["cantidad"] or 0)
    quantity_changed = float(cantidad) != cantidad_anterior
    fecha_changed = not _dates_equal(fecha_vencimiento, current["fecha_vencimiento"])

    if not (item_changed or lote_changed or quantity_changed or fecha_changed):
        return {"result": 2, "message": "No se detectaron cambios en el registro"}

    identity_changed = item_changed or lote_changed
    id_posicion = current["id_posicion"]
    now = datetime.now()

    adjustment_base = {
        "id_inventario": id_inventario,
        "id_inventario_destino": None,
        "id_posicion": id_posicion,
        "id_item_anterior": current["id_item"],
        "id_item_nuevo": id_item,
        "lote_anterior": lote_anterior,
        "lote_nuevo": lote,
        "cantidad_anterior": cantidad_anterior,
        "cantidad_nueva": cantidad,
        "fecha_vencimiento_anterior": current["fecha_vencimiento"],
        "fecha_vencimiento_nueva": fecha_vencimiento,
        "motivo": motivo,
        "id_usuario": id_usuario,
        "fecha": now,
    }

    try:
        merged = False

        if identity_changed:
            # El item o el lote cambiaron: en el kardex esto es una salida del
            # item/lote anterior y una entrada del item/lote nuevo.
            target = await adjustment_repository.find_merge_target(
                db, id_posicion, id_item, lote, exclude_id=id_inventario
            )

            if target:
                # FUSION: sumar la cantidad al registro existente y vaciar el editado
                merged = True
                adjustment_base["tipo_ajuste"] = AJUSTE_FUSION
                adjustment_base["id_inventario_destino"] = target["id"]

                ok = await adjustment_repository.add_quantity_to_target(
                    db, target["id"], cantidad, fecha_vencimiento
                )
                if not ok:
                    raise RuntimeError("No se pudo actualizar el registro destino de la fusion")

                # Eliminacion explicita del registro original (sin depender del trigger)
                ok = await adjustment_repository.delete_record(db, id_inventario)
                if not ok:
                    raise RuntimeError("No se pudo eliminar el registro de inventario original")
            else:
                adjustment_base["tipo_ajuste"] = AJUSTE_MODIFICACION
                ok = await adjustment_repository.update_record(
                    db, id_inventario, id_item, lote, cantidad, fecha_vencimiento
                )
                if not ok:
                    raise RuntimeError("No se pudo actualizar el registro de inventario")

                if float(cantidad) == 0:
                    await adjustment_repository.delete_record(db, id_inventario)

            # Movimiento de ajuste negativo por la cantidad anterior (item/lote viejos)
            if cantidad_anterior > 0:
                motion_id = await adjustment_repository.insert_adjustment_motion(
                    db, MOTION_AJUSTE_NEGATIVO, current["id_item"], lote_anterior,
                    cantidad_anterior, id_posicion, id_usuario, now
                )
                if motion_id is None:
                    raise RuntimeError("No se pudo registrar el movimiento de ajuste negativo")

            # Movimiento de ajuste positivo por la cantidad nueva (item/lote nuevos)
            if cantidad > 0:
                motion_id = await adjustment_repository.insert_adjustment_motion(
                    db, MOTION_AJUSTE_POSITIVO, id_item, lote,
                    cantidad, id_posicion, id_usuario, now
                )
                if motion_id is None:
                    raise RuntimeError("No se pudo registrar el movimiento de ajuste positivo")
        else:
            # Mismo item y lote: solo cambian cantidad y/o fecha de vencimiento
            adjustment_base["tipo_ajuste"] = AJUSTE_MODIFICACION
            ok = await adjustment_repository.update_record(
                db, id_inventario, id_item, lote, cantidad, fecha_vencimiento
            )
            if not ok:
                raise RuntimeError("No se pudo actualizar el registro de inventario")

            if float(cantidad) == 0:
                await adjustment_repository.delete_record(db, id_inventario)

            if quantity_changed:
                delta = float(cantidad) - cantidad_anterior
                tipo = MOTION_AJUSTE_POSITIVO if delta > 0 else MOTION_AJUSTE_NEGATIVO
                motion_id = await adjustment_repository.insert_adjustment_motion(
                    db, tipo, id_item, lote, abs(delta), id_posicion, id_usuario, now
                )
                if motion_id is None:
                    raise RuntimeError("No se pudo registrar el movimiento de ajuste")

        adjustment_id = await adjustment_repository.insert_adjustment(db, adjustment_base)
        if adjustment_id is None:
            raise RuntimeError("No se pudo registrar el ajuste en el historial")

        await db.commit()

        if merged:
            message = "Registro fusionado con el inventario existente de la posicion"
        elif cantidad == 0:
            message = "Inventario actualizado; el registro quedo en 0 y fue retirado de la posicion"
        else:
            message = "Inventario actualizado exitosamente"

        return {"result": 1, "message": message, "id_ajuste": adjustment_id, "fusionado": merged}

    except Exception as e:
        print(f"Error al actualizar el inventario de la posicion: {e}")
        await db.rollback()
        return {"result": 0, "message": "Error al actualizar el inventario de la posicion"}


async def delete_position_inventory(db: AsyncSession, id_inventario: int, motivo: str, id_usuario: int):
    """Retira por completo un item de una posicion dejando trazabilidad.

    Se registra el ajuste como ELIMINACION en el historial, se genera un
    movimiento de ajuste negativo por la cantidad total y el registro se
    lleva a cantidad 0 (el trigger de la BD elimina la fila).
    """
    motivo = (motivo or "").strip()
    if not motivo:
        return {"result": 0, "message": "El motivo de la eliminacion es obligatorio"}

    current = await adjustment_repository.get_inventory_record(db, id_inventario)
    if not current:
        return {"result": 0, "message": "El registro de inventario no existe"}

    cantidad_anterior = float(current["cantidad"] or 0)
    lote_anterior = _normalize_lote(current["lote"])
    now = datetime.now()

    try:
        ok = await adjustment_repository.delete_record(db, id_inventario)
        if not ok:
            raise RuntimeError("No se pudo eliminar el registro de inventario")

        if cantidad_anterior > 0:
            motion_id = await adjustment_repository.insert_adjustment_motion(
                db, MOTION_AJUSTE_NEGATIVO, current["id_item"], lote_anterior,
                cantidad_anterior, current["id_posicion"], id_usuario, now
            )
            if motion_id is None:
                raise RuntimeError("No se pudo registrar el movimiento de ajuste negativo")

        adjustment_id = await adjustment_repository.insert_adjustment(db, {
            "id_inventario": id_inventario,
            "id_inventario_destino": None,
            "id_posicion": current["id_posicion"],
            "tipo_ajuste": AJUSTE_ELIMINACION,
            "id_item_anterior": current["id_item"],
            "id_item_nuevo": None,
            "lote_anterior": lote_anterior,
            "lote_nuevo": None,
            "cantidad_anterior": cantidad_anterior,
            "cantidad_nueva": 0,
            "fecha_vencimiento_anterior": current["fecha_vencimiento"],
            "fecha_vencimiento_nueva": None,
            "motivo": motivo,
            "id_usuario": id_usuario,
            "fecha": now,
        })
        if adjustment_id is None:
            raise RuntimeError("No se pudo registrar el ajuste en el historial")

        await db.commit()
        return {"result": 1, "message": "Item retirado de la posicion exitosamente", "id_ajuste": adjustment_id}

    except Exception as e:
        print(f"Error al eliminar el inventario de la posicion: {e}")
        await db.rollback()
        return {"result": 0, "message": "Error al retirar el item de la posicion"}


async def list_adjustments(db: AsyncSession, cod_posicion: str = None, item: str = None,
                           desde_fecha: datetime = None, hasta_fecha: datetime = None,
                           limite: int = 50, offset: int = 0):
    """Devuelve el historial de ajustes de inventario con filtros opcionales.

    - cod_posicion: busqueda parcial por codigo de posicion (ej. 'R6-N1-P2' o 'R6-N1').
    - item: busqueda parcial por cod_item o descripcion, tanto del item
      anterior como del item nuevo del ajuste.
    """
    data = await adjustment_repository.list_adjustments(
        db, cod_posicion, item, desde_fecha, hasta_fecha, limite, offset
    )
    if data:
        return {"result": 1, "message": "Historial de ajustes encontrado", "data": data}
    return {"result": 0, "message": "No se encontraron ajustes", "data": []}