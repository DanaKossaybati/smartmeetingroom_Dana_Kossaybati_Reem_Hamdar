-- ============================================
-- Smart Meeting Room Management System
-- Database Schema (PostgreSQL 17)
-- Authors: Dana Kossaybati, Reem Hamdar
-- Dana Kossaybati: Users, Bookings, Booking_History
-- Reem Hamdar: Rooms, Equipment, Reviews
-- ============================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Drop tables in dependency order
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS booking_history CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS room_equipment CASCADE;
DROP TABLE IF EXISTS equipment CASCADE;
DROP TABLE IF EXISTS rooms CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ============================================
-- USERS TABLE (Team Member 1: Dana)
-- ============================================
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'regular_user'
        CHECK (role IN ('admin', 'regular_user', 'facility_manager', 'moderator', 'auditor', 'service_account')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMPTZ
);

-- Case-insensitive unique constraints (prevents 'john' and 'JOHN' as different users)
CREATE UNIQUE INDEX ux_users_username_ci ON users (LOWER(username));
CREATE UNIQUE INDEX ux_users_email_ci ON users (LOWER(email));
CREATE INDEX idx_users_role ON users(role);

COMMENT ON TABLE users IS 'User accounts with role-based access control';
COMMENT ON COLUMN users.password_hash IS 'Bcrypt hash with cost factor 12 (never store plain text)';
COMMENT ON COLUMN users.role IS 'RBAC roles: admin, regular_user, facility_manager, moderator, auditor, service_account';

