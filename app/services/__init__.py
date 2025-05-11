# app/services/__init__.py
from .supabase_service import supabase_service # Importa a instância já criada
from .admin_service import AdminService     # Importa a CLASSE AdminService

admin_service_instance = None # Inicializa como None

print("INFO:     app.services.__init__ - Tentando criar instância de AdminService...")
if supabase_service and supabase_service.client:
    try:
        # Passa o cliente Supabase já inicializado para o AdminService
        admin_service_instance = AdminService(supabase_client=supabase_service.client)
        
        # Verifica se o atributo 'db' dentro de AdminService foi realmente definido
        if hasattr(admin_service_instance, 'db') and admin_service_instance.db is not None:
            print("INFO:     Instância de AdminService CRIADA COM SUCESSO e cliente DB (self.db) associado.")
        else:
            print("ERRO CRÍTICO: AdminService foi instanciado, MAS seu atributo 'db' (cliente supabase) é None ou não existe.")
            print("              Isso indica um problema no __init__ do AdminService ou na passagem do supabase_client.")
            admin_service_instance = None # Garante que é None se a inicialização interna falhar
    except Exception as e:
        print(f"ERRO CRÍTICO: Exceção ao tentar instanciar AdminService: {e}")
        import traceback
        traceback.print_exc()
        admin_service_instance = None
else:
    print("ERRO CRÍTICO: Cliente Supabase (supabase_service.client) NÃO ESTÁ DISPONÍVEL ou é None.")
    print("              AdminService não pôde ser instanciado. Verifique a inicialização do SupabaseService")
    print("              (em supabase_service.py) e as variáveis de ambiente SUPABASE_URL/KEY no Render.")

# Para permitir importações como 'from app.services import supabase_service, admin_service_instance'
__all__ = ["supabase_service", "admin_service_instance"]
