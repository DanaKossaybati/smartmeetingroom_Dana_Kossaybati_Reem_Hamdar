"""
Rooms Service - Smart Meeting Room Management System
Handles room management, equipment, and availability.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import requests
import bleach
from functools import wraps

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://admin:admin123@localhost:5432/smartmeeting')
USERS_SERVICE_URL = os.getenv('USERS_SERVICE_URL', 'http://localhost:5001')


def get_db_connection():
    """
    Establish database connection.
    
    Returns:
        psycopg2.connection: Database connection object
    """
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


def sanitize_input(text):
    """
    Sanitize user input to prevent XSS attacks.
    
    Args:
        text (str): Input text to sanitize
        
    Returns:
        str: Sanitized text
    """
    if text is None:
        return None
    return bleach.clean(str(text))


def verify_token(token):
    """
    Verify token with Users Service.
    
    Args:
        token (str): JWT token
        
    Returns:
        dict: User data if valid, None otherwise
    """
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f'{USERS_SERVICE_URL}/api/users/verify', headers=headers)
        
        if response.status_code == 200:
            return response.json()['user']
        return None
    except:
        return None


def token_required(f):
    """
    Decorator to require valid JWT token.
    
    Args:
        f: Function to wrap
        
    Returns:
        function: Wrapped function
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
            
        if token.startswith('Bearer '):
            token = token[7:]
        
        current_user = verify_token(token)
        if not current_user:
            return jsonify({'error': 'Invalid or expired token'}), 401
            
        return f(current_user, *args, **kwargs)
    
    return decorated


