from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.model.picking_model import Orden
from app.model.order_view_model import OrderView, ItemsOrderView

async def create_order (db:AsyncSession, orden: Orden):
    order_data = Orden()
    query = text("""
                 INSERT INTO orden_salida (codigo, cliente, estado, id_usuario)
                 VALUES (:codigo, :cliente, :estado, :id_usuario)
                RETURNING id, codigo, cliente, estado, id_usuario
                 """)
    
    try:
        result = await db.execute(query, {"codigo": orden.codigo, "cliente": orden.cliente, 
                                          "estado": orden.estado, "id_usuario": orden.id_usuario})
        row = result.mappings().first()
        await db.commit()
        if row:
            order_data = Orden(**dict(row))
            order_data.result = 1
            order_data.message = "Orden creada exitosamente"
        else:
            order_data.result = 0
            order_data.message = "Error al crear la orden"
        return order_data
    except Exception as e:
        print(f"Error al crear la orden: {e}")
        order_data.result = 0
        order_data.message = "Error al crear la orden"
        if "codigo_unique" in str(e):
            order_data.message = "El código de la orden ya existe. Por favor, elija un código diferente."
        return order_data
    
    
async def update_order_status(db:AsyncSession, order_data: Orden):
    query = text("""
                 UPDATE orden_salida
                 SET estado = :estado
                 WHERE id = :id
                 RETURNING id, codigo, cliente, estado, id_usuario
                 """)
    try:
        result = await db.execute(query, {"estado": order_data.estado, "id": order_data.id})
        row = result.mappings().first()
        await db.commit()
        if row:
            updated_order = Orden(**dict(row))
            updated_order.result = 1
            updated_order.message = "Estado de la orden actualizado exitosamente"
            return updated_order
        else:
            order_data.result = 0
            order_data.message = "Error al actualizar el estado de la orden"
            return order_data
    except Exception as e:
        print(f"Error al actualizar el estado de la orden: {e}")
        db.rollback()
        order_data.result = 0
        order_data.message = "Error al actualizar el estado de la orden"
        return order_data
    
async def update_order_status_by_picking(db: AsyncSession, id_picking: int):
    query = text("""
                 UPDATE orden_salida
                 SET estado = 3
                 WHERE id IN (
                    SELECT id_orden
                    FROM picking
                    WHERE id = :id_picking
                 )
                 RETURNING id, codigo, cliente, estado, id_usuario
                 """)
    try:
        result = await db.execute(query, {"id_picking": id_picking})
        row = result.mappings().first()
        await db.commit()
        if row:
            updated_order = Orden(**dict(row))
            updated_order.result = 1
            updated_order.message = "Estado de la orden actualizado exitosamente"
            return updated_order
        else:
            order_data = Orden()
            order_data.result = 0
            order_data.message = "Error al actualizar el estado de la orden"
            return order_data
    except Exception as e:
        print(f"Error al actualizar el estado de la orden: {e}")
        db.rollback()
        order_data = Orden()
        order_data.result = 0
        order_data.message = "Error al actualizar el estado de la orden"
        return order_data
    
async def get_list_orders(db:AsyncSession):
    query = text("""
                    SELECT 
                    o.id,
                    o.codigo,
                    o.cliente,
                    o.estado,
                    pd.id_item,
                    i.cod_item,
                    i.descripcion as item,
                    pd.cantidad,
                    i.unidad_medida,
                    pd.lote
                
                    FROM orden_salida AS o
                    INNER JOIN picking AS p ON p.id_orden = o.id
                    INNER JOIN picking_detalle AS pd ON p.id = pd.id_picking
                    INNER JOIN items AS i ON pd.id_item = i.id;
                 """)
    try:
        result = await db.execute(query)
        rows = result.mappings().all()
        ordenes: dict[int, OrderView] = {}

        for row in rows:
            orden_id = row.id

            if orden_id not in ordenes:
                ordenes[orden_id] = OrderView(
                    id=row.id,
                    codigo=row.codigo,
                    cliente=row.cliente,
                    estado=row.estado,
                    productos=[]
                )

            ordenes[orden_id].productos.append(
                ItemsOrderView(
                    id_item=row.id_item,
                    cod_item=row.cod_item,
                    item=row.item,
                    cantidad=row.cantidad,
                    unidad_medida=row.unidad_medida,
                    lote=row.lote
                )
            )
        
        return list(ordenes.values())
    except Exception as e:
        print(f"Error al obtener la lista de órdenes: {e}")
        return []
        