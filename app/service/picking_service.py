import csv
import io
import json
import re
import unicodedata
from collections import OrderedDict
from decimal import Decimal, InvalidOperation

from app.repository import picking_repository, order_repository, inventory_repository, motion_repository
from app.model.picking_model import Orden, Picking, Picking_detalle
from app.model.inventory_model import Motion
from datetime import datetime


REQUIRED_IMPORT_COLUMNS = {
    "codigo": {"nro documento", "nro. documento", "numero documento", "codigo", "código"},
    "cliente": {"razon social cliente factura", "cliente", "razon social", "razón social cliente factura"},
    "cod_item": {"referencia"},
    "cantidad": {"cantidad", "cant. pendiente", "cant pendiente", "cantidad pendiente"},
    "bodega": {"bodega"},
}

OPTIONAL_IMPORT_COLUMNS = {
    "fecha": {"fecha"},
    "estado": {"estado movto.", "estado movto", "estado"},
    "lote": {"lote"},
    "detalles": {"cliente factura", "detalles", "detalle"},
}


def _normalise_header(value) -> str:
    value = unicodedata.normalize("NFD", str(value or "").strip().casefold())
    value = "".join(character for character in value if unicodedata.category(character) != "Mn")
    return re.sub(r"\s+", " ", value)


def _normalise_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _is_blank_row(row: dict) -> bool:
    """Distingue una fila vacía de una fila de pedido incompleta."""
    return all(not _normalise_value(value) for value in row.values())


def _parse_quantity(value) -> int:
    raw = _normalise_value(value).replace(" ", "")
    if not raw:
        raise ValueError("la cantidad está vacía")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    quantity = Decimal(raw)
    if quantity <= 0 or quantity != quantity.to_integral_value():
        raise ValueError("la cantidad debe ser un entero mayor que cero")
    return int(quantity)


def _read_import_rows(content: bytes, extension: str) -> list[dict]:
    if extension == "csv":
        try:
            text_content = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text_content = content.decode("latin-1")
        try:
            dialect = csv.Sniffer().sniff(text_content[:4096], delimiters=";,\t")
        except csv.Error:
            return list(csv.DictReader(io.StringIO(text_content), delimiter=";"))
        return list(csv.DictReader(io.StringIO(text_content), dialect=dialect))
    try:
        from openpyxl import load_workbook
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        rows = workbook.active.iter_rows(values_only=True)
        headers = next(rows, None)
        if not headers:
            return []
        return [dict(zip(headers, row)) for row in rows if any(value is not None for value in row)]
    except Exception as error:
        raise ValueError(f"No fue posible leer el archivo XLSX: {error}") from error


def _column_mapping(rows: list[dict]) -> dict[str, str]:
    if not rows:
        raise ValueError("El archivo no contiene filas de datos")
    headers = {_normalise_header(header): header for header in rows[0].keys()}
    mapping, missing = {}, []
    for field, aliases in REQUIRED_IMPORT_COLUMNS.items():
        header = next(
            (headers[_normalise_header(alias)] for alias in aliases if _normalise_header(alias) in headers),
            None,
        )
        if header is None:
            missing.append(field)
        else:
            mapping[field] = header
    if missing:
        labels = {
            "codigo": "Nro documento",
            "cliente": "Razón social cliente factura",
            "cod_item": "Referencia",
            "cantidad": "Cantidad",
            "bodega": "Bodega",
        }
        raise ValueError("Faltan columnas obligatorias: " + ", ".join(labels[item] for item in missing))
    for field, aliases in OPTIONAL_IMPORT_COLUMNS.items():
        mapping[field] = next(
            (headers[_normalise_header(alias)] for alias in aliases if _normalise_header(alias) in headers),
            None,
        )
    return mapping


