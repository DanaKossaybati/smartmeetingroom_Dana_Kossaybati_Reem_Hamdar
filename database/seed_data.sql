-- ============================================
-- Smart Meeting Room Management System
-- Seed Data (Test/Development)
-- Authors: Dana Kossaybati, Reem Hamdar
-- Password for all users: Password123!
-- ============================================

-- ============================================
-- USERS
-- ============================================
INSERT INTO users (username, password_hash, email, full_name, role) VALUES
('dana_k', '$2b$12$9Bx8YXzk19q6WGr1o/NpB.xl2p4YzqQfqMZPYg9TRrWw2b6Uq9Fhe', 'dak39@mail.aub.edu', 'Dana Kossaybati', 'admin'),
('reem_h', '$2b$12$9Bx8YXzk19q6WGr1o/NpB.xl2p4YzqQfqMZPYg9TRrWw2b6Uq9Fhe', 'rsh44@mail.aub.edu', 'Reem Hamdar', 'facility_manager'),
('fadi_karam', '$2b$12$9Bx8YXzk19q6WGr1o/NpB.xl2p4YzqQfqMZPYg9TRrWw2b6Uq9Fhe', 'fk21@mail.aub.edu', 'Fadi Karam', 'regular_user'),
('mira_sleiman', '$2b$12$9Bx8YXzk19q6WGr1o/NpB.xl2p4YzqQfqMZPYg9TRrWw2b6Uq9Fhe', 'ms45@mail.aub.edu', 'Mira Sleiman', 'moderator'),
('karim_tarek', '$2b$12$9Bx8YXzk19q6WGr1o/NpB.xl2p4YzqQfqMZPYg9TRrWw2b6Uq9Fhe', 'kt88@mail.aub.edu', 'Karim Tarek', 'regular_user');

-- ============================================
-- EQUIPMENT
-- ============================================
INSERT INTO equipment (equipment_name, description) VALUES
('Projector', 'HD Projector with HDMI and wireless connectivity'),
('Whiteboard', 'Large magnetic whiteboard with markers'),
('Conference Phone', 'Professional conference phone with echo cancellation'),
('Smart TV', '55-inch 4K Smart TV with wireless screen sharing'),
('HD Camera', 'High-definition camera for video conferencing'),
('Air Conditioner', 'Climate control system');

-- ============================================
-- ROOMS
-- ============================================
INSERT INTO rooms (room_name, capacity, location, description, status, created_by) VALUES
('Innovation Lab', 12, 'Engineering Building, Floor 2', 'Collaborative workspace with whiteboards', 'available', 1),
('Design Studio', 8, 'Architecture Wing, Floor 1', 'Creative space with large displays', 'available', 2),
('Team Meeting Room', 6, 'Engineering Building, Floor 3', 'Small meeting room with video conferencing', 'available', 2),
('Seminar Hall', 25, 'Main Campus, Ground Floor', 'Large presentation hall with theater seating', 'available', 1);

-- ============================================
-- ROOM-EQUIPMENT ASSIGNMENTS
-- ============================================
INSERT INTO room_equipment (room_id, equipment_id, quantity, condition) VALUES
(1, 1, 1, 'good'),   -- Innovation Lab - Projector
(1, 2, 2, 'good'),   -- Innovation Lab - 2 Whiteboards
(2, 4, 1, 'good'),   -- Design Studio - Smart TV
(2, 6, 1, 'good'),   -- Design Studio - AC
(3, 3, 1, 'good'),   -- Team Meeting Room - Conference Phone
(3, 5, 1, 'good'),   -- Team Meeting Room - HD Camera
(4, 5, 2, 'good'),   -- Seminar Hall - 2 HD Cameras
(4, 1, 1, 'good');   -- Seminar Hall - Projector

-- ============================================
-- BOOKINGS
-- ============================================
INSERT INTO bookings (user_id, room_id, booking_date, start_time, end_time, status, purpose) VALUES
(3, 1, '2025-11-20', '10:00:00', '11:30:00', 'confirmed', 'Team design discussion'),
(5, 3, '2025-11-20', '14:00:00', '15:00:00', 'confirmed', 'Client call with architecture firm'),
(4, 2, '2025-11-21', '09:00:00', '10:30:00', 'confirmed', 'Department meeting'),
(2, 4, '2025-11-21', '11:00:00', '13:00:00', 'confirmed', 'Facility inspection preparation'),
(3, 1, '2025-11-22', '14:00:00', '16:00:00', 'pending', 'Project planning session');

-- ============================================
-- BOOKING HISTORY
-- ============================================
INSERT INTO booking_history (booking_id, user_id, room_id, action, changed_by, new_start_time, new_end_time) VALUES
(1, 3, 1, 'created', 3, '10:00:00', '11:30:00'),
(2, 5, 3, 'created', 5, '14:00:00', '15:00:00'),
(3, 4, 2, 'created', 4, '09:00:00', '10:30:00'),
(4, 2, 4, 'created', 2, '11:00:00', '13:00:00'),
(5, 3, 1, 'created', 3, '14:00:00', '16:00:00');

-- ============================================
-- REVIEWS
-- ============================================
INSERT INTO reviews (user_id, room_id, booking_id, rating, comment) VALUES
(3, 1, 1, 5, 'Spacious and well-equipped lab. The projector worked perfectly.'),
(5, 3, 2, 4, 'Good meeting room, though sound insulation could be better.'),
(4, 2, 3, 5, 'Excellent lighting and comfortable seating.'),
(2, 4, 4, 4, 'Great hall for presentations, minor echo issues.');