"""
Reviews Service - Smart Meeting Room Management System
Handles room reviews, ratings, and moderation.
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
ROOMS_SERVICE_URL = os.getenv('ROOMS_SERVICE_URL', 'http://localhost:5002')


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
    # Allow basic formatting but remove scripts and dangerous tags
    allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']
    return bleach.clean(str(text), tags=allowed_tags, strip=True)


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


def moderator_required(f):
    """
    Decorator to require moderator or admin role.
    
    Args:
        f: Function to wrap
        
    Returns:
        function: Wrapped function
    """
    @wraps(f)
    @token_required
    def decorated(current_user, *args, **kwargs):
        if current_user['role'] not in ['admin', 'moderator']:
            return jsonify({'error': 'Moderator access required'}), 403
        return f(current_user, *args, **kwargs)
    
    return decorated


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        JSON: Service status
    """
    return jsonify({'status': 'healthy', 'service': 'reviews'}), 200


@app.route('/api/reviews', methods=['GET'])
def get_all_reviews():
    """
    Get all reviews with optional filters.
    
    Query Parameters:
        room_id (int, optional): Filter by room
        user_id (int, optional): Filter by user
        min_rating (int, optional): Minimum rating filter
        flagged (bool, optional): Show only flagged reviews (moderators only)
        
    Returns:
        JSON: List of reviews
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT r.review_id, r.rating, r.comment, r.created_at, r.is_flagged,
                   u.username, u.full_name,
                   rm.room_id, rm.room_name, rm.location
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            JOIN rooms rm ON r.room_id = rm.room_id
            WHERE 1=1
        """
        params = []
        
        # Apply filters
        if 'room_id' in request.args:
            query += " AND rm.room_id = %s"
            params.append(int(request.args['room_id']))
        
        if 'user_id' in request.args:
            query += " AND u.user_id = %s"
            params.append(int(request.args['user_id']))
        
        if 'min_rating' in request.args:
            query += " AND r.rating >= %s"
            params.append(int(request.args['min_rating']))
        
        if 'flagged' in request.args and request.args['flagged'].lower() == 'true':
            query += " AND r.is_flagged = true"
        
        query += " ORDER BY r.created_at DESC"
        
        cur.execute(query, params)
        reviews = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({'reviews': [dict(review) for review in reviews]}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reviews/room/<int:room_id>', methods=['GET'])
def get_room_reviews(room_id):
    """
    Get all reviews for a specific room.
    
    Args:
        room_id (int): Room ID
        
    Returns:
        JSON: List of reviews and average rating
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get reviews
        cur.execute("""
            SELECT r.review_id, r.rating, r.comment, r.created_at, r.is_flagged,
                   u.username, u.full_name
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.room_id = %s
            ORDER BY r.created_at DESC
        """, (room_id,))
        
        reviews = cur.fetchall()
        
        # Calculate average rating
        cur.execute("""
            SELECT AVG(rating)::DECIMAL(3,2) as avg_rating, COUNT(*) as review_count
            FROM reviews
            WHERE room_id = %s
        """, (room_id,))
        
        stats = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'reviews': [dict(review) for review in reviews],
            'average_rating': float(stats['avg_rating']) if stats['avg_rating'] else 0,
            'review_count': stats['review_count']
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reviews/<int:review_id>', methods=['GET'])
def get_review(review_id):
    """
    Get specific review by ID.
    
    Args:
        review_id (int): Review ID
        
    Returns:
        JSON: Review details
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT r.review_id, r.rating, r.comment, r.created_at, r.is_flagged,
                   u.user_id, u.username, u.full_name,
                   rm.room_id, rm.room_name, rm.location
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            JOIN rooms rm ON r.room_id = rm.room_id
            WHERE r.review_id = %s
        """, (review_id,))
        
        review = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not review:
            return jsonify({'error': 'Review not found'}), 404
        
        return jsonify({'review': dict(review)}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reviews', methods=['POST'])
@token_required
def create_review(current_user):
    """
    Submit a new review for a room.
    
    Request Body:
        room_id (int): Room ID
        rating (int): Rating (1-5)
        comment (str): Review comment
        
    Headers:
        Authorization: Bearer <token>
        
    Returns:
        JSON: Created review data
    """
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['room_id', 'rating', 'comment']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    room_id = int(data['room_id'])
    rating = int(data['rating'])
    comment = sanitize_input(data['comment'])
    
    # Validate rating
    if rating < 1 or rating > 5:
        return jsonify({'error': 'Rating must be between 1 and 5'}), 400
    
    # Validate comment length
    if len(comment.strip()) < 10:
        return jsonify({'error': 'Comment must be at least 10 characters'}), 400
    
    if len(comment) > 1000:
        return jsonify({'error': 'Comment must not exceed 1000 characters'}), 400
    
    # Check for inappropriate content (basic profanity filter)
    inappropriate_words = ['spam', 'xxx', 'hate']  # This should be more comprehensive
    comment_lower = comment.lower()
    for word in inappropriate_words:
        if word in comment_lower:
            return jsonify({'error': 'Comment contains inappropriate content'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verify room exists
        cur.execute("SELECT room_id FROM rooms WHERE room_id = %s", (room_id,))
        if not cur.fetchone():
            return jsonify({'error': 'Room not found'}), 404
        
        # Get user_id
        cur.execute("SELECT user_id FROM users WHERE username = %s", (current_user['username'],))
        user = cur.fetchone()
        user_id = user['user_id']
        
        # Check if user has already reviewed this room
        cur.execute("""
            SELECT review_id FROM reviews 
            WHERE user_id = %s AND room_id = %s
        """, (user_id, room_id))
        
        existing = cur.fetchone()
        if existing:
            return jsonify({'error': 'You have already reviewed this room. Use PUT to update.'}), 409
        
        # Create review
        cur.execute("""
            INSERT INTO reviews (user_id, room_id, rating, comment)
            VALUES (%s, %s, %s, %s)
            RETURNING review_id, rating, comment, created_at
        """, (user_id, room_id, rating, comment))
        
        review = cur.fetchone()
        
        conn.commit()
        cur.close()
        conn.close()
        
        review_dict = dict(review)
        review_dict['username'] = current_user['username']
        
        return jsonify({
            'message': 'Review submitted successfully',
            'review': review_dict
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reviews/<int:review_id>', methods=['PUT'])
@token_required
def update_review(current_user, review_id):
    """
    Update an existing review.
    
    Args:
        review_id (int): Review ID
        
    Request Body:
        rating (int, optional): New rating
        comment (str, optional): New comment
        
    Headers:
        Authorization: Bearer <token>
        
    Returns:
        JSON: Updated review data
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get existing review
        cur.execute("""
            SELECT r.*, u.username
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.review_id = %s
        """, (review_id,))
        
        existing_review = cur.fetchone()
        
        if not existing_review:
            return jsonify({'error': 'Review not found'}), 404
        
        # Check permission (owner or moderator/admin)
        if current_user['role'] not in ['admin', 'moderator'] and existing_review['username'] != current_user['username']:
            return jsonify({'error': 'Access denied'}), 403
        
        update_fields = []
        params = []
        
        if 'rating' in data:
            rating = int(data['rating'])
            if rating < 1 or rating > 5:
                return jsonify({'error': 'Rating must be between 1 and 5'}), 400
            update_fields.append("rating = %s")
            params.append(rating)
        
        if 'comment' in data:
            comment = sanitize_input(data['comment'])
            if len(comment.strip()) < 10:
                return jsonify({'error': 'Comment must be at least 10 characters'}), 400
            if len(comment) > 1000:
                return jsonify({'error': 'Comment must not exceed 1000 characters'}), 400
            update_fields.append("comment = %s")
            params.append(comment)
        
        if not update_fields:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        params.append(review_id)
        query = f"UPDATE reviews SET {', '.join(update_fields)} WHERE review_id = %s"
        cur.execute(query, params)
        
        # Get updated review
        cur.execute("""
            SELECT r.review_id, r.rating, r.comment, r.created_at, r.is_flagged,
                   u.username, u.full_name,
                   rm.room_name
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            JOIN rooms rm ON r.room_id = rm.room_id
            WHERE r.review_id = %s
        """, (review_id,))
        
        updated_review = cur.fetchone()
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'message': 'Review updated successfully',
            'review': dict(updated_review)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reviews/<int:review_id>', methods=['DELETE'])
@token_required
def delete_review(current_user, review_id):
    """
    Delete a review.
    
    Args:
        review_id (int): Review ID
        
    Headers:
        Authorization: Bearer <token>
        
    Returns:
        JSON: Success message
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get review
        cur.execute("""
            SELECT r.*, u.username
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.review_id = %s
        """, (review_id,))
        
        review = cur.fetchone()
        
        if not review:
            return jsonify({'error': 'Review not found'}), 404
        
        # Check permission (owner or moderator/admin)
        if current_user['role'] not in ['admin', 'moderator'] and review['username'] != current_user['username']:
            return jsonify({'error': 'Access denied'}), 403
        
        cur.execute("DELETE FROM reviews WHERE review_id = %s", (review_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Review deleted successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reviews/<int:review_id>/flag', methods=['POST'])
@token_required
def flag_review(current_user, review_id):
    """
    Flag a review as inappropriate.
    
    Args:
        review_id (int): Review ID
        
    Headers:
        Authorization: Bearer <token>
        
    Returns:
        JSON: Success message
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT review_id, is_flagged FROM reviews WHERE review_id = %s", (review_id,))
        review = cur.fetchone()
        
        if not review:
            return jsonify({'error': 'Review not found'}), 404
        
        if review['is_flagged']:
            return jsonify({'message': 'Review is already flagged'}), 200
        
        cur.execute("UPDATE reviews SET is_flagged = true WHERE review_id = %s", (review_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Review flagged for moderation'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reviews/<int:review_id>/unflag', methods=['POST'])
@moderator_required
def unflag_review(current_user, review_id):
    """
    Remove flag from a review (Moderators only).
    
    Args:
        review_id (int): Review ID
        
    Headers:
        Authorization: Bearer <token>
        
    Returns:
        JSON: Success message
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT review_id FROM reviews WHERE review_id = %s", (review_id,))
        if not cur.fetchone():
            return jsonify({'error': 'Review not found'}), 404
        
        cur.execute("UPDATE reviews SET is_flagged = false WHERE review_id = %s", (review_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Review unflagged successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reviews/flagged', methods=['GET'])
@moderator_required
def get_flagged_reviews(current_user):
    """
    Get all flagged reviews (Moderators only).
    
    Headers:
        Authorization: Bearer <token>
        
    Returns:
        JSON: List of flagged reviews
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT r.review_id, r.rating, r.comment, r.created_at,
                   u.username, u.full_name,
                   rm.room_id, rm.room_name
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            JOIN rooms rm ON r.room_id = rm.room_id
            WHERE r.is_flagged = true
            ORDER BY r.created_at DESC
        """)
        
        reviews = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'flagged_reviews': [dict(review) for review in reviews],
            'count': len(reviews)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('SERVICE_PORT', 5004))
    app.run(host='0.0.0.0', port=port, debug=True)
