import time
import requests
from typing import Dict, Any, Optional, List

# Importamos la configuración centralizada
from src.config import Config

class LimiteDiarioAlcanzadoException(Exception):
    """Excepción lanzada cuando se alcanza el límite seguro de peticiones diarias."""
    pass

class ClienteAPIFootball:
    def __init__(self):
        self.headers = {
            'x-apisports-key': Config.API_FOOTBALL_KEY,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }
        self.base_url = "https://v3.football.api-sports.io"
        
        # Límite estricto de seguridad: 99 para dejar 1 de margen de error
        self.limite_diario = 99 
        self.peticiones_realizadas = 0

    def _hacer_peticion(self, endpoint: str, parametros: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Método centralizado para todas las llamadas a la API.
        Controla la cuota diaria y el límite por minuto.
        """
        if self.peticiones_realizadas >= self.limite_diario:
            raise LimiteDiarioAlcanzadoException(
                f"Límite de seguridad alcanzado ({self.peticiones_realizadas} req). Deteniendo extracción."
            )

        url = f"{self.base_url}/{endpoint}"
        
        try:
            respuesta = requests.get(url, headers=self.headers, params=parametros, timeout=15)
            self.peticiones_realizadas += 1
            
            # Throttling preventivo: 6.1 segundos de pausa evitan romper el límite de 10 req/minuto
            time.sleep(6.1)
            
            respuesta.raise_for_status()
            datos = respuesta.json()
            
            # Parseo Defensivo: Verificar errores internos del JSON que devuelven HTTP 200
            errores = datos.get("errors")
            if errores:
                if isinstance(errores, dict) and "requests" in errores:
                    raise LimiteDiarioAlcanzadoException("La API reporta límite diario excedido internamente.")
                print(f"⚠️ API devolvió un error lógico en {endpoint}: {errores}")
                return None
                
            return datos
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error de red al consultar {endpoint}: {e}")
            return None

    # ==========================================
    # ENDPOINTS PÚBLICOS
    # ==========================================

    def obtener_estadisticas_equipo(self, liga_id: int, temporada: int, equipo_id: int) -> Optional[Dict[str, Any]]:
        """Extrae la radiografía anual de un equipo."""
        parametros = {
            "league": liga_id,
            "season": temporada,
            "team": equipo_id
        }
        
        datos = self._hacer_peticion("teams/statistics", parametros)
        if not datos:
            return None
            
        # Retornamos directamente el nodo 'response' para no lidiar con metadatos de la API después
        return datos.get("response", {})

    def obtener_jugadores_equipo(self, temporada: int, equipo_id: int) -> List[Dict[str, Any]]:
        """
        Extrae todos los jugadores de un equipo en una temporada específica, 
        manejando automáticamente la paginación.
        """
        jugadores_totales = []
        pagina_actual = 1
        paginas_totales = 1
        
        while pagina_actual <= paginas_totales:
            parametros = {
                "season": temporada,
                "team": equipo_id,
                "page": pagina_actual
            }
            
            print(f"   ↳ Pidiendo página {pagina_actual} de {paginas_totales}...")
            datos = self._hacer_peticion("players", parametros)
            
            if not datos:
                break
                
            respuesta_cruda = datos.get("response", [])
            jugadores_totales.extend(respuesta_cruda)
            
            paginacion = datos.get("paging", {})
            paginas_api = paginacion.get("total", 1)
            
            # --- PARCHE DE SEGURIDAD PARA PLAN GRATUITO ---
            # Forzamos un máximo de 3 páginas (60 jugadores)
            paginas_totales = min(paginas_api, 3) 
            
            pagina_actual += 1
            
        return jugadores_totales
    
    def obtener_equipos_temporada(self, liga_id: int, temporada: int) -> List[Dict[str, Any]]:
        """
        Extrae la lista maestra de equipos que participan en una liga y temporada específica.
        Costo: 1 petición. No requiere paginación.
        """
        parametros = {
            "league": liga_id,
            "season": temporada
        }
        
        print(f"Extrayendo catálogo de equipos para Liga {liga_id} - Temporada {temporada}...")
        datos = self._hacer_peticion("teams", parametros)
        
        if not datos:
            return []
            
        # La API devuelve una lista donde cada elemento tiene un nodo 'team' y un nodo 'venue'
        return datos.get("response", [])