async def import_orders_file(db, content: bytes, extension: str, id_usuario: int) -> dict:
    """Importa pedidos aprobados, agrupándolos por documento de venta."""
    try:
        rows = _read_import_rows(content, extension)
        columns = _column_mapping(rows)
    except ValueError as error:
        return {"result": 0, "message": str(error)}

    orders: OrderedDict[str, dict] = OrderedDict()
    errors, skipped_rows = [], 0
    for row_number, row in enumerate(rows, start=2):
        # Los CSV/XLSX exportados desde Excel suelen conservar filas vacías al
        # final. No representan pedidos ni deben impedir la importación.
        if _is_blank_row(row):
            skipped_rows += 1
            continue
        bodega = _normalise_value(row.get(columns["bodega"])) if columns["bodega"] else ""
        # Solo se importan las filas de bodegas cuyo nombre o código comienza por M.
        if not bodega.casefold().startswith("m"):
            skipped_rows += 1
            continue
        status = _normalise_value(row.get(columns["estado"])) if columns["estado"] else ""
        if status and _normalise_header(status) != "aprobada":
            skipped_rows += 1
            continue
        codigo = _normalise_value(row.get(columns["codigo"]))
        cliente = _normalise_value(row.get(columns["cliente"]))
        cod_item = _normalise_value(row.get(columns["cod_item"]))
        lote = _normalise_value(row.get(columns["lote"])) if columns["lote"] else ""
        detalles = _normalise_value(row.get(columns["detalles"])) if columns["detalles"] else ""
        try:
            cantidad = _parse_quantity(row.get(columns["cantidad"]))
        except (InvalidOperation, ValueError) as error:
            errors.append(f"Fila {row_number}: {error}")
            continue
        if not codigo or not cliente or not cod_item:
            errors.append(f"Fila {row_number}: documento, cliente e Id item son obligatorios")
            continue
        order = orders.setdefault(codigo, {
            "codigo": codigo, "cliente": cliente, "items": OrderedDict(),
            "fecha": _normalise_value(row.get(columns["fecha"])) if columns["fecha"] else "",
            "bodega": bodega,
            "detalles": detalles,
        })
        if order["cliente"] != cliente:
            errors.append(f"Fila {row_number}: el documento {codigo} tiene clientes distintos")
            continue
        item_key = (cod_item, lote)
        order["items"][item_key] = order["items"].get(item_key, 0) + cantidad
    if not orders:
        return {"result": 0, "message": "No hay filas aprobadas para importar"}
    if errors:
        return {"result": 0, "message": "El archivo tiene errores y no se importó ninguna orden: " + "; ".join(errors[:10])}

    item_codes = list({code for order in orders.values() for code, _ in order["items"]})
    items_by_code = await picking_repository.get_items_by_codes(db, item_codes)
    missing_codes = sorted(set(item_codes) - set(items_by_code))
    if missing_codes:
        return {"result": 0, "message": "No existen artículos para los códigos: " + ", ".join(missing_codes[:20])}
    existing_codes = await picking_repository.get_existing_order_codes(db, list(orders))
    if existing_codes:
        return {"result": 0, "message": "Ya existen órdenes con los códigos: " + ", ".join(sorted(existing_codes)[:20])}

    inventory = await picking_repository.get_inventory_for_items(db, [item["id"] for item in items_by_code.values()])
    available = {item_id: [dict(entry) for entry in entries] for item_id, entries in inventory.items()}
    orders_to_create, stock_errors = [], []
    for order in orders.values():
        tasks = []
        for (item_code, requested_lot), requested in order["items"].items():
            item, pending = items_by_code[item_code], requested
            for entry in available.get(item["id"], []):
                if pending == 0:
                    break
                inventory_lot = _normalise_value(entry["lote"])
                if requested_lot and inventory_lot.casefold() != requested_lot.casefold():
                    continue
                assigned = min(pending, int(entry["cantidad"]))
                if assigned:
                    tasks.append({"id_item": item["id"], "cantidad": assigned, "lote": entry["lote"], "id_posicion_origen": entry["id_posicion"]})
                    entry["cantidad"] -= assigned
                    pending -= assigned
            if pending:
                lot_label = f", lote {requested_lot}" if requested_lot else ""
                stock_errors.append(f"orden {order['codigo']}, artículo {item_code}{lot_label}: faltan {pending} unidades")
        details = {
            "fecha": order["fecha"],
            "bodega": order["bodega"],
            "detalles": order["detalles"],
            "origen": "importacion_archivo",
        }
        orders_to_create.append({"codigo": order["codigo"], "cliente": order["cliente"], "id_usuario": id_usuario,
                                 "tipo": "OF", "detalles": json.dumps(details, ensure_ascii=False), "tasks": tasks})
    if stock_errors:
        return {"result": 0, "message": "Inventario insuficiente: " + "; ".join(stock_errors[:20])}
    try:
        created = await picking_repository.create_bulk_pickings(db, orders_to_create)
        await db.commit()
    except Exception as error:
        await db.rollback()
        return {"result": 0, "message": f"No fue posible crear las órdenes: {error}"}
    return {"result": 1, "message": f"Se crearon {len(created)} órdenes de salida y sus pickings.",
            "created_orders": len(created), "created_pickings": len(created), "skipped_rows": skipped_rows, "orders": created}

