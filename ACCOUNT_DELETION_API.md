# Account Deletion API Documentation

## Overview

The Account Deletion API allows users to permanently delete their accounts and all associated data. This feature is essential for compliance with privacy regulations like GDPR and gives users full control over their data.

---

## Features

✅ **Complete Data Deletion**
- User account permanently deleted or anonymized
- All orders, addresses, cart items deleted
- All authentication tokens invalidated
- Profile pictures and media removed

✅ **Security**
- Password confirmation required
- Explicit confirmation flag required
- Admin-only hard delete option
- Comprehensive audit logging

✅ **Safety Checks**
- Prevents deletion if pending orders exist
- Cancellation warnings before proceeding
- Deletion confirmation email sent

✅ **Two Deletion Methods**
- **Soft Delete (Anonymize)**: Replace personal data with generic values
- **Hard Delete**: Permanently remove all data from database

---

## API Endpoints

### 1. Get Deletion Information

**Endpoint:** `GET /api/users/users/account_deletion_info/`

**Authentication:** Required (JWT Token)

**Description:** Get information about what will be deleted when the account is deleted.

**Response:**
```json
{
  "user": {
    "id": 123,
    "email": "user@example.com",
    "phone_number": "+971501234567",
    "name": "John Doe"
  },
  "related_data": {
    "addresses": 3,
    "orders": 5,
    "cart_items": 2,
    "profile": true,
    "google_oauth": false
  },
  "note": "This action is irreversible. All data will be permanently deleted."
}
```

### 2. Request Account Deletion

**Endpoint:** `POST /api/users/users/request_account_deletion/`

**Authentication:** Required (JWT Token)

**Description:** Permanently delete user account with all related data.

**Request Body:**
```json
{
  "password": "user_password_here",
  "delete_method": "soft",
  "confirm_deletion": true
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `password` | string | Yes | User's account password for verification |
| `delete_method` | string | Yes | Either "soft" (anonymize) or "hard" (permanent delete) |
| `confirm_deletion` | boolean | Yes | Must be true to confirm deletion |

**Response (Success):**
```json
{
  "status": "success",
  "user_id": 123,
  "user_email": "user@example.com",
  "user_phone": "+971501234567",
  "deletion_method": "soft",
  "deletion_status": "anonymized",
  "deleted_at": "2024-01-15T10:30:45.123456Z",
  "message": "Account successfully anonymized"
}
```

**Response (Error - Pending Orders):**
```json
{
  "detail": "You have 2 pending order(s). Please cancel them before deleting your account."
}
```

**Response (Error - Invalid Password):**
```json
{
  "password": ["Invalid password"]
}
```

**Response (Error - Not Confirmed):**
```json
{
  "confirm_deletion": ["You must confirm account deletion by setting confirm_deletion to true"]
}
```

---

## Deletion Methods

### Soft Delete (Anonymize)
```json
"delete_method": "soft"
```
- Personal data replaced with generic values
- Account becomes inaccessible
- Faster recovery option if user changes mind
- Complies with privacy regulations
- Data structure preserved

**After Soft Delete:**
- Email: `deleted_{user_id}@deleted.local`
- Name: "Deleted User"
- Phone: Null
- is_active: False
- deleted_at: Current timestamp

### Hard Delete (Permanent)
```json
"delete_method": "hard"
```
- Completely removes user and all related data
- Irreversible operation
- Maximum data privacy
- Slower performance (larger deletion)
- Can affect analytics/reports with historical data

**Deleted Data:**
- User account
- User profile and pictures
- All orders
- All addresses
- Cart items
- Authentication tokens
- OTP tokens
- Google OAuth tokens

---

## Usage Examples

### Python/Django Example

```python
import requests

# Get deletion info first
headers = {'Authorization': 'Bearer YOUR_JWT_TOKEN'}
response = requests.get(
    'https://api.example.com/api/users/users/account_deletion_info/',
    headers=headers
)
print(response.json())

# Request deletion
deletion_data = {
    'password': 'user_password',
    'delete_method': 'soft',
    'confirm_deletion': True
}
response = requests.post(
    'https://api.example.com/api/users/users/request_account_deletion/',
    json=deletion_data,
    headers=headers
)

if response.status_code == 200:
    print("Account deleted successfully")
    print(response.json())
else:
    print("Deletion failed:", response.json())
```

### cURL Example

```bash
# Get deletion info
curl -X GET https://api.example.com/api/users/users/account_deletion_info/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Request deletion
curl -X POST https://api.example.com/api/users/users/request_account_deletion/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "user_password",
    "delete_method": "soft",
    "confirm_deletion": true
  }'
```

### JavaScript/Fetch Example

```javascript
// Get deletion info
async function getDeletionInfo() {
  const response = await fetch(
    'https://api.example.com/api/users/users/account_deletion_info/',
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      }
    }
  );
  return response.json();
}

// Request deletion
async function deleteAccount(password, deleteMethod = 'soft') {
  const response = await fetch(
    'https://api.example.com/api/users/users/request_account_deletion/',
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        password: password,
        delete_method: deleteMethod,
        confirm_deletion: true
      })
    }
  );
  return response.json();
}

// Usage
const info = await getDeletionInfo();
console.log('Items to be deleted:', info.related_data);

