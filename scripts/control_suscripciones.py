import sys
import os
from datetime import datetime, timedelta
from sqlmodel import Session, select, create_engine
from sqlalchemy import text
import urllib.parse

# --- CONFIGURACIÓN DE CONEXIÓN (Tus datos) ---
DB_USER = "root"
DB_PASS = "TreborOD(523)"
DB_HOST = "localhost"
DB_PORT = "3306"
DB_NAME = "sistema_ventas"

safe_pass = urllib.parse.quote_plus(DB_PASS)
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{safe_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Conexión a MySQL exitosa.")
except Exception as e:
    print(f"❌ Error conectando: {e}")
    sys.exit(1)

sys.path.append(os.getcwd())

try:
    from app.models.company import Company, PlanType, SubscriptionStatus
except ImportError:
    print("❌ Error importando modelos. Ejecuta desde la raíz.")
    sys.exit(1)

# --- LÓGICA UNIVERSAL ---

def listar_empresas(session):
    print("\n🏢 --- EMPRESAS ---")
    print(f"{'ID':<4} | {'NOMBRE':<25} | {'PLAN':<12} | {'USUARIOS':<10}")
    print("-" * 60)
    companies = session.exec(select(Company)).all()
    for c in companies:
        # Mostramos -1 como "Ilimitado" visualmente
        users = "Ilimitado" if c.max_users == -1 else str(c.max_users)
        plan_val = c.plan_type.value if hasattr(c.plan_type, 'value') else str(c.plan_type)
        print(f"{c.id:<4} | {c.name:<25} | {plan_val:<12} | {users:<10}")
    print("-" * 60)
    return [c.id for c in companies]

def aplicar_cambios(session, company_id, plan_opcion, estado_opcion):
    company = session.get(Company, company_id)
    if not company: return

    # 1. APLICAR PLAN (Y sus límites)
    if plan_opcion == "1": # STANDARD
        company.plan_type = PlanType.STANDARD
        company.max_branches = 5
        company.max_users = 10
        print(f"📋 Plan cambiado a: STANDARD (5 Suc / 10 Users)")

    elif plan_opcion == "2": # PROFESSIONAL
        company.plan_type = PlanType.PROFESSIONAL
        company.max_branches = 10
        company.max_users = -1  # <--- ILIMITADO
        print(f"👑 Plan cambiado a: PROFESSIONAL (10 Suc / Users Ilimitados)")

    elif plan_opcion == "3": # TRIAL (Reset)
        company.plan_type = PlanType.TRIAL
        company.max_branches = 2
        company.max_users = 3
        company.trial_ends_at = datetime.now() + timedelta(days=15)
        company.subscription_ends_at = None
        company.subscription_status = SubscriptionStatus.ACTIVE
        session.add(company)
        session.commit()
        print("🔄 Reseteado a TRIAL original.")
        return # Salimos, no aplica lógica de pagos

    # 2. APLICAR ESTADO DE PAGO (Solo para planes Standard/Pro)
    now = datetime.now()

    if estado_opcion == "1": # ACTIVO
        company.subscription_ends_at = now + timedelta(days=30)
        company.subscription_status = SubscriptionStatus.ACTIVE
        print("✅ Estado: ACTIVO (Vence en 30 días)")

    elif estado_opcion == "2": # WARNING
        company.subscription_ends_at = now + timedelta(days=3)
        company.subscription_status = SubscriptionStatus.ACTIVE
        print("🟡 Estado: WARNING (Vence en 3 días)")

    elif estado_opcion == "3": # GRACIA
        company.subscription_ends_at = now - timedelta(days=2)
        # Dejamos ACTIVE para que el sistema detecte la fecha y cambie a PAST_DUE
        company.subscription_status = SubscriptionStatus.ACTIVE
        print("🔴 Estado: MOROSO (Venció hace 2 días)")

    elif estado_opcion == "4": # SUSPENDIDO
        company.subscription_ends_at = now - timedelta(days=10)
        company.subscription_status = SubscriptionStatus.SUSPENDED
        print("⚫ Estado: SUSPENDIDO (Venció hace 10 días)")

    session.add(company)
    session.commit()
    print("\n🚀 ¡Cambios guardados! Refresca tu navegador.")

def main():
    with Session(engine) as session:
        ids = listar_empresas(session)
        if not ids: return

        cid = input("\n👉 ID Empresa: ")
        if not cid.isdigit() or int(cid) not in ids: return

        print("\n--- PASO 1: ELIGE EL PLAN ---")
        print("1. Standard (Límites Normales)")
        print("2. 👑 Professional (Usuarios Ilimitados)")
        print("3. Resetear a Trial")
        plan = input("Opción: ")

        if plan == "3":
            aplicar_cambios(session, int(cid), plan, None)
        else:
            print("\n--- PASO 2: ELIGE EL ESTADO DEL PAGO ---")
            print("1. ✅ Al día (Activo)")
            print("2. 🟡 Por vencer (Warning)")
            print("3. 🔴 Vencido (Gracia)")
            print("4. ⚫ Suspendido (Bloqueo)")
            estado = input("Opción: ")
            aplicar_cambios(session, int(cid), plan, estado)

if __name__ == "__main__":
    main()