async def create_picking(db, orden: Orden, picking_data: Picking, picking_detalle: Picking_detalle):
    create_order = await order_repository.create_order(db, orden)
    if create_order.result == 1:
        picking_data.id_orden = create_order.id
        create_picking_data = await picking_repository.create_picking(db, picking_data)
        if create_picking_data.result == 1:
            picking_detalle.id_picking = create_picking_data.id
            create_picking_detalle = await picking_repository.create_picking_detalle(db, picking_detalle)
            if create_picking_detalle.result == 1:
                for item in picking_detalle.items:
                    item_data = await inventory_repository.get_position_by_item(db, item.id_item, item.lote)
                    item.id_posicion_origen = item_data.id_posicion_origen
                create_picking_task = await picking_repository.create_picking_task(db, picking_detalle)
                if create_picking_task.result == 1:
                    return create_picking_data
                else:
                    return create_picking_data
            else:
                return create_picking_data
        else:
            return create_picking_data
    else:
        return create_order
        # return picking_data
    


async def get_next_task(db, id_picking: int):
    """Obtiene la siguiente tarea pendiente del picking."""
    task = await picking_repository.get_next_task(db, id_picking)
    if task.result == 0:
        result = await picking_repository.complete_picking(db, id_picking)
        if result["result"] == 1:
            order_data = await order_repository.update_order_status_by_picking(db, id_picking)
            if order_data.result == 1:
                return {"completed":True, "message": "No hay más tareas pendientes. Picking completado."}
            else:
                return {"completed":False, "message": "Error al actualizar el estado de la orden"}
        else:
            return {"completed":False, "message": "Error al completar el picking"}
    return {"completed":False , "task": task}

# ACTUALIZAR ESTADO DE ORDEN ACA MISMO, DESPUES DE CONFIRMAR LA PRIMERA TAREA, SE CAMBIA EL ESTADO DE LA ORDEN
# Y CUANDO SE FINALICE Y NO HAYA UNA TAREA MAS SE FINALIZA LA ORDEN
async def confirm_task(db, id_task: int, id_picking: int, cod_posicion_escaneada: int, cod_item: str, id_usuario: int):
    """
    Confirma una tarea de picking después de escanear la posición de origen.
    Registra el movimiento y actualiza el inventario.
    """
    # Obtener la información de la tarea
    task = await picking_repository.get_next_task(db, id_picking)
    
    if task.result == 0:
        return {"result": 0, "message": "Tarea no encontrada"}
    
    # Validar que la posición escaneada sea correcta
    if cod_posicion_escaneada != task.cod_posicion_origen:
        return {"result": 0, "message": f"Posición incorrecta. Se esperaba {task.id_posicion_origen}, se escaneó {cod_posicion_escaneada}"}
    
    if cod_item != task.cod_item:
        return {"result": 0, "message": f"Item incorrecto. Se esperaba {task.cod_item} {task.nombre_item}, se escaneó {cod_item}"}
    
    try:
        # Crear registro de movimiento (salida/picking)
        # tipo_movimiento: 1=ENTRADA, 2=SALIDA
        motion = Motion(
            tipo_movimiento=2,  # SALIDA
            id_item=task.id_item,
            lote=task.lote,
            cantidad=task.cantidad,
            posicion_origen_id=task.id_posicion_origen,
            posicion_destino_id=None,  # No hay posición destino en picking
            fecha=datetime.now(),
            id_usuario=id_usuario
        )
        
        motion_result = await motion_repository.create_motion_output(db, motion)
        
        if motion_result.result == 0:
            return {"result": 0, "message": "Error al registrar el movimiento"}
        
        # Actualizar inventario (restar la cantidad)
        inventory_result = await inventory_repository.update_inventory_quantity(
            db, task.id_posicion_origen, task.id_item, task.lote, task.cantidad
        )
        
        if inventory_result["result"] == 0:
            return {"result": 0, "message": "Error al actualizar el inventario"}
        
        # Actualizar estado de la tarea a completada (estado = 3)
        task_update = await picking_repository.update_task_status(db, id_task, 3)
        task_update = await picking_repository.delete_task(db, id_task)
        order_data = await picking_repository.get_order_id_by_picking(db, id_picking)
        if order_data.estado == 1:
            order_data.estado = 2
            order_update = await order_repository.update_order_status(db, order_data)
            if order_update.result == 0:
                return {"result": 0, "message": "Error al actualizar el estado de la orden"}
            
        
        
        if task_update["result"] == 0:
            return {"result": 0, "message": "Error al actualizar el estado de la tarea"}
        
        return {"result": 1, "message": "Tarea confirmada exitosamente", 
                "id_movimiento": motion_result.id}
        
    except Exception as e:
        print(f"Error al confirmar la tarea: {e}")
        return {"result": 0, "message": f"Error al confirmar la tarea: {str(e)}"}
    
    
async def list_picking_view(db):
    """Lista los pickings con su información detallada para la vista."""
    picking_view_list = await picking_repository.list_picking_view(db)
    return picking_view_list

async def get_list_orders(db):
    return await order_repository.get_list_orders(db)
