import sys
import os

# Ajuste del path para poder importar desde src si ejecutamos desde la raíz del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.db.database import obtener_sesion
from src.db.models import Liga, Temporada, Equipo, EquipoTemporada
from src.api.client import ClienteAPIFootball, LimiteDiarioAlcanzadoException

def inicializar_catalogo(liga_id: int, nombre_liga: str, pais: str, anio: int) -> None:
    """
    Descarga y guarda el catálogo base de equipos para una liga y temporada específica.
    Implementa lógica defensiva (Upsert) para no duplicar datos si se ejecuta varias veces.
    """
    print(f"🚀 Iniciando Pipeline de Catálogos: {nombre_liga} - {anio}")
    
    cliente_api = ClienteAPIFootball()
    
    with obtener_sesion() as sesion:
        # ==========================================
        # 1. UPSERT DE LIGA
        # ==========================================
        liga = sesion.query(Liga).filter_by(id=liga_id).first()
        if not liga:
            print(f"[BD] Creando nueva liga: {nombre_liga}")
            liga = Liga(id=liga_id, nombre=nombre_liga, pais=pais)
            sesion.add(liga)
            sesion.flush() # Sincroniza el ID con la BD temporalmente dentro de la transacción
        
        # ==========================================
        # 2. UPSERT DE TEMPORADA
        # ==========================================
        temporada = sesion.query(Temporada).filter_by(liga_id=liga.id, anio=anio).first()
        if not temporada:
            print(f"[BD] Creando nueva temporada: {anio}")
            temporada = Temporada(liga_id=liga.id, anio=anio)
            sesion.add(temporada)
            sesion.flush()
            
        # ==========================================
        # 3. EXTRACCIÓN DE LA API
        # ==========================================
        try:
            datos_equipos = cliente_api.obtener_equipos_temporada(liga_id=liga.id, temporada=anio)
        except LimiteDiarioAlcanzadoException as e:
            print(f"❌ Error crítico de cuota: {e}")
            return
            
        if not datos_equipos:
            print("⚠️ No se encontraron equipos en la API para los parámetros dados.")
            return
            
        print(f"[API] Se descargaron {len(datos_equipos)} equipos. Procesando...")
        
        # ==========================================
        # 4. UPSERT DE EQUIPOS Y RELACIÓN (EQUIPO_TEMPORADA)
        # ==========================================
        nuevos_equipos = 0
        nuevas_relaciones = 0
        
        for item in datos_equipos:
            # Parseo defensivo del JSON
            info_equipo = item.get("team", {})
            equipo_id = info_equipo.get("id")
            nombre_equipo = info_equipo.get("name")
            
            if not equipo_id or not nombre_equipo:
                continue
                
            # Upsert Equipo
            equipo_bd = sesion.query(Equipo).filter_by(id=equipo_id).first()
            if not equipo_bd:
                equipo_bd = Equipo(
                    id=equipo_id,
                    nombre=nombre_equipo,
                    codigo=info_equipo.get("code"),
                    logo_url=info_equipo.get("logo")
                )
                sesion.add(equipo_bd)
                nuevos_equipos += 1
            
            # Upsert EquipoTemporada (El Checkpoint Crítico)
            # Solo la creamos si el equipo no estaba ya vinculado a este año
            vinculo_existente = sesion.query(EquipoTemporada).filter_by(
                equipo_id=equipo_id, 
                temporada_id=temporada.id
            ).first()
            
            if not vinculo_existente:
                nuevo_vinculo = EquipoTemporada(
                    equipo_id=equipo_id,
                    temporada_id=temporada.id,
                    estadisticas_descargadas=False,
                    plantilla_descargada=False
                )
                sesion.add(nuevo_vinculo)
                nuevas_relaciones += 1

        # El commit se ejecuta automáticamente al salir del bloque 'with'
        print(f"✅ Pipeline Finalizado. Resumen de Inserciones:")
        print(f"   - Equipos nuevos en el catálogo maestro: {nuevos_equipos}")
        print(f"   - Equipos registrados para la temporada {anio}: {nuevas_relaciones}")

if __name__ == "__main__":
    # Ejecución de prueba con la Liga Profesional Argentina 2026
    # LIGA ID = 128
    inicializar_catalogo(
        liga_id=128, 
        nombre_liga="Liga Profesional Argentina", 
        pais="Argentina", 
        anio=2024
    )