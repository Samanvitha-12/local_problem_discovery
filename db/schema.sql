-- Database schema for AI-Based Local Problem Detection, Prioritization, and Automated Multi-Action Alert System for Officials

CREATE DATABASE IF NOT EXISTS problem_alert_db;
USE problem_alert_db;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  phone VARCHAR(24) NOT NULL,
  password_hash VARCHAR(256) NOT NULL,
  district VARCHAR(100) NOT NULL,
  taluk VARCHAR(100) NOT NULL,
  village VARCHAR(120) NOT NULL,
  address VARCHAR(256) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS departments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  description VARCHAR(256)
);

CREATE TABLE IF NOT EXISTS officials (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  phone VARCHAR(24) NOT NULL,
  password_hash VARCHAR(256) NOT NULL,
  district VARCHAR(100) NOT NULL,
  taluk VARCHAR(100) NOT NULL,
  village VARCHAR(120) NOT NULL,
  address VARCHAR(256) NOT NULL,
  employee_id VARCHAR(64) NOT NULL UNIQUE,
  department_id INT,
  designation VARCHAR(120) NOT NULL,
  office_address VARCHAR(256) NOT NULL,
  identity_card_url VARCHAR(256),
  approved BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS admins (
  id INT AUTO_INCREMENT PRIMARY KEY,
  admin_id VARCHAR(64) NOT NULL UNIQUE,
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(256) NOT NULL,
  full_name VARCHAR(120) NOT NULL,
  phone VARCHAR(24),
  department VARCHAR(120),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS complaint_status (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(64) NOT NULL UNIQUE,
  description VARCHAR(256)
);

CREATE TABLE IF NOT EXISTS complaints (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(180) NOT NULL,
  category VARCHAR(120) NOT NULL,
  description TEXT NOT NULL,
  priority VARCHAR(24) NOT NULL DEFAULT 'Normal',
  priority_score INT NOT NULL DEFAULT 0,
  location VARCHAR(256) NOT NULL,
  latitude VARCHAR(64),
  longitude VARCHAR(64),
  status_id INT NOT NULL,
  user_id INT NOT NULL,
  official_id INT,
  remarks VARCHAR(512),
  ai_category VARCHAR(120),
  ai_confidence FLOAT,
  sla_due_at DATETIME,
  reminder_sent_at DATETIME,
  escalated_at DATETIME,
  cluster_id INT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (status_id) REFERENCES complaint_status(id),
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (official_id) REFERENCES officials(id)
);

CREATE TABLE IF NOT EXISTS notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT,
  official_id INT,
  message VARCHAR(256) NOT NULL,
  read BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (official_id) REFERENCES officials(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS complaint_history (
  id INT AUTO_INCREMENT PRIMARY KEY,
  complaint_id INT NOT NULL,
  status_name VARCHAR(64) NOT NULL,
  note VARCHAR(512),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS emergency_alerts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  complaint_id INT NOT NULL,
  official_id INT,
  message VARCHAR(512) NOT NULL,
  contact_number VARCHAR(24),
  status VARCHAR(32) NOT NULL DEFAULT 'queued',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
  FOREIGN KEY (official_id) REFERENCES officials(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  complaint_id INT NOT NULL,
  url VARCHAR(256) NOT NULL,
  phase VARCHAR(64),
  media_type VARCHAR(16) NOT NULL DEFAULT 'image',
  uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS complaint_clusters (
  id INT AUTO_INCREMENT PRIMARY KEY,
  category VARCHAR(120) NOT NULL,
  latitude FLOAT NOT NULL,
  longitude FLOAT NOT NULL,
  radius_meters INT NOT NULL DEFAULT 200,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evidence_validations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  complaint_id INT NULL,
  user_id INT NOT NULL,
  selected_category VARCHAR(120) NOT NULL,
  detected_category VARCHAR(120),
  confidence FLOAT,
  image_path VARCHAR(256),
  preview_path VARCHAR(256),
  content_sha256 VARCHAR(64) NOT NULL UNIQUE,
  validation_status VARCHAR(16) NOT NULL,
  message VARCHAR(512) NOT NULL,
  model_version VARCHAR(128),
  predicted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE SET NULL
  ,FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  event VARCHAR(256) NOT NULL,
  details TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT IGNORE INTO complaint_status (name, description) VALUES
('Submitted', 'Complaint has been logged and is pending assignment'),
('In Progress', 'Assigned official is working on the complaint'),
('Resolved', 'Complaint has been addressed'),
('Escalated', 'Complaint has been escalated to a higher authority');

INSERT IGNORE INTO departments (name, description) VALUES
('Public Works', 'Infrastructure, drains, and street maintenance'),
('Water Management', 'Water supply and pipeline services'),
('Sanitation', 'Waste, garbage, and cleaning services'),
('Traffic and Safety', 'Road safety, signals, and traffic coordination');
