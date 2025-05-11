import httpx
from app.core.config import settings
from typing import Optional, Dict

async def get_geoip_data(ip_address: str) -> Optional[Dict]:
    if ip_address == "127.0.0.1" or ip_address == "localhost": # ipapi.co não resolve localhost
        return {"ip": ip_address, "city": "Localhost", "country_name": "Local Network", "org": "Local Machine"}

    url = f"{settings.IPAPI_URL}/{ip_address}/json/"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0) # Timeout de 5s
            response.raise_for_status() # Lança exceção para 4xx/5xx
            data = response.json()
            # print(f"GeoIP Data for {ip_address}: {data}") # Debug
            # Mapear para os campos que queremos, ipapi.co pode ter nomes diferentes
            return {
                "ip": data.get("ip"),
                "city": data.get("city"),
                "region": data.get("region"),
                "country_name": data.get("country_name") or data.get("country"), # ipapi usa country_name
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "org": data.get("org") # ISP / Organização
            }
    except httpx.HTTPStatusError as e:
        print(f"Erro HTTP ao buscar GeoIP para {ip_address}: {e.response.status_code} - {e.response.text}")
        return None
    except httpx.RequestError as e:
        print(f"Erro de requisição ao buscar GeoIP para {ip_address}: {e}")
        return None
    except Exception as e:
        print(f"Erro inesperado ao buscar GeoIP para {ip_address}: {e}")
        return None
