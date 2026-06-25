import os
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env a la memoria
load_dotenv()

class Config:
    """Clase centralizada para gestionar la configuración y credenciales del pipeline."""
    
    # Credenciales de API
    API_FOOTBALL_KEY: str = os.getenv("API_FOOTBALL_KEY", "")
    
    # Credenciales de Base de Datos
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "api_football_db")

    @classmethod
    def validar_configuracion(cls) -> None:
        """
        Aplica el patrón Fail-Fast. Si falta una credencial crítica,
        detiene el programa inmediatamente con un mensaje claro.
        """
        if not cls.API_FOOTBALL_KEY or cls.API_FOOTBALL_KEY == "pega_aqui_tu_clave_gratuita_de_apisports":
            raise ValueError("CRÍTICO: API_FOOTBALL_KEY no configurada correctamente en el archivo .env")
        
        if not cls.DB_PASSWORD or cls.DB_PASSWORD == "tu_contraseña_de_postgres":
            raise ValueError("CRÍTICO: DB_PASSWORD no configurada correctamente en el archivo .env")

    @classmethod
    def get_db_url(cls) -> str:
        """
        Genera la URL de conexión específica para SQLAlchemy 2.0 usando el driver psycopg3.
        """
        return f"postgresql+psycopg://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"

# Al importar este módulo, validamos automáticamente la configuración.
Config.validar_configuracion()