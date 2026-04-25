# Account Deletion API - Quick Reference

## API Endpoints

### Get Deletion Information
```
GET /api/users/users/account_deletion_info/
Authorization: Bearer {JWT_TOKEN}
```
Shows what will be deleted (orders, addresses, etc.)

### Delete Account
```
POST /api/users/users/request_account_deletion/
Authorization: Bearer {JWT_TOKEN}
Content-Type: application/json

{
  "password": "user_password",
  "delete_method": "soft",  // or "hard"
  "confirm_deletion": true
}
```

---

## Quick Examples

### 1. Get Deletion Info (Python)
```python
import requests

headers = {'Authorization': f'Bearer {jwt_token}'}
response = requests.get(
    'https://api.example.com/api/users/users/account_deletion_info/',
    headers=headers
)
deletion_info = response.json()
print(f"Orders to delete: {deletion_info['related_data']['orders']}")
print(f"Addresses to delete: {deletion_info['related_data']['addresses']}")
```

### 2. Delete Account (Python)
```python
import requests

headers = {'Authorization': f'Bearer {jwt_token}'}
payload = {
    'password': 'user_password',
    'delete_method': 'soft',  # soft = anonymize, hard = permanent
    'confirm_deletion': True
}

response = requests.post(
    'https://api.example.com/api/users/users/request_account_deletion/',
    json=payload,
    headers=headers
)

if response.status_code == 200:
    print("✅ Account deleted successfully")
    result = response.json()
    print(f"Deleted at: {result['deleted_at']}")
else:
    print(f"❌ Error: {response.json()}")
```

### 3. Delete Account (cURL)
```bash
# Get deletion info
curl -X GET https://api.example.com/api/users/users/account_deletion_info/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Delete account (soft)
curl -X POST https://api.example.com/api/users/users/request_account_deletion/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "your_password",
    "delete_method": "soft",
    "confirm_deletion": true
  }'

# Delete account (hard - permanent)
curl -X POST https://api.example.com/api/users/users/request_account_deletion/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "your_password",
    "delete_method": "hard",
    "confirm_deletion": true
  }'
```

### 4. Delete Account (JavaScript/Fetch)
```javascript
// Get deletion info
async function checkDeletion() {
  const response = await fetch(
    'https://api.example.com/api/users/users/account_deletion_info/',
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  return response.json();
}

// Delete account
async function deleteMyAccount(password, method = 'soft') {
  const response = await fetch(
    'https://api.example.com/api/users/users/request_account_deletion/',
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        password: password,
        delete_method: method,
        confirm_deletion: true
      })
    }
  );
  return response.json();
}

// Usage
const info = await checkDeletion();
if (info.related_data.orders > 0) {
  alert('You have pending orders. Please cancel them first.');
} else {
  const result = await deleteMyAccount('mypassword', 'soft');
  console.log('Account deleted:', result);
}
```

---

## Deletion Methods Comparison

| Feature | Soft Delete | Hard Delete |
|---------|-------------|------------|
| Speed | Fast | Slower |
| Recovery | 30 days | Never |
| Personal Data | Anonymized | Removed |
| Email Available | After 30 days | Immediately |
| Order History | Kept | Kept |
| Best For | Privacy concerns | Complete removal |

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | ✅ Deletion successful |
| 400 | ❌ Bad request (validation error) |
| 401 | ❌ Unauthorized (invalid token) |
| 403 | ❌ Forbidden (pending orders) |
| 404 | ❌ User not found |
| 500 | ❌ Server error |

---

## Error Responses

**Wrong Password:**
```json
{
  "password": ["Invalid password"]
}
```

**No Confirmation:**
```json
{
  "confirm_deletion": ["You must confirm account deletion by setting confirm_deletion to true"]
}
```

**Pending Orders:**
```json
{
  "detail": "You have 2 pending order(s). Please cancel them before deleting your account."
}
```

**Already Deleted:**
```json
{
  "detail": "Account is already deleted"
}
```

---

## What Gets Deleted

### Hard Delete (Everything)
- ✅ User account
- ✅ Personal information (name, email, phone)
- ✅ Profile picture
- ✅ All addresses
- ✅ Cart items
- ✅ Authentication tokens
- ✅ Google OAuth tokens
- ✅ OTP records
- ⚠️ Orders (kept for tax purposes)

### Soft Delete (Anonymized)
- ✅ Personal data replaced with generic values
- ✅ Account becomes inaccessible
- ✅ Email replaced: deleted_{user_id}@deleted.local
- ✅ Name: "Deleted User"
- ✅ Phone: Removed
- ✅ Account marked inactive
- ⚠️ Can be restored within 30 days

---

## Checklist for Frontend

```
Before showing delete button:
- [ ] User is authenticated
- [ ] User hasn't already deleted account
- [ ] Check for pending orders

When user clicks delete:
1. [ ] Show warning dialog
2. [ ] List what will be deleted
3. [ ] Ask for confirmation
4. [ ] Get password confirmation
5. [ ] Show loading state
6. [ ] Handle success/error response
7. [ ] Redirect to login page
8. [ ] Show success message
9. [ ] Offer support contact

API Call:
1. [ ] GET /account_deletion_info/ first
2. [ ] Check related_data counts
3. [ ] If orders > 0, show warning
4. [ ] POST /request_account_deletion/
5. [ ] Include password
6. [ ] Set confirm_deletion: true
7. [ ] Choose deletion method

After deletion:
1. [ ] Clear auth tokens
2. [ ] Clear local storage
3. [ ] Clear cookies
4. [ ] Redirect to homepage
5. [ ] Show "Account deleted successfully"
6. [ ] Offer support link
```

---

## Troubleshooting

**"Invalid password" error**
- Double-check password is correct
- Clear browser cache
- Try password reset if forgotten

**"Pending orders" error**
- Go to Orders page
- Cancel pending orders
- Try deletion again

**"Unauthorized" error**
- JWT token might have expired
- Re-login and try again
- Check token is in Authorization header

**"Server error" response**
- Try again in a few moments
- Check internet connection
- Contact support if persists

---

## Important Notes

⚠️ **This action is permanent!**
- Hard delete cannot be undone
- Data cannot be recovered
- Consider soft delete first

📧 **Confirmation Email**
- User receives deletion confirmation
- Email includes timestamp
- No further action needed

🔐 **Security**
- Password required to prevent accidental deletion
- Explicit confirmation flag required
- All sessions terminated after deletion

---

## Support Links

- API Documentation: `/docs/ACCOUNT_DELETION_API.md`
- FAQ: `/help/account-deletion-faq`
- Support: support@example.com
- Emergency: +971-XX-XXXXXXX

---

**Last Updated:** January 2024
