import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

log = logging.getLogger(__name__)


@dataclass
class Player:
    username: str
    player_id: int
    ping: int
    is_bot: bool
    is_spectator: bool = False
    joined_at: float = field(default_factory=time.time)


@dataclass
class MatchState:
    status: str = 'WaitingForServer'
    map_name: str = ''
    players: List[Player] = field(default_factory=list)
    match_started_at: Optional[float] = None
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Serialise to the wire format expected by the Discord bot."""
        return {
            'state': self.status,
            'map': self.map_name,
            'players': [
                {
                    'username': p.username,
                    'id': p.player_id,
                    'ping': p.ping,
                    'is_spectator': p.is_spectator,
                    'is_bot': p.is_bot,
                }
                for p in self.players
            ],
            'match_start_time': int(self.match_started_at) if self.match_started_at else 0,
            'events': [],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class MatchStateManager:
    def __init__(self):
        self._state = MatchState()
        self._lock = asyncio.Lock()
        self._on_state_change: List[Callable] = []
        self._on_match_end: List[Callable] = []
        self._on_player_join: List[Callable] = []
        self._on_player_leave: List[Callable] = []

    @property
    def state(self) -> MatchState:
        return self._state

    # ── Callback registration ─────────────────────────────────────────────────

    def on_state_change(self, cb: Callable) -> None:
        """Register a callback invoked with the serialised state dict on any change."""
        self._on_state_change.append(cb)

    def on_match_end(self, cb: Callable) -> None:
        self._on_match_end.append(cb)

    def on_player_join(self, cb: Callable) -> None:
        self._on_player_join.append(cb)

    def on_player_leave(self, cb: Callable) -> None:
        self._on_player_leave.append(cb)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _fire_state_change(self) -> None:
        snapshot = self._state.to_dict()
        for cb in self._on_state_change:
            asyncio.ensure_future(cb(snapshot))

    # ── State mutations ───────────────────────────────────────────────────────

    async def update_from_tracker(self, data: dict) -> None:
        async with self._lock:
            prev_players = {p.username for p in self._state.players}
            new_status = data.get('state', self._state.status)
            raw = data.get('players', [])
            new_players = [
                Player(
                    username=p['username'],
                    player_id=p.get('id', 0),
                    ping=p.get('ping', 0),
                    is_bot=p.get('is_bot', False),
                    is_spectator=p.get('is_spectator', False),
                )
                for p in raw
            ]
            new_usernames = {p.username for p in new_players}

            if new_status == 'InProgress' and self._state.status != 'InProgress':
                self._state.match_started_at = time.time()

            changed = (new_status != self._state.status or new_usernames != prev_players)
            self._state.status = new_status
            self._state.players = new_players
            self._state.last_updated = time.time()

        if changed:
            self._fire_state_change()

        for name in new_usernames - prev_players:
            for cb in self._on_player_join:
                asyncio.ensure_future(cb(name))

        for name in prev_players - new_usernames:
            for cb in self._on_player_leave:
                asyncio.ensure_future(cb(name))

    async def set_server_ready(self) -> None:
        async with self._lock:
            self._state.status = 'WaitingForPlayers'
            self._state.last_updated = time.time()
        self._fire_state_change()

    async def set_map_name(self, map_name: str) -> None:
        async with self._lock:
            if self._state.map_name == map_name:
                return
            self._state.map_name = map_name
            self._state.last_updated = time.time()
        self._fire_state_change()

    async def signal_match_end(self) -> None:
        log.info('Match ended')
        async with self._lock:
            self._state.status = 'Ended'
            self._state.last_updated = time.time()
        self._fire_state_change()
        for cb in self._on_match_end:
            asyncio.ensure_future(cb())

    async def reset(self) -> None:
        async with self._lock:
            self._state = MatchState()
        self._fire_state_change()
