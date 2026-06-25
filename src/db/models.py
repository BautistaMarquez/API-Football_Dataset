from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, Date, ForeignKey, JSON, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

class ModeloBase(DeclarativeBase):
    """Clase base declarativa de SQLAlchemy 2.0"""
    pass

class AuditoriaMixin:
    """Mixin para auditar creación y modificación."""
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ==========================================
# CATÁLOGOS BASE
# ==========================================

class Liga(ModeloBase, AuditoriaMixin):
    __tablename__ = 'ligas'
    id: Mapped[int] = mapped_column(primary_key=True) # ID original API (ej. 128)
    nombre: Mapped[str] = mapped_column(String(100))
    pais: Mapped[str] = mapped_column(String(100))

class Temporada(ModeloBase, AuditoriaMixin):
    __tablename__ = 'temporadas'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    liga_id: Mapped[int] = mapped_column(ForeignKey('ligas.id'))
    anio: Mapped[int] = mapped_column(Integer) # Ej. 2023
    fecha_inicio: Mapped[Optional[date]] = mapped_column(Date)
    fecha_fin: Mapped[Optional[date]] = mapped_column(Date)

class Equipo(ModeloBase, AuditoriaMixin):
    __tablename__ = 'equipos'
    id: Mapped[int] = mapped_column(primary_key=True) # ID original API
    nombre: Mapped[str] = mapped_column(String(100))
    codigo: Mapped[Optional[str]] = mapped_column(String(10))
    logo_url: Mapped[Optional[str]] = mapped_column(String(255))

class Jugador(ModeloBase, AuditoriaMixin):
    __tablename__ = 'jugadores'
    id: Mapped[int] = mapped_column(primary_key=True) # ID original API
    nombre_completo: Mapped[str] = mapped_column(String(150))
    nacionalidad: Mapped[Optional[str]] = mapped_column(String(100))

class Arbitro(ModeloBase, AuditoriaMixin):
    __tablename__ = 'arbitros'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(150), unique=True)

# ==========================================
# RELACIONES Y CHECKPOINTS DE PIPELINE
# ==========================================

class EquipoTemporada(ModeloBase, AuditoriaMixin):
    """
    TABLA CRÍTICA: Control de Cuota y Relación.
    Dicta qué equipos participan en el año y si ya consumimos sus endpoints.
    """
    __tablename__ = 'equipo_temporada'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    equipo_id: Mapped[int] = mapped_column(ForeignKey('equipos.id'))
    temporada_id: Mapped[int] = mapped_column(ForeignKey('temporadas.id'))
    
    # Banderas para el script diario (Para no repetir peticiones)
    estadisticas_descargadas: Mapped[bool] = mapped_column(Boolean, default=False)
    plantilla_descargada: Mapped[bool] = mapped_column(Boolean, default=False)

# ==========================================
# ESTADÍSTICAS MACRO (POR TEMPORADA)
# ==========================================

class EstadisticaEquipoTemporada(ModeloBase, AuditoriaMixin):
    __tablename__ = 'estadisticas_equipo_temporada'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    equipo_temporada_id: Mapped[int] = mapped_column(ForeignKey('equipo_temporada.id'))
    
    # Columnas rápidas (Top level)
    partidos_jugados: Mapped[Optional[int]] = mapped_column(Integer)
    victorias: Mapped[Optional[int]] = mapped_column(Integer)
    empates: Mapped[Optional[int]] = mapped_column(Integer)
    derrotas: Mapped[Optional[int]] = mapped_column(Integer)
    goles_a_favor: Mapped[Optional[int]] = mapped_column(Integer)
    goles_en_contra: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Capa Bronce: Todo el resto de la info para PowerBI mediante Vistas SQL
    datos_crudos: Mapped[Optional[dict]] = mapped_column(JSON)

class EstadisticaJugadorTemporada(ModeloBase, AuditoriaMixin):
    __tablename__ = 'estadisticas_jugador_temporada'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    jugador_id: Mapped[int] = mapped_column(ForeignKey('jugadores.id'))
    equipo_temporada_id: Mapped[int] = mapped_column(ForeignKey('equipo_temporada.id'))
    
    # Columnas rápidas (Top level)
    posicion: Mapped[Optional[str]] = mapped_column(String(50))
    minutos_jugados: Mapped[Optional[int]] = mapped_column(Integer)
    calificacion_promedio: Mapped[Optional[float]] = mapped_column(Float)
    goles: Mapped[Optional[int]] = mapped_column(Integer)
    asistencias: Mapped[Optional[int]] = mapped_column(Integer)
    tarjetas_amarillas: Mapped[Optional[int]] = mapped_column(Integer)
    tarjetas_rojas: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Capa Bronce: Tiros, regates, pases, duelos, penales, etc.
    datos_crudos: Mapped[Optional[dict]] = mapped_column(JSON)

# ==========================================
# TABLAS MICRO (PARTIDOS) - FUTURO
# ==========================================

class Partido(ModeloBase, AuditoriaMixin):
    __tablename__ = 'partidos'
    id: Mapped[int] = mapped_column(primary_key=True) # ID original API
    temporada_id: Mapped[int] = mapped_column(ForeignKey('temporadas.id'))
    equipo_local_id: Mapped[int] = mapped_column(ForeignKey('equipos.id'))
    equipo_visitante_id: Mapped[int] = mapped_column(ForeignKey('equipos.id'))
    arbitro_id: Mapped[Optional[int]] = mapped_column(ForeignKey('arbitros.id'))
    
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(20))
    goles_local: Mapped[Optional[int]] = mapped_column(Integer)
    goles_visitante: Mapped[Optional[int]] = mapped_column(Integer)

    estadisticas_equipo_descargadas: Mapped[bool] = mapped_column(Boolean, default=False)
    estadisticas_jugador_descargadas: Mapped[bool] = mapped_column(Boolean, default=False)