"""
TCP broadcast server: pushes match state JSON to connected clients (Discord bot, etc.).

Clients connect and immediately receive the current state, then receive a
push whenever state changes. The connection stays open until the client
disconnects.
"""

import asyncio
import json
import logging

from .config import Config
from .match_state import MatchStateManager

log = logging.getLogger(__name__)


class BroadcastServer:
    def __init__(self, config: Config, match_state: MatchStateManager):
        self._cfg = config
        self._state = match_state
        self._clients: set[asyncio.StreamWriter] = set()

    async def start(self) -> None:
        server = await asyncio.start_server(
            self._handle_client,
            self._cfg.broadcast_host,
            self._cfg.broadcast_port,
        )
        log.info('Broadcast server on :%d', self._cfg.broadcast_port)
        async with server:
            await server.serve_forever()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        addr = writer.get_extra_info('peername')
        log.debug('Broadcast client connected: %s', addr)
        self._clients.add(writer)
        try:
            await self._send(writer, self._state.state.to_dict())
            await reader.read(1)  # Keep open; unblocks when client disconnects
        except (ConnectionResetError, asyncio.IncompleteReadError, OSError):
            pass
        finally:
            self._clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            log.debug('Broadcast client disconnected: %s', addr)

    async def push_update(self, data: dict) -> None:
        stale: set[asyncio.StreamWriter] = set()
        for writer in list(self._clients):
            try:
                await self._send(writer, data)
            except Exception:
                stale.add(writer)
        self._clients -= stale

    @staticmethod
    async def _send(writer: asyncio.StreamWriter, data: dict) -> None:
        writer.write(json.dumps(data).encode() + b'\n')
        await writer.drain()
