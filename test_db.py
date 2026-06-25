# test_db.py
from src.db.database import inicializar_base_de_datos, obtener_sesion
from src.db.models import Liga

def probar_conexion():
    print("Iniciando prueba de conexión a PostgreSQL...")
    
    # 1. Esto creará todas las tablas que definimos en models.py
    inicializar_base_de_datos()
    
    # 2. Hacemos una prueba rápida de Inserción/Lectura usando nuestro Administrador de Contexto
    try:
        with obtener_sesion() as sesion:
            # Buscamos si la Liga Argentina ya existe para no duplicarla en la prueba
            liga_existente = sesion.query(Liga).filter_by(id=128).first()
            
            if not liga_existente:
                print("Insertando dato de prueba (Liga Profesional Argentina)...")
                nueva_liga = Liga(id=128, nombre="Liga Profesional Argentina", pais="Argentina")
                sesion.add(nueva_liga)
                # El commit se hace automáticamente al salir del bloque 'with' exitosamente
            else:
                print("La liga ya existe en la base de datos.")
                
        print("✅ Prueba de inserción/transacción completada con éxito.")
    except Exception as e:
        print(f"❌ Falló la prueba de transacción: {e}")

if __name__ == "__main__":
    probar_conexion()