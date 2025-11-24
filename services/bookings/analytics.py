"""
Analytics and Insights API for Bookings Service
Provides data aggregation and analysis endpoints for monitoring service performance.

Author: Dana Kossaybati
Part II Enhancement: Analytics and Insights
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy import func, extract, and_, or_
from datetime import datetime, timedelta, date
from typing import Optional
import json


from auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["Analytics & Insights"])


# ============================================
# BOOKING ANALYTICS ENDPOINTS
# ============================================

@router.get("/bookings/summary")
async def booking_summary(current_user: dict = Depends(get_current_user)):
    """
    Get comprehensive booking statistics summary.
    
    Returns:
        - Total bookings count
        - Bookings by status (confirmed, cancelled, etc.)
        - Bookings this month
        - Top 5 most active users
        - Average bookings per user
    
    Access: All authenticated users (admins see all, users see own stats)
    """
    from database import SessionLocal
    from models import Booking
    
    db = SessionLocal()
    
    try:
        # Check if user is admin - admins see all data, users see only their data
        is_admin = current_user.get('role') == 'admin'
        user_id = current_user.get('user_id')
        
        # Base query - filter by user if not admin
        base_query = db.query(Booking)
        if not is_admin:
            base_query = base_query.filter(Booking.user_id == user_id)
        
        # Total bookings
        total_bookings = base_query.count()
        
        # Bookings by status
        status_breakdown = base_query.with_entities(
            Booking.status,
            func.count(Booking.booking_id).label('count')
        ).group_by(Booking.status).all()
        
        # Bookings this month
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        bookings_this_month = base_query.filter(
            Booking.created_at >= current_month_start
        ).count()
        
        # Bookings last month for comparison
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        bookings_last_month = base_query.filter(
            and_(
                Booking.created_at >= last_month_start,
                Booking.created_at < current_month_start
            )
        ).count()
        
        # Calculate growth rate
        if bookings_last_month > 0:
            growth_rate = ((bookings_this_month - bookings_last_month) / bookings_last_month) * 100
        else:
            growth_rate = 100 if bookings_this_month > 0 else 0
        
        # Top users (admin only)
        top_users = []
        if is_admin:
            from sqlalchemy import text
    
            query = text("""
                SELECT u.username, u.full_name, COUNT(b.booking_id) as booking_count
                FROM users u
                JOIN bookings b ON u.user_id = b.user_id
                GROUP BY u.user_id, u.username, u.full_name
                ORDER BY COUNT(b.booking_id) DESC
                LIMIT 5
            """)
            
            top_users_result = db.execute(query).fetchall()
            top_users = [
                {
                    "username": row[0],
                    "full_name": row[1],
                    "total_bookings": row[2]
                }
                for row in top_users_result
            ]
        
        # Average bookings per user (admin only)
        avg_bookings_per_user = 0
        if is_admin:
            total_users_with_bookings = db.query(func.count(func.distinct(Booking.user_id))).scalar()
            if total_users_with_bookings > 0:
                avg_bookings_per_user = round(total_bookings / total_users_with_bookings, 2)
        
        return {
            "success": True,
            "summary": {
                "total_bookings": total_bookings,
                "bookings_this_month": bookings_this_month,
                "bookings_last_month": bookings_last_month,
                "growth_rate_percent": round(growth_rate, 2),
                "status_breakdown": {status: count for status, count in status_breakdown},
                "average_bookings_per_user": avg_bookings_per_user,
                "top_users": top_users
            },
            "scope": "all_bookings" if is_admin else "my_bookings",
            "generated_at": datetime.utcnow().isoformat()
        }
        
    finally:
        db.close()


@router.get("/bookings/trends")
async def booking_trends(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """
    Get booking trends over last N days.
    Shows daily booking counts to identify patterns.
    
    Args:
        days: Number of days to analyze (default: 30, max: 365)
    
    Returns:
        Daily booking counts with trend analysis
    """
    from database import SessionLocal
    from models import Booking
    
    # Validate input
    if days < 1 or days > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days parameter must be between 1 and 365"
        )
    
    db = SessionLocal()
    
    try:
        is_admin = current_user.get('role') == 'admin'
        user_id = current_user.get('user_id')
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Base query
        base_query = db.query(
            func.date(Booking.created_at).label('date'),
            func.count(Booking.booking_id).label('count')
        ).filter(Booking.created_at >= start_date)
        
        # Filter by user if not admin
        if not is_admin:
            base_query = base_query.filter(Booking.user_id == user_id)
        
        daily_bookings = base_query.group_by(
            func.date(Booking.created_at)
        ).order_by('date').all()
        
        # Calculate trend statistics
        booking_counts = [count for _, count in daily_bookings]
        
        if booking_counts:
            avg_per_day = sum(booking_counts) / len(booking_counts)
            max_day = max(booking_counts)
            min_day = min(booking_counts)
            total = sum(booking_counts)
        else:
            avg_per_day = max_day = min_day = total = 0
        
        return {
            "success": True,
            "period": f"last_{days}_days",
            "statistics": {
                "total_bookings": total,
                "average_per_day": round(avg_per_day, 2),
                "busiest_day_count": max_day,
                "slowest_day_count": min_day
            },
            "trends": [
                {
                    "date": str(booking_date),
                    "bookings": count,
                    "day_of_week": booking_date.strftime('%A')
                }
                for booking_date, count in daily_bookings
            ],
            "scope": "all_bookings" if is_admin else "my_bookings"
        }
        
    finally:
        db.close()


@router.get("/bookings/peak-hours")
async def peak_hours(current_user: dict = Depends(get_current_user)):
    """
    Analyze peak booking hours.
    Shows which hours are most popular for meeting room bookings.
    
    Returns:
        Hourly distribution of bookings with popularity ratings
    """
    from database import SessionLocal
    from models import Booking
    
    db = SessionLocal()
    
    try:
        is_admin = current_user.get('role') == 'admin'
        user_id = current_user.get('user_id')
        
        # Base query - extract hour from start_time
        base_query = db.query(
            extract('hour', Booking.start_time).label('hour'),
            func.count(Booking.booking_id).label('count')
        )
        
        # Filter by user if not admin
        if not is_admin:
            base_query = base_query.filter(Booking.user_id == user_id)
        
        hourly_distribution = base_query.group_by('hour').order_by('hour').all()
        
        # Calculate statistics
        if hourly_distribution:
            counts = [count for _, count in hourly_distribution]
            total = sum(counts)
            avg = total / 24  # Average across all possible hours
            max_count = max(counts)
        else:
            total = avg = max_count = 0
        
        # Categorize popularity
        def get_popularity(count):
            if count >= avg * 1.5:
                return "high"
            elif count >= avg * 0.5:
                return "medium"
            else:
                return "low"
        
        return {
            "success": True,
            "peak_hours_analysis": [
                {
                    "hour": f"{int(hour):02d}:00",
                    "hour_24": int(hour),
                    "booking_count": count,
                    "percentage_of_total": round((count / total * 100) if total > 0 else 0, 2),
                    "popularity": get_popularity(count)
                }
                for hour, count in hourly_distribution
            ],
            "statistics": {
                "total_bookings_analyzed": total,
                "busiest_hour": f"{int(hourly_distribution[counts.index(max_count)][0]):02d}:00" if counts else "N/A",
                "busiest_hour_count": max_count
            },
            "scope": "all_bookings" if is_admin else "my_bookings"
        }
        
    finally:
        db.close()


@router.get("/bookings/day-of-week")
async def day_of_week_analysis(current_user: dict = Depends(get_current_user)):
    """
    Analyze booking patterns by day of week.
    Identifies which days are most popular for bookings.
    
    Returns:
        Breakdown by day of week (Monday-Sunday)
    """
    from database import SessionLocal
    from models import Booking
    
    db = SessionLocal()
    
    try:
        is_admin = current_user.get('role') == 'admin'
        user_id = current_user.get('user_id')
        
        # Base query - extract day of week from booking_date
        base_query = db.query(
            extract('dow', Booking.booking_date).label('day_of_week'),
            func.count(Booking.booking_id).label('count')
        )
        
        # Filter by user if not admin
        if not is_admin:
            base_query = base_query.filter(Booking.user_id == user_id)
        
        dow_distribution = base_query.group_by('day_of_week').order_by('day_of_week').all()
        
        # Map PostgreSQL day of week (0=Sunday) to day names
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        
        total = sum(count for _, count in dow_distribution)
        
        return {
            "success": True,
            "day_of_week_analysis": [
                {
                    "day_number": int(dow),
                    "day_name": day_names[int(dow)],
                    "booking_count": count,
                    "percentage": round((count / total * 100) if total > 0 else 0, 2)
                }
                for dow, count in dow_distribution
            ],
            "total_bookings": total,
            "scope": "all_bookings" if is_admin else "my_bookings"
        }
        
    finally:
        db.close()


@router.get("/bookings/cancellation-rate")
async def cancellation_rate(current_user: dict = Depends(get_current_user)):
    """
    Calculate booking cancellation rate and analyze cancellation patterns.
    
    Returns:
        - Overall cancellation rate
        - Cancellations by time period
        - Cancellation trend
    """
    from database import SessionLocal
    from models import Booking, BookingHistory
    
    db = SessionLocal()
    
    try:
        is_admin = current_user.get('role') == 'admin'
        user_id = current_user.get('user_id')
        
        # Base queries
        base_query = db.query(Booking)
        if not is_admin:
            base_query = base_query.filter(Booking.user_id == user_id)
        
        total_bookings = base_query.count()
        cancelled_bookings = base_query.filter(Booking.status == 'cancelled').count()
        
        rate = (cancelled_bookings / total_bookings * 100) if total_bookings > 0 else 0
        
        # Cancellation history by month (last 6 months)
        six_months_ago = datetime.now() - timedelta(days=180)
        
        history_query = db.query(
            func.date_trunc('month', BookingHistory.timestamp).label('month'),
            func.count(BookingHistory.history_id).label('count')
        ).filter(
            and_(
                BookingHistory.action == 'cancelled',
                BookingHistory.timestamp >= six_months_ago
            )
        )
        
        if not is_admin:
            history_query = history_query.filter(BookingHistory.user_id == user_id)
        
        monthly_cancellations = history_query.group_by('month').order_by('month').all()
        
        # Determine status
        def get_status(rate):
            if rate > 25:
                return "critical"
            elif rate > 15:
                return "high"
            elif rate > 10:
                return "moderate"
            else:
                return "healthy"
        
        return {
            "success": True,
            "cancellation_analysis": {
                "total_bookings": total_bookings,
                "cancelled_bookings": cancelled_bookings,
                "active_bookings": total_bookings - cancelled_bookings,
                "cancellation_rate_percent": round(rate, 2),
                "status": get_status(rate),
                "status_description": {
                    "critical": "Cancellation rate is very high (>25%)",
                    "high": "Cancellation rate is concerning (15-25%)",
                    "moderate": "Cancellation rate is acceptable (10-15%)",
                    "healthy": "Cancellation rate is healthy (<10%)"
                }.get(get_status(rate))
            },
            "monthly_trend": [
                {
                    "month": month.strftime('%Y-%m'),
                    "cancellations": count
                }
                for month, count in monthly_cancellations
            ],
            "scope": "all_bookings" if is_admin else "my_bookings"
        }
        
    finally:
        db.close()


# ============================================
# USER ANALYTICS ENDPOINTS
# ============================================

@router.get("/users/activity")
async def user_activity(current_user: dict = Depends(get_current_user)):
    """
    User activity statistics.
    Shows user engagement metrics.
    
    Access: Admin only
    
    Returns:
        - Total users
        - Active users (with bookings)
        - Inactive users
        - New registrations
        - Role distribution
    """
    from database import SessionLocal
    from models import User, Booking
    
    # Check admin permission
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access user activity analytics"
        )
    
    db = SessionLocal()
    
    try:
        # Total users
        total_users = db.query(func.count(User.user_id)).scalar()
        
        # Active users (made at least 1 booking)
        active_users = db.query(func.count(func.distinct(Booking.user_id))).scalar()
        
        # Users by role
        role_distribution = db.query(
            User.role,
            func.count(User.user_id).label('count')
        ).group_by(User.role).all()
        
        # Registration trend (last 30 days, 90 days, all time)
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        ninety_days_ago = now - timedelta(days=90)
        
        new_users_30d = db.query(func.count(User.user_id)).filter(
            User.created_at >= thirty_days_ago
        ).scalar()
        
        new_users_90d = db.query(func.count(User.user_id)).filter(
            User.created_at >= ninety_days_ago
        ).scalar()
        
        # Active vs inactive
        inactive_users = total_users - active_users
        engagement_rate = (active_users / total_users * 100) if total_users > 0 else 0
        
        return {
            "success": True,
            "user_statistics": {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": inactive_users,
                "engagement_rate_percent": round(engagement_rate, 2),
                "new_users_last_30_days": new_users_30d,
                "new_users_last_90_days": new_users_90d,
                "role_distribution": {role: count for role, count in role_distribution}
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    finally:
        db.close()


# ============================================
# DASHBOARD ENDPOINT
# ============================================

@router.get("/dashboard", response_class=HTMLResponse)
async def analytics_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Interactive HTML dashboard showing all analytics in a visual format.
    Uses Chart.js for visualizations.
    
    Access: All authenticated users (admins see full data, users see personal data)
    """
    is_admin = current_user.get('role') == 'admin'
    username = current_user.get('username', 'User')
    
    # Fetch analytics data
    try:
        summary_data = await booking_summary(current_user)
        trends_data = await booking_trends(days=30, current_user=current_user)
        peak_hours_data = await peak_hours(current_user)
        dow_data = await day_of_week_analysis(current_user)
        cancellation_data = await cancellation_rate(current_user)
        
        summary = summary_data['summary']
        trends = trends_data['trends']
        peak_hours_list = peak_hours_data['peak_hours_analysis']
        dow_list = dow_data['day_of_week_analysis']
        cancellation = cancellation_data['cancellation_analysis']
        
    except Exception as e:
        return f"<html><body><h1>Error loading dashboard</h1><p>{str(e)}</p></body></html>"
    
    # Prepare data for charts
    trends_labels = [t['date'] for t in trends[-14:]]  # Last 14 days
    trends_values = [t['bookings'] for t in trends[-14:]]
    
    peak_labels = [h['hour'] for h in peak_hours_list]
    peak_values = [h['booking_count'] for h in peak_hours_list]
    
    dow_labels = [d['day_name'] for d in dow_list]
    dow_values = [d['booking_count'] for d in dow_list]
    
    status_labels = list(summary['status_breakdown'].keys())
    status_values = list(summary['status_breakdown'].values())
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Analytics Dashboard - Bookings Service</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px;
                min-height: 100vh;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
            }}
            
            .header {{
                background: white;
                padding: 30px;
                border-radius: 15px;
                margin-bottom: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }}
            
            .header h1 {{
                color: #333;
                font-size: 32px;
                margin-bottom: 10px;
            }}
            
            .header p {{
                color: #666;
                font-size: 16px;
            }}
            
            .badge {{
                display: inline-block;
                padding: 5px 15px;
                background: #667eea;
                color: white;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                margin-left: 10px;
            }}
            
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .metric-card {{
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }}
            
            .metric-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0,0,0,0.15);
            }}
            
            .metric-card h3 {{
                color: #666;
                font-size: 14px;
                font-weight: 500;
                margin-bottom: 10px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .metric-card .value {{
                font-size: 36px;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 5px;
            }}
            
            .metric-card .change {{
                font-size: 14px;
                color: #28a745;
            }}
            
            .metric-card .change.negative {{
                color: #dc3545;
            }}
            
            .metric-card .change.neutral {{
                color: #666;
            }}
            
            .charts-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .chart-card {{
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            
            .chart-card h2 {{
                color: #333;
                font-size: 20px;
                margin-bottom: 20px;
                padding-bottom: 15px;
                border-bottom: 2px solid #f0f0f0;
            }}
            
            .chart-container {{
                position: relative;
                height: 300px;
            }}
            
            .status-badge {{
                display: inline-block;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                text-transform: uppercase;
            }}
            
            .status-healthy {{
                background: #d4edda;
                color: #155724;
            }}
            
            .status-moderate {{
                background: #fff3cd;
                color: #856404;
            }}
            
            .status-high {{
                background: #f8d7da;
                color: #721c24;
            }}
            
            .footer {{
                text-align: center;
                color: white;
                margin-top: 30px;
                padding: 20px;
                opacity: 0.9;
            }}
            
            @media (max-width: 768px) {{
                .charts-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .metrics-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Analytics Dashboard</h1>
                <p>By Dana Kossaybati</p>
                <p>Welcome, <strong>{username}</strong> 
                    <span class="badge">{'Administrator' if is_admin else 'User'}</span>
                </p>
                <p style="margin-top: 10px; color: #999; font-size: 14px;">
                    Last updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
                </p>
            </div>
            
            <!-- Key Metrics -->
            <div class="metrics-grid">
                <div class="metric-card">
                    <h3>Total Bookings</h3>
                    <div class="value">{summary['total_bookings']}</div>
                    <div class="change {'positive' if summary['growth_rate_percent'] > 0 else 'negative' if summary['growth_rate_percent'] < 0 else 'neutral'}">
                        {'↑' if summary['growth_rate_percent'] > 0 else '↓' if summary['growth_rate_percent'] < 0 else '→'} 
                        {abs(summary['growth_rate_percent']):.1f}% vs last month
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>This Month</h3>
                    <div class="value">{summary['bookings_this_month']}</div>
                    <div class="change neutral">
                        Last month: {summary['bookings_last_month']}
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>Cancellation Rate</h3>
                    <div class="value">{cancellation['cancellation_rate_percent']:.1f}%</div>
                    <div class="change">
                        <span class="status-badge status-{cancellation['status']}">
                            {cancellation['status']}
                        </span>
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>Active Bookings</h3>
                    <div class="value">{cancellation['active_bookings']}</div>
                    <div class="change neutral">
                        {cancellation['cancelled_bookings']} cancelled
                    </div>
                </div>
            </div>
            
            <!-- Charts -->
            <div class="charts-grid">
                <!-- Booking Trends (Last 14 Days) -->
                <div class="chart-card">
                    <h2>Booking Trends (Last 14 Days)</h2>
                    <div class="chart-container">
                        <canvas id="trendsChart"></canvas>
                    </div>
                </div>
                
                <!-- Peak Hours -->
                <div class="chart-card">
                    <h2>Peak Booking Hours</h2>
                    <div class="chart-container">
                        <canvas id="peakHoursChart"></canvas>
                    </div>
                </div>
                
                <!-- Day of Week -->
                <div class="chart-card">
                    <h2>Bookings by Day of Week</h2>
                    <div class="chart-container">
                        <canvas id="dowChart"></canvas>
                    </div>
                </div>
                
                <!-- Status Breakdown -->
                <div class="chart-card">
                    <h2>Booking Status Distribution</h2>
                    <div class="chart-container">
                        <canvas id="statusChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p>Bookings Service Analytics Dashboard</p>
                <p style="font-size: 12px; margin-top: 5px;">
                    Data scope: {trends_data['scope'].replace('_', ' ').title()}
                </p>
            </div>
        </div>
        
        <script>
            // Chart.js default settings
            Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
            Chart.defaults.color = '#666';
            
            // Trends Chart
            const trendsCtx = document.getElementById('trendsChart').getContext('2d');
            new Chart(trendsCtx, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(trends_labels)},
                    datasets: [{{
                        label: 'Bookings per Day',
                        data: {json.dumps(trends_values)},
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#667eea'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                precision: 0
                            }}
                        }}
                    }}
                }}
            }});
            
            // Peak Hours Chart
            const peakHoursCtx = document.getElementById('peakHoursChart').getContext('2d');
            new Chart(peakHoursCtx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(peak_labels)},
                    datasets: [{{
                        label: 'Bookings',
                        data: {json.dumps(peak_values)},
                        backgroundColor: 'rgba(102, 126, 234, 0.7)',
                        borderColor: '#667eea',
                        borderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                precision: 0
                            }}
                        }}
                    }}
                }}
            }});
            
            // Day of Week Chart
            const dowCtx = document.getElementById('dowChart').getContext('2d');
            new Chart(dowCtx, {{
                type: 'doughnut',
                data: {{
                    labels: {json.dumps(dow_labels)},
                    datasets: [{{
                        data: {json.dumps(dow_values)},
                        backgroundColor: [
                            '#667eea',
                            '#764ba2',
                            '#f093fb',
                            '#4facfe',
                            '#43e97b',
                            '#fa709a',
                            '#fee140'
                        ],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'right'
                        }}
                    }}
                }}
            }});
            
            // Status Chart
            const statusCtx = document.getElementById('statusChart').getContext('2d');
            new Chart(statusCtx, {{
                type: 'pie',
                data: {{
                    labels: {json.dumps(status_labels)},
                    datasets: [{{
                        data: {json.dumps(status_values)},
                        backgroundColor: [
                            '#28a745',
                            '#dc3545',
                            '#ffc107',
                            '#17a2b8'
                        ],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'right'
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    return html_content