def admin_or_facility_required(f):
    """
    Decorator to require admin or facility_manager role.
    
    Args:
        f: Function to wrap
        
    Returns:
        function: Wrapped function
    """
    @wraps(f)
    @token_required
    def decorated(current_user, *args, **kwargs):
        if current_user['role'] not in ['admin', 'facility_manager']:
            return jsonify({'error': 'Admin or Facility Manager access required'}), 403
        return f(current_user, *args, **kwargs)
    
    return decorated


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        JSON: Service status
    """
    return jsonify({'status': 'healthy', 'service': 'rooms'}), 200


@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    """
    Get all rooms with optional filters.
    
    Query Parameters:
        capacity (int, optional): Minimum capacity
        location (str, optional): Location filter
        status (str, optional): Room status filter
        equipment (str, optional): Comma-separated equipment names
        
    Returns:
        JSON: List of rooms matching criteria
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Base query
        query = """
            SELECT DISTINCT r.room_id, r.room_name, r.capacity, r.location, r.status
            FROM rooms r
            WHERE 1=1
        """
        params = []
        
        # Apply filters
        if 'capacity' in request.args:
            query += " AND r.capacity >= %s"
            params.append(int(request.args['capacity']))
        
        if 'location' in request.args:
            query += " AND r.location ILIKE %s"
            params.append(f"%{sanitize_input(request.args['location'])}%")
        
        if 'status' in request.args:
            query += " AND r.status = %s"
            params.append(sanitize_input(request.args['status']))
        
        if 'equipment' in request.args:
            equipment_names = [sanitize_input(e.strip()) for e in request.args['equipment'].split(',')]
            query += """
                AND r.room_id IN (
                    SELECT re.room_id 
                    FROM room_equipment re
                    JOIN equipment e ON re.equipment_id = e.equipment_id
                    WHERE e.equipment_name = ANY(%s)
                    GROUP BY re.room_id
                    HAVING COUNT(DISTINCT e.equipment_name) = %s
                )
            """
            params.extend([equipment_names, len(equipment_names)])
        
        query += " ORDER BY r.room_name"
        
        cur.execute(query, params)
        rooms = cur.fetchall()
        
        # Get equipment for each room
        result = []
        for room in rooms:
            cur.execute("""
                SELECT e.equipment_name, re.quantity
                FROM room_equipment re
                JOIN equipment e ON re.equipment_id = e.equipment_id
                WHERE re.room_id = %s
            """, (room['room_id'],))
            
            equipment = cur.fetchall()
            
            room_dict = dict(room)
            room_dict['equipment'] = [
                {'name': eq['equipment_name'], 'quantity': eq['quantity']} 
                for eq in equipment
            ]
            result.append(room_dict)
        
        cur.close()
        conn.close()
        
        return jsonify({'rooms': result}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id):
    """
    Get specific room by ID.
    
    Args:
        room_id (int): Room ID
        
    Returns:
        JSON: Room details
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT room_id, room_name, capacity, location, status
            FROM rooms WHERE room_id = %s
        """, (room_id,))
        
        room = cur.fetchone()
        
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        
        # Get equipment
        cur.execute("""
            SELECT e.equipment_name, re.quantity
            FROM room_equipment re
            JOIN equipment e ON re.equipment_id = e.equipment_id
            WHERE re.room_id = %s
        """, (room_id,))
        
        equipment = cur.fetchall()
        
        cur.close()
        conn.close()
        
        room_dict = dict(room)
        room_dict['equipment'] = [
            {'name': eq['equipment_name'], 'quantity': eq['quantity']} 
            for eq in equipment
        ]
        
        return jsonify({'room': room_dict}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rooms', methods=['POST'])
@admin_or_facility_required
def add_room(current_user):
    """
    Add a new meeting room.
    
    Request Body:
        room_name (str): Room name
        capacity (int): Room capacity
        location (str): Room location
        equipment (list, optional): List of equipment with name and quantity
        
    Headers:
        Authorization: Bearer <token>
        
    Returns:
        JSON: Created room data
    """
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['room_name', 'capacity', 'location']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    room_name = sanitize_input(data['room_name'])
    capacity = int(data['capacity'])
    location = sanitize_input(data['location'])
    equipment = data.get('equipment', [])
    
    if capacity <= 0:
        return jsonify({'error': 'Capacity must be positive'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if room name exists
        cur.execute("SELECT room_id FROM rooms WHERE room_name = %s", (room_name,))
        if cur.fetchone():
            return jsonify({'error': 'Room name already exists'}), 409
        
        # Insert room
        cur.execute("""
            INSERT INTO rooms (room_name, capacity, location, status)
            VALUES (%s, %s, %s, 'available')
            RETURNING room_id, room_name, capacity, location, status
        """, (room_name, capacity, location))
        
        room = cur.fetchone()
        room_id = room['room_id']
        
        # Add equipment if provided
        equipment_list = []
        for eq in equipment:
            eq_name = sanitize_input(eq.get('name'))
            eq_quantity = int(eq.get('quantity', 1))
            
            # Get or create equipment
            cur.execute("""
                INSERT INTO equipment (equipment_name)
                VALUES (%s)
                ON CONFLICT DO NOTHING
                RETURNING equipment_id
            """, (eq_name,))
            
            result = cur.fetchone()
            if result:
                equipment_id = result['equipment_id']
            else:
                cur.execute("SELECT equipment_id FROM equipment WHERE equipment_name = %s", (eq_name,))
                equipment_id = cur.fetchone()['equipment_id']
            
            # Link equipment to room
            cur.execute("""
                INSERT INTO room_equipment (room_id, equipment_id, quantity)
                VALUES (%s, %s, %s)
            """, (room_id, equipment_id, eq_quantity))
            
            equipment_list.append({'name': eq_name, 'quantity': eq_quantity})
        
        conn.commit()
        cur.close()
        conn.close()
        
        room_dict = dict(room)
        room_dict['equipment'] = equipment_list
        
        return jsonify({
            'message': 'Room created successfully',
            'room': room_dict
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rooms/<int:room_id>', methods=['PUT'])
@admin_or_facility_required
def update_room(current_user, room_id):
    """
    Update room details.
    
    Args:
        room_id (int): Room ID
        
    Request Body:
        room_name (str, optional): New room name
        capacity (int, optional): New capacity
        location (str, optional): New location
        status (str, optional): New status
        equipment (list, optional): New equipment list
        
    Headers:
        Authorization: Bearer <token>
        
    Returns:
        JSON: Updated room data
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if room exists
        cur.execute("SELECT room_id FROM rooms WHERE room_id = %s", (room_id,))
        if not cur.fetchone():
            return jsonify({'error': 'Room not found'}), 404
        
        update_fields = []
        params = []
        
        if 'room_name' in data:
            update_fields.append("room_name = %s")
            params.append(sanitize_input(data['room_name']))
        
        if 'capacity' in data:
            capacity = int(data['capacity'])
            if capacity <= 0:
                return jsonify({'error': 'Capacity must be positive'}), 400
            update_fields.append("capacity = %s")
            params.append(capacity)
        
        if 'location' in data:
            update_fields.append("location = %s")
            params.append(sanitize_input(data['location']))
        
        if 'status' in data:
            status = sanitize_input(data['status'])
            if status not in ['available', 'unavailable', 'maintenance']:
                return jsonify({'error': 'Invalid status'}), 400
            update_fields.append("status = %s")
            params.append(status)
        
        if update_fields:
            params.append(room_id)
            query = f"UPDATE rooms SET {', '.join(update_fields)} WHERE room_id = %s"
            cur.execute(query, params)
        
        # Update equipment if provided
        if 'equipment' in data:
            # Remove existing equipment
            cur.execute("DELETE FROM room_equipment WHERE room_id = %s", (room_id,))
            
            # Add new equipment
            for eq in data['equipment']:
                eq_name = sanitize_input(eq.get('name'))
                eq_quantity = int(eq.get('quantity', 1))
                
                cur.execute("""
                    INSERT INTO equipment (equipment_name)
                    VALUES (%s)
                    ON CONFLICT DO NOTHING
                    RETURNING equipment_id
                """, (eq_name,))
                
                result = cur.fetchone()
                if result:
                    equipment_id = result['equipment_id']
                else:
                    cur.execute("SELECT equipment_id FROM equipment WHERE equipment_name = %s", (eq_name,))
                    equipment_id = cur.fetchone()['equipment_id']
                
                cur.execute("""
                    INSERT INTO room_equipment (room_id, equipment_id, quantity)
                    VALUES (%s, %s, %s)
                """, (room_id, equipment_id, eq_quantity))
        
        # Get updated room
        cur.execute("""
            SELECT room_id, room_name, capacity, location, status
            FROM rooms WHERE room_id = %s
        """, (room_id,))
        
        room = cur.fetchone()
        
        # Get equipment
        cur.execute("""
            SELECT e.equipment_name, re.quantity
            FROM room_equipment re
            JOIN equipment e ON re.equipment_id = e.equipment_id
            WHERE re.room_id = %s
        """, (room_id,))
        
        equipment = cur.fetchall()
        
        conn.commit()
        cur.close()
        conn.close()
        
        room_dict = dict(room)
        room_dict['equipment'] = [
            {'name': eq['equipment_name'], 'quantity': eq['quantity']} 
            for eq in equipment
        ]
        
        return jsonify({
            'message': 'Room updated successfully',
            'room': room_dict
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rooms/<int:room_id>', methods=['DELETE'])
@admin_or_facility_required
def delete_room(current_user, room_id):
    """
    Delete a room.
    
    Args:
        room_id (int): Room ID
        
    Headers:
        Authorization: Bearer <token>
        
    Returns:
        JSON: Success message
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check for active bookings
        cur.execute("""
            SELECT COUNT(*) as count FROM bookings 
            WHERE room_id = %s AND booking_date >= CURRENT_DATE AND status = 'confirmed'
        """, (room_id,))
        
        result = cur.fetchone()
        if result['count'] > 0:
            return jsonify({'error': 'Cannot delete room with active bookings'}), 400
        
        cur.execute("DELETE FROM rooms WHERE room_id = %s RETURNING room_id", (room_id,))
        deleted = cur.fetchone()
        
        if not deleted:
            return jsonify({'error': 'Room not found'}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Room deleted successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rooms/available', methods=['GET'])
def check_availability():
    """
    Check room availability for a specific date and time.
    
    Query Parameters:
        date (str): Booking date (YYYY-MM-DD)
        start_time (str): Start time (HH:MM)
        end_time (str): End time (HH:MM)
        capacity (int, optional): Minimum capacity
        
    Returns:
        JSON: List of available rooms
    """
    required_params = ['date', 'start_time', 'end_time']
    for param in required_params:
        if param not in request.args:
            return jsonify({'error': f'{param} is required'}), 400
    
    date = request.args['date']
    start_time = request.args['start_time']
    end_time = request.args['end_time']
    capacity = request.args.get('capacity', 0)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT r.room_id, r.room_name, r.capacity, r.location
            FROM rooms r
            WHERE r.status = 'available'
            AND r.capacity >= %s
            AND r.room_id NOT IN (
                SELECT room_id FROM bookings
                WHERE booking_date = %s
                AND status = 'confirmed'
                AND (
                    (start_time <= %s AND end_time > %s)
                    OR (start_time < %s AND end_time >= %s)
                    OR (start_time >= %s AND end_time <= %s)
                )
            )
            ORDER BY r.capacity, r.room_name
        """
        
        cur.execute(query, (capacity, date, start_time, start_time, end_time, end_time, start_time, end_time))
        rooms = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({'available_rooms': [dict(room) for room in rooms]}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/equipment', methods=['GET'])
def get_equipment():
    """
    Get all available equipment.
    
    Returns:
        JSON: List of all equipment
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT equipment_id, equipment_name FROM equipment ORDER BY equipment_name")
        equipment = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({'equipment': [dict(eq) for eq in equipment]}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('SERVICE_PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)
