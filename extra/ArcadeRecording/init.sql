CREATE TABLE `arcades` (
  `group_id` decimal(10,0) NOT NULL,
  `name` tinytext NOT NULL,
  `subnames` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT '[]' CHECK (json_valid(`subnames`)),
  `names` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin GENERATED ALWAYS AS (json_array_append(`subnames`,'$',`name`)) VIRTUAL,
  `num` tinyint(3) unsigned DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  `update_user_id` decimal(10,0) DEFAULT NULL,
  KEY `group_id` (`group_id`,`name`(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;