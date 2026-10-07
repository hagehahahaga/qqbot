CREATE TABLE `arcades` (
  `hash` binary(32) GENERATED ALWAYS AS (unhex(sha2(concat(`name`,`group_id`),256))) STORED,
  `group_id` decimal(12,0) NOT NULL,
  `name` tinytext NOT NULL,
  `subnames` json NOT NULL DEFAULT (_utf8mb4'[]'),
  `num` tinyint unsigned DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  `update_user_id` decimal(10,0) DEFAULT NULL,
  UNIQUE KEY `arcades_hash_unique` (`hash`),
  KEY `arcades_hash_index` (`hash`),
  KEY `arcades_group_options_id_fk` (`group_id`),
  CONSTRAINT `arcades_group_options_id_fk` FOREIGN KEY (`group_id`) REFERENCES `group_options` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE `arcades_bind` (
  `type` enum('group','private') NOT NULL,
  `id` decimal(12,0) NOT NULL,
  `hash` binary(32) NOT NULL,
  `names` json NOT NULL DEFAULT (_utf8mb4'[]'),
  KEY `arcades_bind_type_id_index` (`type`,`id`),
  KEY `arcades_bind_arcades_hash_fk` (`hash`),
  CONSTRAINT `arcades_bind_arcades_hash_fk` FOREIGN KEY (`hash`) REFERENCES `arcades` (`hash`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE `arcades_cabs` (
  `hash` binary(32) NOT NULL,
  `name` tinytext NOT NULL,
  `slot` tinyint unsigned NOT NULL DEFAULT '2',
  `tracks` tinyint unsigned NOT NULL DEFAULT '3',
  `must_pickup` tinyint(1) DEFAULT '1',
  `pickup_bonus` tinyint(1) DEFAULT '1',
  `num` tinyint unsigned DEFAULT NULL,
  KEY `arcades_cabs_arcades_hash_fk` (`hash`),
  CONSTRAINT `arcades_cabs_arcades_hash_fk` FOREIGN KEY (`hash`) REFERENCES `arcades` (`hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