if (confirm('Are you sure you want to delete your account?')) {
  const result = await deleteAccount('your_password', 'soft');
  console.log('Account deleted:', result);
}
```

---

## Frontend Implementation Checklist

### Step 1: Show Deletion Info
```
1. Call GET /account_deletion_info/
2. Display:
   - Number of orders
   - Number of addresses
   - Account age
   - Warning: "This action is irreversible"
```

### Step 2: Confirmation Dialog
```
1. Show two options:
   - Cancel account (keep data for 30 days)
   - Permanently delete (immediate)
2. Ask user to type their email to confirm
3. Display checklist of what will be deleted
```

### Step 3: Password Verification
```
1. Prompt for account password
2. Explain: "We need this to verify it's you"
3. Show password strength indicator
```

### Step 4: Final Confirmation
```
1. Show summary of deletion
2. "Confirm Deletion" button
3. Optional: Show reasons for deletion survey
```

### Step 5: Success Screen
```
1. Show confirmation message
2. "Account successfully deleted"
3. Redirect to homepage or login
4. Inform: "Confirmation email sent"
```

---

## Security Considerations

### What Happens to User Data

| Data | Action |
|------|--------|
| Personal Information | Permanently deleted or anonymized |
| Email/Phone | Becomes available for new registration |
| Orders | Stored for 7 years (tax compliance) |
| Passwords | Hashed password immediately invalidated |
| Tokens | All JWT tokens invalidated |
| Sessions | All active sessions terminated |
| Profile Pictures | Files deleted from storage |
| API Keys | All revoked |

### Audit Trail

All deletions are logged with:
- User ID
- Email (before deletion)
- Deletion timestamp
- Deletion method (soft/hard)
- IP address (if available)
- User agent

### Notifications

**Email Sent After Deletion:**
- Confirmation of account deletion
- What was deleted
- Timeline of deletion (immediate or soft)
- Contact support link

---

## Error Handling

### Common Errors

**Invalid Password**
```json
{
  "password": ["Invalid password"]
}
```
- User entered wrong password
- Action: Ask user to try again or use password reset

**Pending Orders**
```json
{
  "detail": "You have 3 pending order(s). Please cancel them before deleting your account."
}
```
- User has active/pending orders
- Action: Show pending orders, allow cancellation first

**Confirmation Not Set**
```json
{
  "confirm_deletion": ["You must confirm account deletion..."]
}
```
- User didn't set confirm_deletion to true
- Action: Show checkbox to confirm

**Already Deleted**
```json
{
  "detail": "Account is already deleted"
}
```
- Account was already deleted
- Action: No action needed

**Server Error**
```json
{
  "detail": "Account deletion failed. Please try again later."
}
```
- Unexpected server error
- Action: Show error message, contact support

---

## Compliance & Privacy

### GDPR Compliance
✅ Users can request complete data deletion  
✅ Deletion happens within 30 days  
✅ Audit trail for compliance  
✅ No data sharing with third parties  

### Data Retention
- **Hard Delete**: Immediate (within 24 hours)
- **Soft Delete**: 30 days before purge
- **Orders**: 7 years (tax/legal requirement)
- **Logs**: 1 year for compliance

### User Rights
- **Right to Delete**: Fully supported
- **Right to Download**: Supported (export data endpoint)
- **Right to Know**: Supported (see what will be deleted)
- **Right to Object**: Supported (can restore soft-deleted within 30 days)

---

## Testing

### Test Cases

```
1. Test deletion info retrieval
   - GET /account_deletion_info/
   - Verify counts are accurate

2. Test soft delete
   - POST with delete_method='soft'
   - Verify account is anonymized
   - Verify user can't login

3. Test hard delete
   - POST with delete_method='hard'
   - Verify all data is deleted
   - Verify no recovery possible

4. Test validation
   - Wrong password
   - Confirm not set to true
   - Pending orders present

5. Test email notification
   - Verify confirmation email sent
   - Check email content

6. Test logging
   - Verify deletion logged
   - Check audit trail
```

---

## FAQ

**Q: Can I recover my account after deletion?**  
A: For soft delete, within 30 days. For hard delete, no - it's permanent.

**Q: What happens to my orders?**  
A: Orders are kept for tax/legal reasons. Personal data is removed but order history remains.

**Q: Will my email be available after deletion?**  
A: Yes, after 30 days for soft delete, immediately for hard delete.

**Q: Is there a cooldown period?**  
A: No, deletion happens immediately. Check for pending orders first.

**Q: What about my referral rewards?**  
A: All referral-related data is deleted with the account.

**Q: Will I receive a confirmation?**  
A: Yes, an email is sent confirming the deletion.

---

## Admin API (Future)

For admin panel management:
```
GET /api/admin/deleted-accounts/
- List deleted accounts
- Filter by date
- View deletion details

POST /api/admin/restore-account/{user_id}/
- Restore soft-deleted accounts
- Restore from backup

GET /api/admin/deletion-audit/
- Audit log of all deletions
- Export for compliance
```

---

## Support

For issues or questions:
- Email: support@example.com
- Phone: +971-XX-XXXXXXX
- Help docs: https://help.example.com/account-deletion
- Contact form: https://example.com/contact

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-01-15 | Initial release |

---

**Last Updated:** January 15, 2024
