# app/services/__init__.py
from .supabase_service import supabase_service # Importa a instância já criada
from .admin_service import AdminService     # Importa a classe AdminService

admin_service_instance = None # Inicializa como None

print("INFO:     Tentando criar instância de AdminService em app.services.__init__ ...")
if supabase_service and supabase_service.client:
    try:
        admin_service_instance = AdminService(supabase_client=supabase_service.client)
        if admin_service_instance and admin_service_instance.db: # Checa se o client foi passado corretamente
            print("INFO:     Instância de AdminService CRIADA COM SUCESSO e cliente DB associado.")
        else:
            print("ERRO CRÍTICO: AdminService foi instanciado, MAS seu atributo 'db' (cliente supabase) é None.")
            admin_service_instance = None # Garante que é None se a inicialização interna falhar
    except Exception as e:
        print(f"ERRO CRÍTICO: Exceção ao tentar instanciar AdminService: {e}")
        import traceback
        traceback.print_exc()
        admin_service_instance = None
else:
    print("ERRO CRÍTICO: Cliente Supabase (supabase_service.client) NÃO ESTÁ DISPONÍVEL ou é None.")
    print("              AdminService não pôde ser instanciado. Verifique a inicialização do SupabaseService")
    print("              e as variáveis de ambiente SUPABASE_URL/KEY.")

# Para permitir importações como 'from app.services import supabase_service, admin_service_instance'
__all__ = ["supabase_service", "admin_service_instance"]
