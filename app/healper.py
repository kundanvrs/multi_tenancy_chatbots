
from config.database import get_db
from services.db_service import drop_all_tenant_tables

drop_tables = drop_all_tenant_tables(db=next(get_db()))
print(f"Dropped tables: {drop_tables}")



