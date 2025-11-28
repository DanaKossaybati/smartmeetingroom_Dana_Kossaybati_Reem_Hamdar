# Sphinx Documentation

This folder contains automatically generated Sphinx documentation for the Users and Bookings microservices.

## Documentation Structure

```
docs/
├── source/              # Source RST files for documentation
│   ├── conf.py         # Sphinx configuration
│   ├── index.rst       # Main documentation index
│   ├── users/          # Users service documentation
│   │   ├── index.rst
│   │   ├── main.rst
│   │   ├── models.rst
│   │   ├── schemas.rst
│   │   ├── services.rst
│   │   ├── auth.rst
│   │   ├── database.rst
│   │   ├── errors.rst
│   │   ├── routes.rst
│   │   └── utils.rst
│   ├── bookings/       # Bookings service documentation
│   │   ├── index.rst
│   │   ├── main.rst
│   │   ├── models.rst
│   │   ├── schemas.rst
│   │   ├── services.rst
│   │   ├── routes.rst
│   │   ├── database.rst
│   │   └── analytics.rst
│   ├── _static/        # Static assets
│   └── _templates/     # Custom templates
└── source/_build/      # Generated HTML documentation

```

## Building the Documentation

### Prerequisites

Ensure you have Sphinx installed:

```bash
pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints
```

### Install Service Dependencies

To ensure all modules can be imported properly for documentation generation:

```bash
cd services/users && pip install -r requirements.txt
cd services/bookings && pip install -r requirements.txt
```

### Generate HTML Documentation

```bash
cd docs
python -m sphinx -b html source source/_build/html
```

## Viewing the Documentation

After generation, open `source/_build/html/index.html` in your web browser to view the documentation.

Alternatively, if you have a local HTTP server, you can serve the documentation:

```bash
cd docs/source/_build/html
python -m http.server 8000
```

Then visit `http://localhost:8000` in your browser.

## Documentation Contents

### Users Service
- **Overview**: Authentication and user management microservice
- **Features**: User registration, login, profile management, role-based access control
- **API Port**: 8001
- **Modules Documented**:
  - `models.py` - Database models (User model)
  - `schemas.py` - Request/response validation schemas
  - `services.py` - Business logic for user operations
  - `auth.py` - JWT token handling and authentication
  - `routes.py` - API endpoint definitions
  - `database.py` - Database connection and session management
  - `errors.py` - Custom error handling
  - `utils.py` - Utility functions

### Bookings Service
- **Overview**: Room reservation and availability management
- **Features**: Booking creation, conflict detection, history tracking, analytics
- **API Port**: 8003
- **Modules Documented**:
  - `models.py` - Database models (Booking, BookingHistory)
  - `schemas.py` - Request/response validation schemas
  - `services.py` - Business logic for booking operations
  - `routes.py` - API endpoint definitions
  - `database.py` - Database connection and session management
  - `analytics.py` - Analytics and reporting functions

## Documentation Features

The generated documentation includes:

- **Module Index**: Complete listing of all modules and functions
- **Class and Function Documentation**: Extracted from inline docstrings
- **Source Code Links**: Direct links to the source code
- **API Reference**: Detailed API endpoint documentation
- **Type Annotations**: Parameter and return type information
- **Search Functionality**: Full-text search across documentation

## Module Documentation Extraction

Documentation is automatically extracted from:

- **Docstrings**: Detailed descriptions in Python docstrings
- **Type Hints**: Parameter types and return types
- **Field Descriptions**: Pydantic model field descriptions
- **Comments**: Inline code comments and documentation

## Sphinx Configuration

The `conf.py` file includes:

- **autodoc extension**: Automatic documentation from Python docstrings
- **napoleon extension**: Support for Google/NumPy docstring formats
- **viewcode extension**: Links to source code
- **ReadTheDocs theme**: Professional documentation theme
- **HTML theme options**: Customized navigation and layout

## Warnings and Notes

During documentation generation, warnings may appear for:

1. **Import Errors**: These are expected if service dependencies aren't fully installed
2. **Indentation Errors**: Minor formatting issues in docstrings
3. **Duplicate Descriptions**: When modules are documented in multiple places

These warnings don't prevent the documentation from being generated and don't affect the documentation quality.

## Rebuilding After Changes

When you modify the service code:

1. Update docstrings with new information
2. Run the build command again:

```bash
cd docs
python -m sphinx -b html source source/_build/html
```

The documentation will be regenerated automatically.

## API Endpoint Documentation

For interactive API documentation (Swagger UI and ReDoc), visit:

- **Users Service**: http://localhost:8001/docs
- **Bookings Service**: http://localhost:8003/docs

These provide interactive API exploration and testing capabilities alongside the Sphinx documentation.
