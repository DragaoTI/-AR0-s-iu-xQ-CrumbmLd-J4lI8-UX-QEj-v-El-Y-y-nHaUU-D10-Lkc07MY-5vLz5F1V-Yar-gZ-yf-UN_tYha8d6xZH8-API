from .supabase_service import supabase_service # Sua instância existente
from .admin_service import AdminService

# Use o client da instância supabase_service
admin_service_instance = AdminService(supabase_client=supabase_service.client)
