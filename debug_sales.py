from sqlmodel import select, Session, create_engine
from app.models import Sale
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

import rxconfig

print(f"DB URL: {rxconfig.config.db_url}")

from sqlalchemy import create_engine
engine = create_engine(rxconfig.config.db_url)

with Session(engine) as session:
    sales = session.exec(select(Sale)).all()
    print(f"Found {len(sales)} sales.")
    for sale in sales:
        print(f"ID: {sale.id}, Method: '{sale.payment_method}', Details: '{sale.payment_details}', Total: {sale.total_amount}, Deleted: {sale.is_deleted}")
