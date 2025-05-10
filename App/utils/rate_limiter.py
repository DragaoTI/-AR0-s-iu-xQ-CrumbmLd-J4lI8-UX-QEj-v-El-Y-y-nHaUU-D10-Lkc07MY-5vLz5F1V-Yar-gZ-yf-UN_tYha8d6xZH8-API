from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings # Para pegar RATE_LIMIT_LOGIN_ATTEMPTS

limiter = Limiter(key_func=get_remote_address, default_limits=["1000/hour", "200/minute"])
# O default_limits acima é um exemplo genérico.
# Você aplicará limites específicos às rotas.
