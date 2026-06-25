from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Importamos nuestra configuración centralizada
from src.config import Config
# Importamos la clase base de nuestros modelos para poder crear las tablas
from src.db.models import ModeloBase 

# ==========================================
# 1. CONFIGURACIÓN DEL MOTOR (ENGINE)
# ==========================================
# pool_pre_ping=True asegura una reconexión automática si el motor pierde conexión con PostgreSQL
motor = create_engine(
    Config.get_db_url(), 
    echo=False, # Pon esto en True si alguna vez necesitas ver el SQL crudo en la terminal
    pool_pre_ping=True 
)

# ==========================================
# 2. FÁBRICA DE SESIONES
# ==========================================
SesionLocal = sessionmaker(autocommit=False, autoflush=False, bind=motor)

# ==========================================
# 3. FUNCIONES CORE
# ==========================================

def inicializar_base_de_datos() -> None:
    """
    Lee todos los modelos que heredan de ModeloBase y crea las tablas
    en PostgreSQL si aún no existen. No sobrescribe datos existentes.
    """
    try:
        ModeloBase.metadata.create_all(bind=motor)
        print("✅ Base de datos y tablas inicializadas correctamente.")
    except Exception as e:
        print(f"❌ Error al inicializar la base de datos: {e}")
        raise

@contextmanager
def obtener_sesion() -> Generator[Session, None, None]:
    """
    Generador de sesiones seguro (Context Manager).
    Garantiza que toda transacción haga commit exitosamente o rollback en caso de error,
    y siempre cierra la conexión para liberar recursos.
    """
    sesion: Session = SesionLocal()
    try:
        yield sesion
        sesion.commit()
    except Exception as e:
        sesion.rollback()
        print(f"⚠️ Error en la transacción. Rollback ejecutado de forma segura: {e}")
        raise
    finally:
        sesion.close()