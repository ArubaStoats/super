from .. import settings

from .redis import SuperRedis
from .eightball import eightball_options

R = SuperRedis(host=settings.SUPER_REDIS_HOST, port=settings.SUPER_REDIS_PORT,)
