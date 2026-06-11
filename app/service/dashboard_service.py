from datetime import date

from app.model.dashboard_model import Summary
from app.repository import inventory_repository, position_repository

async def get_summary(db):
    summary_data = Summary()
    summary_data.total_posiciones = await position_repository.count_positions(db)
    summary_data.posiciones_ocupadas = await position_repository.count_occupied_positions(db)
    summary_data.posiciones_disponibles = await position_repository.count_available_positions(db)
    result_alerts = await inventory_repository.count_expiration_alerts(db)
    if result_alerts.result == 1:
        summary_data.alertas_vencido = result_alerts.alertas_vencido
        summary_data.alertas_vencimiento_leve = result_alerts.alertas_vencimiento_leve
        summary_data.alertas_vencimiento_critico = result_alerts.alertas_vencimiento_critico
        summary_data.result = 1
        summary_data.message = "Resumen obtenido exitosamente"
        return summary_data
    else:
        summary_data.result = 0
        summary_data.message = "Error al obtener el resumen"
        return summary_data
    
    
async def get_all_positions_table(db, item: str = None, posicion_estado: str = None, lote: str = None, estado_alerta: str = None, limite: int = 50, offset: int = 0):
    positions_data = await position_repository.get_all_positions_table(db, item, posicion_estado, lote,estado_alerta ,limite, offset)
    return positions_data


async def get_all_positions(db):
    positions_data = await position_repository.get_all_positions(db)
    return positions_data

async def get_positions_by_item(db, item: str = None, lote: str = None):
    positions_data = await position_repository.get_positions_by_item(db, item, lote)
    return positions_data
