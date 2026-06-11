import logging
from typing import Optional

from .database import Database

log = logging.getLogger(__name__)


class BanHandler:
    def __init__(self, db: Database):
        self._db = db

    async def is_banned(
        self, ip_address: str, user_id: Optional[int] = None
    ) -> tuple[bool, str]:
        """
        Returns (banned, reason). IP is checked before account so a banned IP
        cannot bypass by using a clean account.
        """
        if await self._db.is_ip_banned(ip_address):
            log.info('Rejected banned IP: %s', ip_address)
            return True, 'ip_banned'

        if user_id is not None and await self._db.is_user_banned(user_id):
            log.info('Rejected banned account %d from %s', user_id, ip_address)
            return True, 'account_banned'

        return False, ''
