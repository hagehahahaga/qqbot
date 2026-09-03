CREATE TABLE `ai_messages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `target` varchar(10) NOT NULL,
  `role` enum('system','user','assistant') NOT NULL,
  `text` longtext,
  `type` enum('text','image_url') DEFAULT 'text',
  PRIMARY KEY (`id`),
  KEY `ai_messages_target_index` (`target`)
) ENGINE=InnoDB AUTO_INCREMENT=489 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

