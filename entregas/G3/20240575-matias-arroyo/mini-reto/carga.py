#!/usr/bin/env python3
"""Carga del mini-reto G3 (Discord) en el keyspace discord_20240575.

Cassandra no tiene JOIN: los JOIN de consultas.sql se hacen aqui, una sola vez,
al cargar. El script lee los CSV relacionales de data/mini-reto/G3-discord/,
arma un CSV ya desnormalizado por cada tabla de modelo.cql, los copia al
contenedor y los carga con COPY FROM, con CONSISTENCY QUORUM.

Uso, desde la carpeta del repo y con modelo.cql ya ejecutado:

    python3 entregas/G3/20240575-matias-arroyo/mini-reto/carga.py [nodo]

nodo: el contenedor de Cassandra de esta laptop (por defecto, cassandra3).
"""
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

KEYSPACE = "discord_20240575"
NODO = sys.argv[1] if len(sys.argv) > 1 else "cassandra3"
ORIGEN = Path(__file__).resolve().parents[4] / "data" / "mini-reto" / "G3-discord"
DESTINO = "/tmp/discord_carga"


def leer(nombre):
    with open(ORIGEN / nombre, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def utc(ts):
    # Las horas de los CSV estan en UTC: se marca explicitamente.
    return ts + "+0000"


def escribir(carpeta, tabla, columnas, filas):
    with open(Path(carpeta) / f"{tabla}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(columnas)
        w.writerows(filas)
    return tabla, columnas, len(filas)


def main():
    servidores = {s["servidor_id"]: s for s in leer("servidores.csv")}
    canales = {c["canal_id"]: c for c in leer("canales.csv")}
    usuarios = {u["usuario_id"]: u for u in leer("usuarios.csv")}
    mensajes = leer("mensajes.csv")

    with tempfile.TemporaryDirectory() as tmp:
        tablas = [
            # C1: usuarios tal cual.
            escribir(tmp, "usuarios_por_id",
                     ["usuario_id", "nombre_usuario", "creado_en"],
                     [[u["usuario_id"], u["nombre_usuario"], utc(u["creado_en"])]
                      for u in usuarios.values()]),
            # C2: mensajes JOIN usuarios.
            escribir(tmp, "mensajes_por_canal",
                     ["canal_id", "enviado_en", "mensaje_id", "usuario_id", "nombre_usuario", "contenido"],
                     [[m["canal_id"], utc(m["enviado_en"]), m["mensaje_id"], m["usuario_id"],
                       usuarios[m["usuario_id"]]["nombre_usuario"], m["contenido"]]
                      for m in mensajes]),
            # C3: mensajes JOIN canales JOIN servidores.
            escribir(tmp, "mensajes_por_usuario",
                     ["usuario_id", "enviado_en", "mensaje_id", "canal_id", "canal",
                      "servidor_id", "servidor", "contenido"],
                     [[m["usuario_id"], utc(m["enviado_en"]), m["mensaje_id"], m["canal_id"],
                       canales[m["canal_id"]]["nombre"], canales[m["canal_id"]]["servidor_id"],
                       servidores[canales[m["canal_id"]]["servidor_id"]]["nombre"], m["contenido"]]
                      for m in mensajes]),
            # C4: mensajes agrupados por canal y dia (UTC).
            escribir(tmp, "mensajes_por_canal_y_dia",
                     ["canal_id", "dia", "enviado_en", "mensaje_id"],
                     [[m["canal_id"], m["enviado_en"][:10], utc(m["enviado_en"]), m["mensaje_id"]]
                      for m in mensajes]),
        ]

        subprocess.run(["docker", "exec", NODO, "rm", "-rf", DESTINO], check=True)
        subprocess.run(["docker", "cp", tmp, f"{NODO}:{DESTINO}"], check=True)

        for tabla, columnas, n in tablas:
            print(f"== {KEYSPACE}.{tabla}: {n} filas")
            # COPY usa la consistencia de la sesion de cqlsh.
            copy = (f"CONSISTENCY QUORUM; COPY {KEYSPACE}.{tabla} ({', '.join(columnas)}) "
                    f"FROM '{DESTINO}/{tabla}.csv' WITH HEADER = true;")
            r = subprocess.run(["docker", "exec", NODO, "cqlsh", "-e", copy],
                               capture_output=True, text=True)
            print((r.stdout.strip().splitlines() or [""])[-1])
            if r.returncode != 0:
                sys.exit(r.stderr)

        subprocess.run(["docker", "exec", NODO, "rm", "-rf", DESTINO], check=True)


if __name__ == "__main__":
    main()