-- ============================================
-- ROOMS TABLE (Team Member 2: Reem)
-- ============================================
CREATE TABLE rooms (
    room_id SERIAL PRIMARY KEY,
    room_name VARCHAR(100) NOT NULL UNIQUE,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    location VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'available'
        CHECK (status IN ('available', 'unavailable', 'maintenance')),
    created_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rooms_status ON rooms(status);
CREATE INDEX idx_rooms_capacity ON rooms(capacity);
CREATE INDEX idx_rooms_location ON rooms(location);

COMMENT ON TABLE rooms IS 'Meeting room inventory with capacity and equipment';
COMMENT ON COLUMN rooms.status IS 'Room availability status for booking system';

-- ============================================
-- EQUIPMENT TABLE (Team Member 2: Reem)
-- ============================================
CREATE TABLE equipment (
    equipment_id SERIAL PRIMARY KEY,
    equipment_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE equipment IS 'Types of available equipment (projectors, whiteboards, etc.)';

-- ============================================
-- ROOM_EQUIPMENT JUNCTION TABLE (Team Member 2: Reem)
-- ============================================
CREATE TABLE room_equipment (
    room_equipment_id SERIAL PRIMARY KEY,
    room_id INTEGER NOT NULL REFERENCES rooms(room_id) ON DELETE CASCADE,
    equipment_id INTEGER NOT NULL REFERENCES equipment(equipment_id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 1 CHECK (quantity > 0),
    condition VARCHAR(20) DEFAULT 'good'
        CHECK (condition IN ('new', 'good', 'fair', 'poor', 'broken'))
);

-- Prevent duplicate room-equipment pairs
CREATE UNIQUE INDEX ux_room_equipment_pair ON room_equipment(room_id, equipment_id);
CREATE INDEX idx_room_equipment_room ON room_equipment(room_id);
CREATE INDEX idx_room_equipment_equipment ON room_equipment(equipment_id);

COMMENT ON TABLE room_equipment IS 'Many-to-many relationship between rooms and equipment';

-- ============================================
-- BOOKINGS TABLE (Team Member 1: Dana)
-- ============================================
CREATE TABLE bookings (
    booking_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES rooms(room_id) ON DELETE CASCADE,
    booking_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    status VARCHAR(20) DEFAULT 'confirmed'
        CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed')),
    purpose TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    cancelled_at TIMESTAMPTZ,
    cancelled_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    
    -- Time validation: end must be after start
    CONSTRAINT chk_time_order CHECK (end_time > start_time),
    
    -- Generated range column for automatic conflict detection
    -- Combines booking_date + start_time and booking_date + end_time into a timestamp range
    booking_range tsrange GENERATED ALWAYS AS (
        tsrange(
            (booking_date::timestamp + start_time),
            (booking_date::timestamp + end_time),
            '[)'  -- Inclusive start, exclusive end (standard interval notation)
        )
    ) STORED
);

-- EXCLUSION CONSTRAINT: Automatic conflict detection at database level
-- Prevents overlapping bookings for the same room using GiST indexing
-- This is MORE RELIABLE than application-level checking (handles race conditions)
ALTER TABLE bookings
ADD CONSTRAINT no_overlapping_bookings
EXCLUDE USING gist (
    room_id WITH =,           -- Same room
    booking_range WITH &&     -- Overlapping time ranges
);

CREATE INDEX idx_bookings_user ON bookings(user_id);
CREATE INDEX idx_bookings_room ON bookings(room_id);
CREATE INDEX idx_bookings_date ON bookings(booking_date);
CREATE INDEX idx_bookings_status ON bookings(status);

COMMENT ON TABLE bookings IS 'Room reservations with automatic double-booking prevention';
COMMENT ON COLUMN bookings.booking_range IS 'Generated tsrange used by exclusion constraint for conflict detection';
COMMENT ON CONSTRAINT no_overlapping_bookings ON bookings IS 'Database-level guarantee: no overlapping reservations for same room';

-- ============================================
-- BOOKING_HISTORY TABLE (Team Member 1: Dana)
-- ============================================
CREATE TABLE booking_history (
    history_id SERIAL PRIMARY KEY,
    booking_id INTEGER NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES rooms(room_id) ON DELETE CASCADE,
    action VARCHAR(20) NOT NULL
        CHECK (action IN ('created', 'updated', 'cancelled', 'completed')),
    previous_start_time TIME,
    previous_end_time TIME,
    new_start_time TIME,
    new_end_time TIME,
    changed_by INTEGER,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- ON DELETE SET NULL preserves audit trail even if admin account deleted
    CONSTRAINT booking_history_changed_by_fkey
        FOREIGN KEY (changed_by) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE INDEX idx_booking_history_booking ON booking_history(booking_id);
CREATE INDEX idx_booking_history_timestamp ON booking_history(timestamp);
CREATE INDEX idx_booking_history_action ON booking_history(action);

COMMENT ON TABLE booking_history IS 'Complete immutable audit trail of all booking modifications';
COMMENT ON COLUMN booking_history.changed_by IS 'User who performed the action (NULL if user deleted)';

-- ============================================
-- REVIEWS TABLE (Team Member 2: Reem)
-- ============================================
CREATE TABLE reviews (
    review_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES rooms(room_id) ON DELETE CASCADE,
    booking_id INTEGER UNIQUE REFERENCES bookings(booking_id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    is_flagged BOOLEAN DEFAULT FALSE,
    flag_reason TEXT,
    flagged_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    flagged_at TIMESTAMPTZ,
    is_moderated BOOLEAN DEFAULT FALSE,
    moderated_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    moderated_at TIMESTAMPTZ,
    moderation_action VARCHAR(20) CHECK (moderation_action IN ('approved', 'removed', 'hidden') OR moderation_action IS NULL),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reviews_room ON reviews(room_id);
CREATE INDEX idx_reviews_user ON reviews(user_id);
CREATE INDEX idx_reviews_flagged ON reviews(is_flagged);
CREATE INDEX idx_reviews_rating ON reviews(rating);

COMMENT ON TABLE reviews IS 'Room feedback and ratings with moderation capability';
COMMENT ON COLUMN reviews.booking_id IS 'UNIQUE constraint enforces 1:1 relationship (one review per booking)';

-- ============================================
-- AUDIT_LOGS TABLE (Part II Enhancement - Shared)
-- ============================================
CREATE TABLE audit_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    record_id INTEGER NOT NULL,
    old_value JSONB,
    new_value JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_table ON audit_logs(table_name);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

COMMENT ON TABLE audit_logs IS 'System-wide audit trail using JSONB for flexible change tracking';

-- ============================================
-- AUTOMATIC TIMESTAMP TRIGGERS
-- ============================================

-- Reusable function to update updated_at column
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION set_updated_at() IS 'Trigger function: automatically updates updated_at timestamp on row modification';

-- Apply trigger to all tables with updated_at column
CREATE TRIGGER users_updated_at_trg BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER rooms_updated_at_trg BEFORE UPDATE ON rooms FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER bookings_updated_at_trg BEFORE UPDATE ON bookings FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER reviews_updated_at_trg BEFORE UPDATE ON reviews FOR EACH ROW EXECUTE FUNCTION set_updated_at();