Smart Meeting Room - API Documentation
=========================================

Welcome to the Smart Meeting Room microservices API documentation. This documentation covers the **Users** and **Bookings** services.

.. toctree::
   :maxdepth: 2
   :caption: Services

   users/index
   bookings/index

Overview
========

Smart Meeting Room Management System is a microservices architecture designed to manage:

- **Users Service**: Authentication, user management, and role-based access control
- **Bookings Service**: Room reservations, availability management, and booking analytics

Architecture
============

The system follows a microservices pattern with:

- **Independent Services**: Each service runs in its own container with its own database
- **REST APIs**: Services communicate via HTTP REST APIs
- **JWT Authentication**: Secure token-based authentication
- **PostgreSQL**: Persistent data storage
- **Docker Compose**: Orchestration and deployment

Quick Start
===========

For API Swagger documentation, visit:

- Users Service: http://localhost:8001/docs
- Bookings Service: http://localhost:8003/docs

Service Ports
=============

- Users Service: 8001
- Bookings Service: 8003
- Database (PostgreSQL): 5432

.. note::
   Each service provides OpenAPI/Swagger documentation at its `/docs` endpoint.

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
