import sys
import os

# Ajuste del path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.db.database import obtener_sesion
from src.db.models import EquipoTemporada, EstadisticaEquipoTemporada, Liga, Temporada, Equipo
from src.api.client import ClienteAPIFootball, LimiteDiarioAlcanzadoException

def sincronizar_estadisticas_equipos():
    """
    Script automatizado que busca equipos pendientes en la base de datos
    y descarga sus estadísticas anuales respetando el límite de cuota.
    """
    print("🚀 Iniciando Pipeline de Sincronización de Estadísticas de Equipos...")
    cliente_api = ClienteAPIFootball()
    
    with obtener_sesion() as sesion:
        # 1. Buscar equipos pendientes (estadisticas_descargadas == False)
        equipos_pendientes = (
            sesion.query(EquipoTemporada)
            .join(Temporada)
            .join(Liga)
            .filter(EquipoTemporada.estadisticas_descargadas == False)
            .all()
        )
        
        total_pendientes = len(equipos_pendientes)
        if total_pendientes == 0:
            print("✅ No hay equipos pendientes. Todas las estadísticas están actualizadas.")
            return
            
        print(f"📊 Se encontraron {total_pendientes} equipos pendientes de descarga.")
        
        equipos_procesados = 0
        
        # 2. Bucle de Descarga
        for vinculo in equipos_pendientes:
            equipo_id = vinculo.equipo_id
            temporada_anio = vinculo.temporada.anio
            liga_id = vinculo.temporada.liga_id
            
            # Obtener el nombre del equipo para los logs
            nombre_equipo = sesion.query(Equipo.nombre).filter_by(id=equipo_id).scalar()
            
            print(f"➤ Extrayendo stats: {nombre_equipo} (Temporada {temporada_anio})...")
            
            try:
                # Llamada al Cliente API
                datos = cliente_api.obtener_estadisticas_equipo(
                    liga_id=liga_id, 
                    temporada=temporada_anio, 
                    equipo_id=equipo_id
                )
                
                if datos:
                    # 3. Extraer métricas principales defensivamente
                    fixtures = datos.get("fixtures", {}).get("played", {})
                    wins = datos.get("fixtures", {}).get("wins", {})
                    draws = datos.get("fixtures", {}).get("draws", {})
                    loses = datos.get("fixtures", {}).get("loses", {})
                    goals_for = datos.get("goals", {}).get("for", {}).get("total", {})
                    goals_against = datos.get("goals", {}).get("against", {}).get("total", {})
                    
                    # 4. Guardar en Base de Datos (Mapeo Top-Level + JSONB)
                    nueva_estadistica = EstadisticaEquipoTemporada(
                        equipo_temporada_id=vinculo.id,
                        partidos_jugados=fixtures.get("total"),
                        victorias=wins.get("total"),
                        empates=draws.get("total"),
                        derrotas=loses.get("total"),
                        goles_a_favor=goals_for.get("total"),
                        goles_en_contra=goals_against.get("total"),
                        datos_crudos=datos # <- ¡Aquí guardamos el tesoro completo para PowerBI!
                    )
                    
                    sesion.add(nueva_estadistica)
                    
                    # 5. Actualizar el Checkpoint
                    vinculo.estadisticas_descargadas = True
                    
                    # 6. Commit por cada equipo (Crucial para no perder datos si se corta el proceso)
                    sesion.commit()
                    equipos_procesados += 1
                    
            except LimiteDiarioAlcanzadoException as e:
                print(f"\n🛑 LÍMITE DIARIO ALCANZADO: {e}")
                print(f"💾 Guardando estado actual. Equipos procesados hoy: {equipos_procesados}/{total_pendientes}")
                # Hacemos un rollback de seguridad por si quedó una transacción colgada
                sesion.rollback() 
                break
            except Exception as e:
                print(f"❌ Error inesperado con el equipo {nombre_equipo}: {e}")
                sesion.rollback()
                # Opcional: Podrías hacer un continue aquí si quieres que un error ignore ese equipo y pase al siguiente.
                continue

        print(f"\n🏁 Ejecución finalizada. Se procesaron {equipos_procesados} equipos exitosamente.")

if __name__ == "__main__":
    sincronizar_estadisticas_equipos()