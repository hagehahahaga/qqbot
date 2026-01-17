CREATE TABLE `ai_messages` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `target` varchar(10) NOT NULL,
  `role` enum('system','user','assistant') NOT NULL,
  `text` longtext DEFAULT NULL,
  `type` enum('text','image_url') DEFAULT 'text',
  PRIMARY KEY (`id`),
  KEY `ai_messages_target_index` (`target`)
) ENGINE=InnoDB AUTO_INCREMENT=489 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `arcades` (
  `group_id` decimal(10,0) NOT NULL,
  `name` tinytext NOT NULL,
  `subnames` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT '[]' CHECK (json_valid(`subnames`)),
  `names` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin GENERATED ALWAYS AS (json_array_append(`subnames`,'$',`name`)) VIRTUAL,
  `num` tinyint(3) unsigned DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  KEY `group_id` (`group_id`,`name`(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `game_data` (
  `id` decimal(65,0) NOT NULL,
  `black_list` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT '[]' CHECK (json_valid(`black_list`)),
  `game_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT '{}' CHECK (json_valid(`game_data`)),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `group_options` (
  `id` decimal(65,0) NOT NULL,
  `trusted` tinyint(1) DEFAULT 0,
  `r18` tinyint(1) DEFAULT 0,
  `recall_catch` tinyint(1) DEFAULT 0,
  `city` varchar(30) DEFAULT NULL,
  `weather_notice` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  CONSTRAINT `check_trusted` CHECK (`trusted` = 1 and 2 >= `r18` >= 0 or `trusted` = 0 and `r18` = 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `notice_schedule` (
  `id` decimal(65,0) NOT NULL,
  `type` enum('group','private') NOT NULL,
  `time` datetime NOT NULL,
  `text` longtext DEFAULT NULL,
  `every` enum('day','week') DEFAULT NULL,
  KEY `notice_schedule_time_index` (`time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `qq_users` (
  `id` decimal(65,0) NOT NULL,
  `points` decimal(65,0) DEFAULT 0,
  `sign_date` date DEFAULT '1000-01-01',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `stocks` (
  `id` decimal(65,0) NOT NULL,
  `stocks` decimal(10,0) DEFAULT 0,
  `stocks_bought` decimal(10,0) DEFAULT 0,
  `points_sold` decimal(10,0) DEFAULT 0,
  `commission_type` enum('buy','sell','none') DEFAULT 'none',
  `commission_price` decimal(10,0) DEFAULT 0,
  `commission_num` decimal(10,0) DEFAULT 0,
  `commission_time` datetime DEFAULT '1000-01-01 00:00:00',
  `points_sold_using` decimal(10,0) DEFAULT 0,
  `trade_price` decimal(10,0) DEFAULT 0,
  `trade_num` decimal(10,0) DEFAULT 0,
  `trade_time` datetime DEFAULT '1000-01-01 00:00:00',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

