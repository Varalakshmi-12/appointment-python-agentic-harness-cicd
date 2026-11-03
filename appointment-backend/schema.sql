CREATE DATABASE IF NOT EXISTS appointment_db;
USE appointment_db;

CREATE TABLE IF NOT EXISTS appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_name VARCHAR(255) NOT NULL,
    patient_phone VARCHAR(20),
    provider_name VARCHAR(255),
    patient_email VARCHAR(255),
    appointment_time DATETIME,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled'
);

-- Databases created before the status column existed won't get it from
-- CREATE TABLE IF NOT EXISTS above. Run this once against those databases:
-- ALTER TABLE appointments ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'scheduled';