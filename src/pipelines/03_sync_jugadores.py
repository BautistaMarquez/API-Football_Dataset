import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.db.database import obtener_sesion
from src.db.models import EquipoTemporada, EstadisticaJugadorTemporada, Jugador, Temporada, Equipo
from src.api.client import ClienteAPIFootball, LimiteDiarioAlcanzadoException

def parsear_rating(rating_str: str | None) -> float | None:
    """Intenta convertir el rating a float. Falla silenciosamente devolviendo None si es inválido."""
    if not rating_str:
        return None
    try:
        return float(rating_str)
    except ValueError:
        return None

def sincronizar_plantillas():
    """
    Script automatizado que busca los equipos a los que aún no se les ha 
    descargado la plantilla de jugadores y sus estadísticas anuales.
    """
    print("🚀 Iniciando Pipeline de Sincronización de Plantillas y Jugadores...")
    cliente_api = ClienteAPIFootball()
    
    with obtener_sesion() as sesion:
        # 1. Buscar equipos con plantillas pendientes
        equipos_pendientes = (
            sesion.query(EquipoTemporada)
            .join(Temporada)
            .filter(EquipoTemporada.plantilla_descargada == False)
            .all()
        )
        
        total_pendientes = len(equipos_pendientes)
        if total_pendientes == 0:
            print("✅ No hay plantillas pendientes. Todos los jugadores están actualizados.")
            return
            
        print(f"👥 Se encontraron {total_pendientes} plantillas pendientes de descarga.")
        equipos_procesados = 0
        
        # 2. Bucle de Descarga por Equipo
        for vinculo in equipos_pendientes:
            equipo_id = vinculo.equipo_id
            temporada_anio = vinculo.temporada.anio
            nombre_equipo = sesion.query(Equipo.nombre).filter_by(id=equipo_id).scalar()
            
            print(f"\n➤ Extrayendo plantilla: {nombre_equipo} (Temporada {temporada_anio})...")
            
            try:
                datos_jugadores = cliente_api.obtener_jugadores_equipo(
                    temporada=temporada_anio, 
                    equipo_id=equipo_id
                )
                
                if datos_jugadores:
                    nuevos_jugadores = 0
                    
                    for item in datos_jugadores:
                        info_jugador = item.get("player", {})
                        info_stats = item.get("statistics", [])
                        
                        jugador_id = info_jugador.get("id")
                        if not jugador_id:
                            continue
                            
                        # 3. UPSERT DEL JUGADOR MAESTRO
                        jugador_bd = sesion.query(Jugador).filter_by(id=jugador_id).first()
                        if not jugador_bd:
                            jugador_bd = Jugador(
                                id=jugador_id,
                                nombre_completo=info_jugador.get("name", "Desconocido"),
                                nacionalidad=info_jugador.get("nationality")
                            )
                            sesion.add(jugador_bd)
                            
                            # --- PARCHE PARA LLAVE FORÁNEA ---
                            # Fuerza la escritura inmediata en BD para que exista el ID
                            sesion.flush()
                            nuevos_jugadores += 1
                        
                        # 4. EXTRACCIÓN DE ESTADÍSTICAS (Filtro Inteligente por Liga)
                        # Obtenemos el ID de la liga que estamos procesando (ej. 128 para Argentina)
                        liga_id_actual = vinculo.temporada.liga_id
                        
                        stats = {}
                        # Recorremos todas las competiciones del jugador en el año
                        for competicion in info_stats:
                            liga_info = competicion.get("league", {})
                            if liga_info.get("id") == liga_id_actual:
                                stats = competicion # Encontramos las stats de nuestro torneo
                                break
                        
                        # Si el jugador no jugó ni un minuto en esta liga específica, stats quedará vacío
                        juegos = stats.get("games", {})
                        goles = stats.get("goals", {})
                        tarjetas = stats.get("cards", {})
                        
                        # 5. GUARDAR ESTADÍSTICA DEL JUGADOR
                        nueva_estadistica = EstadisticaJugadorTemporada(
                            jugador_id=jugador_id,
                            equipo_temporada_id=vinculo.id,
                            posicion=juegos.get("position"),
                            minutos_jugados=juegos.get("minutes"),
                            calificacion_promedio=parsear_rating(juegos.get("rating")),
                            goles=goles.get("total"),
                            asistencias=goles.get("assists"),
                            tarjetas_amarillas=tarjetas.get("yellow"),
                            tarjetas_rojas=tarjetas.get("red"),
                            datos_crudos=item # JSONB intacto
                        )
                        sesion.add(nueva_estadistica)
                        
                    # 6. Actualizar Checkpoint y hacer Commit por equipo
                    vinculo.plantilla_descargada = True
                    sesion.commit()
                    equipos_procesados += 1
                    print(f"   ✅ Equipo guardado: {nuevos_jugadores} nuevos perfiles creados.")
                    
            except LimiteDiarioAlcanzadoException as e:
                print(f"\n🛑 LÍMITE DIARIO ALCANZADO: {e}")
                print(f"💾 Guardando estado. Plantillas procesadas hoy: {equipos_procesados}/{total_pendientes}")
                sesion.rollback()
                break
            except Exception as e:
                print(f"❌ Error inesperado con el equipo {nombre_equipo}: {e}")
                sesion.rollback()
                continue

        print(f"\n🏁 Ejecución finalizada. Se procesaron {equipos_procesados} plantillas exitosamente.")

if __name__ == "__main__":
    sincronizar_plantillas()