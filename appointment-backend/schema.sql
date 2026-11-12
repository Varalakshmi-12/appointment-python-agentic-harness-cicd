CREATE DATABASE IF NOT EXISTS appointment_db;
USE appointment_db;

CREATE TABLE IF NOT EXISTS appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_name VARCHAR(255) NOT NULL,
    patient_phone VARCHAR(20),
    provider_name VARCHAR(255),
    patient_email VARCHAR(255),
    appointment_time DATETIME, -- UTC by contract; the API converts at the edges, never store local time
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    cancellation_reason VARCHAR(500) NULL -- optional free-text reason, set only when status becomes 'cancelled'
);

-- Databases created before the status column existed won't get it from
-- CREATE TABLE IF NOT EXISTS above. Run this once against those databases:
-- ALTER TABLE appointments ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'scheduled';

-- Same for the cancellation_reason column. One-time migration: the operator
-- runs this ONCE against existing databases:
-- ALTER TABLE appointments ADD COLUMN cancellation_reason VARCHAR(500) NULL;

-- Rows stored before the UTC contract hold clinic-local times. One-time manual
-- migration: the operator runs this ONCE, after taking a backup, replacing
-- <clinic tz> with the clinic's timezone (e.g. 'America/Chicago'; named zones
-- need the MySQL timezone tables loaded):
-- UPDATE appointments SET appointment_time = CONVERT_TZ(appointment_time, '<clinic tz>', '+00:00');