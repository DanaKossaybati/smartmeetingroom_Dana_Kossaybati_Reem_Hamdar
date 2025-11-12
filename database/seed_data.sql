-- Smart Meeting Room Management System - Seed Data
-- Authors: Dana Kossaybati, Reem Hamdar

-- USERS
INSERT INTO users (username, password_hash, email, full_name, role) VALUES
('dana_k', '$2b$12$9Bx8YXzk19q6WGr1o/NpB.xl2p4YzqQfqMZPYg9TRrWw2b6Uq9Fhe', 'dak39@mail.aub.edu', 'Dana Kossaybati', 'admin'),
('reem_h', '$2b$12$9Bx8YXzk19q6WGr1o/NpB.xl2p4YzqQfqMZPYg9TRrWw2b6Uq9Fhe', 'rsh44@mail.aub.edu', 'Reem Hamdar', 'facility_manager'),
('fadi_karam', '$2b$12$9Bx8YXzk19q6WGr1o/NpB.xl2p4YzqQfqMZPYg9TRrWw2b6Uq9Fhe', 'fk21@mail.aub.edu', 'Fadi Karam', 'regular_user'),
('mira_sleiman', '$2b$12$9Bx8YXzk19q6WGr1o/NpB.xl2p4YzqQfqMZPYg9TRrWw2b6Uq9Fhe', 'ms45@mail.aub.edu', 'Mira Sleiman', 'moderator'),
('karim_tarek', '$2b$12$9Bx8YXzk19q6WGr1o/NpB.xl2p4YzqQfqMZPYg9TRrWw2b6Uq9Fhe', 'kt88@mail.aub.edu', 'Karim Tarek', 'regular_user');

-- EQUIPMENT
INSERT INTO equipment (equipment_name) VALUES
('Projector'),
('Whiteboard'),
('Conference Phone'),
('Smart TV'),
('HD Camera'),
('Air Conditioner');

-- ROOMS
INSERT INTO rooms (room_name, capacity, location, status) VALUES
('Innovation Lab', 12, 'Engineering Building, Floor 2', 'available'),
('Design Studio', 8, 'Architecture Wing, Floor 1', 'available'),
('Team Meeting Room', 6, 'Engineering Building, Floor 3', 'available'),
('Seminar Hall', 25, 'Main Campus, Ground Floor', 'available');

-- ROOM-EQUIPMENT ASSIGNMENTS
INSERT INTO room_equipment (room_id, equipment_id, quantity) VALUES
(1, 1, 1), -- Innovation Lab - Projector
(1, 2, 2), -- Innovation Lab - Whiteboards
(2, 4, 1), -- Design Studio - Smart TV
(3, 3, 1), -- Team Meeting Room - Conference Phone
(4, 5, 2), -- Seminar Hall - HD Cameras
(4, 1, 1); -- Seminar Hall - Projector

-- BOOKINGS
INSERT INTO bookings (user_id, room_id, booking_date, start_time, end_time, status, purpose) VALUES
(3, 1, '2025-11-14', '10:00:00', '11:30:00', 'confirmed', 'Team design discussion'),
(5, 3, '2025-11-14', '14:00:00', '15:00:00', 'confirmed', 'Client call with architecture firm'),
(4, 2, '2025-11-15', '09:00:00', '10:30:00', 'confirmed', 'Department meeting'),
(2, 4, '2025-11-15', '11:00:00', '13:00:00', 'confirmed', 'Facility inspection preparation');

-- BOOKING HISTORY
INSERT INTO booking_history (booking_id, action, changed_by) VALUES
(1, 'created', 3),
(2, 'created', 5),
(3, 'created', 4),
(4, 'created', 2),
(2, 'updated', 5);

-- REVIEWS
INSERT INTO reviews (user_id, room_id, rating, comment) VALUES
(3, 1, 5, 'Spacious and well-equipped lab. The projector worked perfectly.'),
(5, 3, 4, 'Good meeting room, though sound insulation could be better.'),
(4, 2, 5, 'Excellent lighting and comfortable seating.'),
(2, 4, 4, 'Great hall for presentations, minor echo issues.'),
(3, 2, 3, 'Decent space, but projector connectivity took time.');
