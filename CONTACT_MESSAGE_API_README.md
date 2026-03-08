# Contact Messages API - Frontend Guide

## Overview
Users can submit contact messages which are stored in the database. Admins can view all messages and reply via email.

---

## Endpoints

### 1. **Create Contact Message** (User)
Submit a new contact message.

**POST** `/api/notifications/contact/`

**Authentication:** Required (Bearer Token)  
**Permissions:** Authenticated users with verified email

**Request Body:**
```json
{
  "subject": "Question about my order",
  "message": "I have a question regarding order #123"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "subject": "Question about my order",
  "message": "I have a question regarding order #123",
  "is_resolved": false,
  "created_at": "2026-03-08T10:30:00Z"
}
```

**Error (403 - Unverified Email):**
```json
{
  "detail": "Your email must be verified to send a message."
}
```

---

### 2. **List All Messages** (Admin Only)
Retrieve all contact messages.

**GET** `/api/notifications/contact/`

**Authentication:** Required (Bearer Token)  
**Permissions:** Admin only

**Query Parameters:**
- `page` - Pagination
- `ordering` - Sort by field

**Response (200 OK):**
```json
{
  "count": 10,
  "next": "...",
  "previous": "...",
  "results": [
    {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com",
      "subject": "Question about my order",
      "message": "I have a question regarding order #123",
      "is_resolved": false,
      "created_at": "2026-03-08T10:30:00Z"
    }
  ]
}
```

---

### 3. **Retrieve Single Message** (Admin Only)
Get details of a specific message.

**GET** `/api/notifications/contact/{id}/`

**Authentication:** Required (Bearer Token)  
**Permissions:** Admin only

**Response (200 OK):**
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "subject": "Question about my order",
  "message": "I have a question regarding order #123",
  "is_resolved": false,
  "created_at": "2026-03-08T10:30:00Z"
}
```

---

### 4. **Reply to Message** (Admin Only)
Send a reply email to the user and optionally mark as resolved.

**POST** `/api/notifications/contact/{id}/reply/`

**Authentication:** Required (Bearer Token)  
**Permissions:** Admin only

**Request Body:**
```json
{
  "reply_message": "Thank you for your inquiry. Your order is being processed...",
  "mark_resolved": true
}
```

**Response (200 OK):**
```json
{
  "detail": "Reply sent successfully to user email."
}
```

**Error (400 - Missing Reply):**
```json
{
  "detail": "Reply message is required."
}
```

**Error (500 - Email Failed):**
```json
{
  "detail": "Failed to send reply: SMTP connection error"
}
```

---

## Frontend Implementation Guide

### **User Side - Send Message**
1. User must have verified email before sending
2. Name and email are auto-filled from user profile
3. Only `subject` and `message` required in request
4. Show success message after submission

### **Admin Dashboard - Manage Messages**
1. List all messages in a table
2. Click on a message to view details
3. Click "Reply" button to open reply modal
4. Fill in reply text and optionally mark as resolved
5. Send reply (email sent to user automatically)

### **Key Points**
- ✅ User email auto-populated (no need to send)
- ✅ User name auto-populated (no need to send)
- ✅ Admin receives notification email when new message arrives
- ✅ User receives reply via email
- ✅ Messages can be marked as resolved
- ✅ No attachment support (text only)

---

## Common Use Cases

**User wants to contact support:**
```
1. Go to Contact Us page
2. Fill "Subject" and "Message"
3. Click "Send"
4. Success message shown
5. Admin receives email notification
```

**Admin needs to reply:**
```
1. Go to Admin Dashboard → Messages
2. Find message and click "Reply"
3. Type response message
4. Check "Mark as Resolved" if needed
5. Click "Send Reply"
6. User receives reply email
```

---

## Error Handling

| Status | Error | Solution |
|--------|-------|----------|
| 401 | Not authenticated | Login first |
| 403 | Email not verified | Verify email in account settings |
| 400 | Missing reply_message | Include reply_message field |
| 500 | Email failed | Check admin email settings |

