CREATE TABLE `ai_messages` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `target` varchar(10) NOT NULL,
  `role` enum('system','user','assistant') NOT NULL,
  `text` longtext DEFAULT NULL,
  `type` enum('text','image_url') DEFAULT 'text',
  PRIMARY KEY (`id`),
  KEY `ai_messages_target_index` (`target`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

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
  `maimai_notice` tinyint(1) NOT NULL DEFAULT 0,
  `night_disturb` tinyint(1) NOT NULL DEFAULT 1,
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
  `todo_notice` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
