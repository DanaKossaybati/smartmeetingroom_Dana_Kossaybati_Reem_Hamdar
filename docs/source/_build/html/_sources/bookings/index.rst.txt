Bookings Service
================

Overview
--------

The Bookings Service manages room reservations and availability. It handles booking creation, updates, cancellations, and provides analytics on booking patterns for the Smart Meeting Room system.

Key Features:

- Room booking creation and management
- Availability checking and conflict detection
- Booking cancellation and modification
- Booking history and audit trails
- Analytics and reporting
- Status tracking (pending, confirmed, cancelled, completed)

Service Details
---------------

- **Port**: 8003
- **Author**: Dana Kossaybati
- **Version**: 1.0.0
- **API Documentation**: http://localhost:8003/docs

Modules
-------

.. toctree::
   :maxdepth: 2

   main
   models
   schemas
   services
   routes
   database
   analytics

Database Models
---------------

.. automodule:: bookings.models
   :members:
   :undoc-members:
   :show-inheritance:

Request/Response Schemas
------------------------

.. automodule:: bookings.schemas
   :members:
   :undoc-members:
   :show-inheritance:

Core Services
-------------

.. automodule:: bookings.services
   :members:
   :undoc-members:
   :show-inheritance:

Database
--------

.. automodule:: bookings.database
   :members:
   :undoc-members:
   :show-inheritance:

Analytics
---------

.. automodule:: bookings.analytics
   :members:
   :undoc-members:
   :show-inheritance:

API Routes
----------

.. automodule:: bookings.routes
   :members:
   :undoc-members:
   :show-inheritance:

API Endpoints
~~~~~~~~~~~~~

Booking Management:

- ``POST /api/bookings`` - Create a new booking
- ``GET /api/bookings/{booking_id}`` - Get booking details
- ``GET /api/bookings`` - List bookings (with filters)
- ``PUT /api/bookings/{booking_id}`` - Update booking
- ``DELETE /api/bookings/{booking_id}`` - Cancel booking

Availability:

- ``GET /api/rooms/{room_id}/availability`` - Check room availability
- ``GET /api/bookings/room/{room_id}/schedule`` - Get room schedule

Analytics:

- ``GET /api/analytics/bookings/summary`` - Booking statistics
- ``GET /api/analytics/peak-hours`` - Peak usage times
- ``GET /api/analytics/utilization`` - Room utilization rates

Health Check:

- ``GET /`` - Service status
- ``GET /health`` - Health check endpoint
