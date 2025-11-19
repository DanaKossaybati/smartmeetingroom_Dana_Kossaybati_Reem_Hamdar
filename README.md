# Smart Meeting Room Management System

**Course:** EECE435L – Software Tools Lab (Fall 2025–2026)  
**Project Type:** Backend Microservices (Dockerized)  

**Team Members:**  
- Dana Kossaybati – dak39@mail.aub.edu
- Reem Hamdar – rsh44@mail.aub.edu
---

## Project Overview
The Smart Meeting Room Management System is a backend solution built using FastAPI microservices.  
It provides functionality for user management, room reservations, and review moderation through RESTful APIs.  
Each service runs independently in a Docker container and communicates with others through HTTP requests.

The system is designed to be modular, scalable, and secure, focusing on authentication, validation, and performance.

---

## Core Services
| Service | Description | Example Port |
|----------|--------------|--------------|
| **Users Service** | Handles registration, login, and authentication | 8001 |
| **Rooms Service** | Manages room details, capacity, and equipment | 8002 |
| **Bookings Service** | Handles room reservations and booking history | 8003 |
| **Reviews Service** | Allows users to submit and manage reviews | 8004 |

Each service has:
- A dedicated FastAPI app and Dockerfile  
- Its own database connection  
- RESTful endpoints  
- Integration with a centralized PostgreSQL instance

---

## Team Responsibilities

### Team Member 1 – Dana Kossaybati
- **Services:** Users (8001), Bookings (8003)  
- **Part II Tasks:**  

### Team Member 2 – Reem Hamdar
- **Services:** Rooms (8002), Reviews (8004)  
- **Part II Tasks:**  


---

## Technology Stack
- **Language:** Python 3.10+  
- **Framework:** FastAPI   
- **Database:** PostgreSQL (via Docker container)  
- **Authentication:** JWT-based with Role-Based Access Control (RBAC)  
- **Testing:** Pytest and Postman  
- **Documentation:** Sphinx  
- **Containerization:** Docker and Docker Compose  

---

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/DanaKossaybati/smartmeetingroom_Dana_Kossaybati_Reem_Hamdar.git
cd smartmeetingroom_Dana_Kossaybati_Reem_Hamdar
