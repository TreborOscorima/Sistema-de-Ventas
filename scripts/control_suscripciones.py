import sys
import os
from datetime import datetime, timedelta
from sqlmodel import Session, select, create_engine
from sqlalchemy import text
import urllib.parse

# --- CONFIGURACIÓN DE CONEXIÓN ---
# Tus datos del .env
DB_USER = "root"
DB_PASS = "TreborOD(523)"  # Tu contraseña exacta
DB_HOST = "localhost"
DB_PORT = "3306"
DB_NAME = "sistema_ventas"

# Codificamos la contraseña por si tiene caracteres especiales
safe_pass = urllib.parse.quote_plus(DB_PASS)

# Construimos la URL de conexión manualmente
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{safe_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Creamos el motor localmente
try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Conexión directa a MySQL exitosa.")
except Exception as e:
    print(f"❌ Error conectando a la BD: {e}")
    sys.exit(1)

# Aseguramos ruta para importar los modelos
sys.path.append(os.getcwd())

# Importamos modelos
try:
    from app.models.company import Company, PlanType, SubscriptionStatus
except ImportError as e:
    print(f"❌ Error importando modelos: {e}")
    print("Asegúrate de estar ejecutando esto desde la raíz del proyecto.")
    sys.exit(1)

# --- LÓGICA DEL CONTROL ---

def listar_empresas(session):
    print("\n🏢 --- TUS EMPRESAS REGISTRADAS ---")
    print(f"{'ID':<4} | {'NOMBRE':<25} | {'PLAN':<12} | {'ESTADO':<10} | {'VENCE'}")
    print("-" * 80)
    companies = session.exec(select(Company)).all()
    for c in companies:
        vence = c.subscription_ends_at.strftime('%Y-%m-%d') if c.subscription_ends_at else "N/A"
        # Manejo seguro de Enums
        plan = c.plan_type.value if hasattr(c.plan_type, 'value') else str(c.plan_type)
        status = c.subscription_status.value if hasattr(c.subscription_status, 'value') else str(c.subscription_status)

        print(f"{c.id:<4} | {c.name:<25} | {plan:<12} | {status:<10} | {vence}")
    print("-" * 80)
    return [c.id for c in companies]

def simular_estado(session, company_id, opcion):
    company = session.get(Company, company_id)
    if not company:
        print("❌ Empresa no encontrada.")
        return

    now = datetime.now()

    if opcion == "1": # WARNING (Amarillo)
        print("🟡 Aplicando: Plan Standard + Vence en 3 días (Warning)...")
        company.plan_type = PlanType.STANDARD
        company.subscription_ends_at = now + timedelta(days=3)
        company.subscription_status = SubscriptionStatus.ACTIVE

    elif opcion == "2": # GRACIA (Rojo)
        print("🔴 Aplicando: Plan Standard + Venció hace 2 días (Periodo Gracia)...")
        company.plan_type = PlanType.STANDARD
        company.subscription_ends_at = now - timedelta(days=2)
        company.subscription_status = SubscriptionStatus.ACTIVE

    elif opcion == "3": # BLOQUEO (Suspendido)
        print("⚫ Aplicando: Plan Standard + Venció hace 7 días (Bloqueo Total)...")
        company.plan_type = PlanType.STANDARD
        company.subscription_ends_at = now - timedelta(days=7)
        company.subscription_status = SubscriptionStatus.SUSPENDED

    elif opcion == "4": # RESTAURAR (Trial Limpio)
        print("🟢 Restaurando: Plan Trial Original...")
        company.plan_type = PlanType.TRIAL
        company.trial_ends_at = now + timedelta(days=15)
        company.subscription_ends_at = None
        company.subscription_status = SubscriptionStatus.ACTIVE

    session.add(company)
    session.commit()
    session.refresh(company)
    print("✅ ¡Cambio aplicado! Ve al Dashboard y refresca (F5).")

def main():
    with Session(engine) as session:
        ids_validos = listar_empresas(session)

        if not ids_validos:
            print("No hay empresas creadas.")
            return

        cid = input("\n👉 Ingresa el ID de la empresa a probar: ")
        if not cid.isdigit() or int(cid) not in ids_validos:
            print("ID inválido.")
            return

        print("\n🧪 --- MENÚ DE PRUEBAS SAAS ---")
        print("1. 🟡 Simular Alerta AMARILLA (Vence en 3 días)")
        print("2. 🔴 Simular Alerta ROJA (Vencido hace 2 días)")
        print("3. ⚫ Simular BLOQUEO (Vencido hace 7 días)")
        print("4. 🟢 Volver a TRIAL limpio (Reset)")

        opcion = input("Elige una opción (1-4): ")
        simular_estado(session, int(cid), opcion)

if __name__ == "__main__":
    main()
