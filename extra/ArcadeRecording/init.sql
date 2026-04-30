CREATE TABLE `arcades` (
  `hash` binary(32) GENERATED ALWAYS AS (unhex(sha2(concat(`name`,`group_id`),256))) STORED,
  `group_id` decimal(10,0) NOT NULL,
  `name` tinytext NOT NULL,
  `subnames` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT '[]' CHECK (json_valid(`subnames`)),
  `names` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin GENERATED ALWAYS AS (json_array_append(`subnames`,'$',`name`)) VIRTUAL,
  `num` tinyint(3) unsigned DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  `update_user_id` decimal(10,0) DEFAULT NULL,
  UNIQUE KEY `arcades_pk` (`group_id`,`name`) USING HASH,
  KEY `arcades_hash_index` (`hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `arcades_bind` (
  `type` enum('group','private') NOT NULL,
  `id` decimal(65,0) NOT NULL,
  `hash` binary(32) NOT NULL,
  `names` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT '[]',
  KEY `arcades_bind_type_id_index` (`type`,`id`),
  KEY `arcades_bind_arcades_hash_fk` (`hash`),
  CONSTRAINT `arcades_bind_arcades_hash_fk` FOREIGN KEY (`hash`) REFERENCES `arcades` (`hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
