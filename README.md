# Civic Intelligence System – User Service

Microservice for user authentication and account management.

---

## Overview

This service provides APIs for:

- User registration and authentication  
- Email verification and password reset  
- User account retrieval  

---

## Services

| Service | Base URL | Description |
|--------|--------|------------|
| User/Auth Service | (domain or in case of local http://localhost) | Authentication and user management |


---

## Authentication Flow

1. Register user  
2. Verify email  
3. Login  
4. Access protected APIs  

---

## API Reference

---

## User and Authentication APIs

### 1. Register User

POST /register  
URL: Base URL

Request Body:
```
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "your_password",
  "phone": "your_phone_number"
}
```
---

### 2. Login User

POST /login  
URL: Base URL

Request Body:
```
{
  "email": "john@example.com",
  "password": "your_password"
}
```
---

### 3. Verify Email

GET /verify_email?access_token=access-token  
URL: Base URL 

Description: Verifies user email using the token sent via email.

---

### 4. Forgot Password

POST /forget  
URL: Base URL  

Request Body:
```
{
  "email": "john@example.com"
}
```
---

### 5. Reset Password

POST /reset  
URL: Base URL  

Request Body:
```
{
  "token": "reset_token_here",
  "password": "new_password"
}
```
---

### 7. Get Account Details by Token for token verification

POST /account  
URL: Base URL  

Request Body:
```
{
  "access_token": "",
  "token_type": "bearer"
}
```
Note: This endpoint may require authentication.

---

### 6. Get Account Details

POST /get_user  
URL: Base URL  

Request Body:
```
{
  "id": 1
}
```
Note: This endpoint may require authentication.

---

## Example Workflow

User Flow:
1. Register user  
2. Verify email  
3. Login  
4. Fetch account details  

---

## Collection

Postman Collection Name: Complaints  

Main Requests:
- Register  
- Login  
- Verify Email  
- Forget Password  
- Reset Password  
- Account  