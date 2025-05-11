# app/services/__init__.py
from .supabase_service import supabase_service
from .admin_service import AdminService

admin_service_instance = None # Default

if supabase_service and supabase_service.client:
    admin_service_instance = AdminService(supabase_client=supabase_service.client)
    print("INFO:     Instância de AdminService criada com sucesso em app.services.")
else:
    print("ERRO CRÍTICO: Cliente Supabase (supabase_service.client) não está disponível ao tentar criar AdminService.")
    print("              Verifique a inicialização do SupabaseService e as variáveis de ambiente SUPABASE_URL/KEY.")
    # Considere levantar uma exceção aqui se admin_service_instance for crucial para a inicialização do app.
    # raise RuntimeError("Falha ao inicializar AdminService: cliente Supabase indisponível.")
