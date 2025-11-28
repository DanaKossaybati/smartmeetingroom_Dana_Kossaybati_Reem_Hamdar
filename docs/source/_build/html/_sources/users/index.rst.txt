Users Service
==============

Overview
--------

The Users Service handles authentication, user management, and role-based access control (RBAC). It provides user registration, login, profile management, and token-based authentication for the Smart Meeting Room system.

Key Features:

- User registration and authentication
- JWT token generation and validation
- Profile management
- Role-based access control (RBAC)
- Password security (bcrypt hashing)
- Email validation

Service Details
---------------

- **Port**: 8001
- **Author**: Dana Kossaybati
- **Version**: 1.0.0
- **API Documentation**: http://localhost:8001/docs

Modules
-------

.. toctree::
   :maxdepth: 2

   main
   models
   schemas
   services
   auth
   routes
   database
   errors
   utils

Database Models
---------------

.. automodule:: users.models
   :members:
   :undoc-members:
   :show-inheritance:

Request/Response Schemas
------------------------

.. automodule:: users.schemas
   :members:
   :undoc-members:
   :show-inheritance:

Core Services
-------------

.. automodule:: users.services
   :members:
   :undoc-members:
   :show-inheritance:

Authentication
--------------

.. automodule:: users.auth
   :members:
   :undoc-members:
   :show-inheritance:

Database
--------

.. automodule:: users.database
   :members:
   :undoc-members:
   :show-inheritance:

Error Handling
--------------

.. automodule:: users.errors
   :members:
   :undoc-members:
   :show-inheritance:

Utilities
---------

.. automodule:: users.utils
   :members:
   :undoc-members:
   :show-inheritance:

API Routes
----------

.. automodule:: users.routes
   :members:
   :undoc-members:
   :show-inheritance:

API Endpoints
~~~~~~~~~~~~~

Authentication Endpoints:

- ``POST /api/auth/register`` - Register a new user
- ``POST /api/auth/login`` - User login
- ``POST /api/auth/refresh`` - Refresh JWT token

Profile Endpoints:

- ``GET /api/users/{user_id}`` - Get user profile
- ``PUT /api/users/{user_id}`` - Update user profile
- ``DELETE /api/users/{user_id}`` - Delete user account

Admin Endpoints:

- ``GET /api/users`` - List all users (admin only)
- ``PUT /api/users/{user_id}/role`` - Update user role (admin only)

Health Check:

- ``GET /`` - Service status
- ``GET /health`` - Health check endpoint
