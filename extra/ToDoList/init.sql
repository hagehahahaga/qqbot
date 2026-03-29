CREATE TABLE `todo_list` (
  `user_id` decimal(65,0) NOT NULL,
  `do` longtext NOT NULL,
  `finished` tinyint(1) NOT NULL DEFAULT 0,
  KEY `todo_list_user_id_finished_index` (`user_id`,`finished`),
  CONSTRAINT `todo_list_qq_users_id_fk` FOREIGN KEY (`user_id`) REFERENCES `qq_users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;