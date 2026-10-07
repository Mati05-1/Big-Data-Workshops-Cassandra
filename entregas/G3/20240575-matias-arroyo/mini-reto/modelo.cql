-- Mini-reto G3 · Discord: del modelo relacional a Cassandra
-- Matias Arroyo (20240575) · cluster UFM-G3, datacenter dc-g3
--
-- Una tabla por consulta de consultas.sql. Sin JOIN: cada tabla ya trae
-- copiados los datos de las otras tablas que su consulta necesita.

CREATE KEYSPACE IF NOT EXISTS discord_20240575
  WITH replication = {'class': 'NetworkTopologyStrategy', 'dc-g3': 3};

-- C1. Perfil de un usuario.
-- Una particion por usuario, con una sola fila.
CREATE TABLE IF NOT EXISTS discord_20240575.usuarios_por_id (
  usuario_id     text,
  nombre_usuario text,
  creado_en      timestamp,
  PRIMARY KEY ((usuario_id))
);

-- C2. Los 20 mensajes mas recientes de un canal, con el autor.
-- Una particion por canal, ordenada del mensaje mas reciente al mas antiguo.
-- nombre_usuario se copia de usuarios (reemplaza el JOIN).
CREATE TABLE IF NOT EXISTS discord_20240575.mensajes_por_canal (
  canal_id       text,
  enviado_en     timestamp,
  mensaje_id     int,
  usuario_id     text,
  nombre_usuario text,
  contenido      text,
  PRIMARY KEY ((canal_id), enviado_en, mensaje_id)
) WITH CLUSTERING ORDER BY (enviado_en DESC, mensaje_id ASC);

-- C3. Los 10 mensajes mas recientes de un usuario, con el canal y el servidor.
-- Una particion por usuario, ordenada del mas reciente al mas antiguo.
-- canal y servidor (nombres) se copian de canales y servidores (reemplazan dos JOIN).
CREATE TABLE IF NOT EXISTS discord_20240575.mensajes_por_usuario (
  usuario_id  text,
  enviado_en  timestamp,
  mensaje_id  int,
  canal_id    text,
  canal       text,
  servidor_id text,
  servidor    text,
  contenido   text,
  PRIMARY KEY ((usuario_id), enviado_en, mensaje_id)
) WITH CLUSTERING ORDER BY (enviado_en DESC, mensaje_id ASC);

-- C4. Cuantos mensajes tuvo un canal en un dia.
-- Una particion por canal y dia (dia en UTC): el conteo lee una sola
-- particion pequena, y las particiones no crecen sin limite.
CREATE TABLE IF NOT EXISTS discord_20240575.mensajes_por_canal_y_dia (
  canal_id   text,
  dia        date,
  enviado_en timestamp,
  mensaje_id int,
  PRIMARY KEY ((canal_id, dia), enviado_en, mensaje_id)
) WITH CLUSTERING ORDER BY (enviado_en DESC, mensaje_id ASC);
