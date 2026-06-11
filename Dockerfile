FROM brendoncintas/spellbreak_game_server:latest

RUN pip3 install --no-cache-dir aiosqlite

ENV WINEDLLOVERRIDES=match_tracker.dll=n,b

COPY elefrac/            /spellbreak-server/elefrac/
COPY elefrac.config.ini  /spellbreak-server/config.ini
COPY docker-entrypoint.sh /spellbreak-server/docker-entrypoint.sh
RUN chmod +x /spellbreak-server/docker-entrypoint.sh

WORKDIR /spellbreak-server
ENTRYPOINT ["/bin/sh", "-c"]
CMD ["/spellbreak-server/docker-entrypoint.sh"]
