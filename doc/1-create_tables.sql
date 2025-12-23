-- step 1: Make sure database default charset is also utf8mb4: for Lao unicode

ALTER DATABASE apb_msp
CHARACTER SET utf8mb4
COLLATE utf8mb4_0900_ai_ci;

-- step 2: create main table:

-- --------------------------------------------------------
-- Database: `apb_msp`
-- --------------------------------------------------------

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

-- --------------------------------------------------------
-- Table structure for table `msp`
-- --------------------------------------------------------

CREATE TABLE `msp` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `trn_id` VARCHAR(20) NOT NULL,
  `trn_desc` VARCHAR(250) NOT NULL,
  `status` VARCHAR(50) NOT NULL,
  `fail_reason` VARCHAR(250) DEFAULT NULL,

  `bis_date` DATETIME NOT NULL,
  `create_date` DATETIME NOT NULL,
  `update_date` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_trn_id` (`trn_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;

COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;


-- step 3: create tbl_dr

CREATE TABLE `tbl_dr` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `trn_id` VARCHAR(20) NOT NULL,
  `db_ac` VARCHAR(20) NOT NULL,
  `db_amt` DECIMAL(18,2) NOT NULL,
  `db_desc` VARCHAR(250) DEFAULT NULL,

  PRIMARY KEY (`id`),
  KEY `idx_dr_trn_id` (`trn_id`),

  CONSTRAINT `fk_dr_msp`
    FOREIGN KEY (`trn_id`)
    REFERENCES `msp` (`trn_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;


-- step 4: create tbl_cr

CREATE TABLE `tbl_cr` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `trn_id` VARCHAR(20) NOT NULL,
  `cr_ac` VARCHAR(20) NOT NULL,
  `cr_amt` DECIMAL(18,2) NOT NULL,
  `cr_desc` VARCHAR(250) DEFAULT NULL,

  PRIMARY KEY (`id`),
  KEY `idx_cr_trn_id` (`trn_id`),

  CONSTRAINT `fk_cr_msp`
    FOREIGN KEY (`trn_id`)
    REFERENCES `msp` (`trn_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;