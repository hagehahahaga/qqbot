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