# Delivery Timeslot System — Frontend Integration Guide

## Overview

The delivery timeslot system allows customers to select a preferred delivery time window when placing an order.  
Each timeslot has a **cutoff time** — orders must be placed before that time (same day) to be eligible for a given slot.

**Timezone:** All times are in **UAE time (Asia/Dubai, UTC+4)**.

---

## How It Works

| Slot             | Window       | Cutoff  |
|------------------|--------------|---------|
| Early Morning    | 8 AM – 9 AM  | 7:30 AM |
| Morning          | 10 AM – 11 AM| 9:30 AM |
| Midday           | 12 PM – 1 PM | 11:30 AM|
| Afternoon        | 2 PM – 3 PM  | 1:30 PM |
| Evening          | 6 PM – 7 PM  | 5:30 PM |

- A customer ordering at **8:00 AM today** will only see slots from **Morning (10 AM)** onward, since the Early Morning cutoff (7:30 AM) has passed.
- For **future dates**, all active slots are available.
- Admin can **disable a slot for a specific date** (e.g. holiday, no delivery boys available).

---

## Customer Flow

### Step 1 — Let customer pick a delivery date

Show a date picker. Only allow today or future dates.

---

### Step 2 — Fetch available slots for that date

```
GET /api/orders/delivery-slots/available/?date=YYYY-MM-DD
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Parameter | Type   | Required | Description                           |
|-----------|--------|----------|---------------------------------------|
| `date`    | string | No       | Format: `YYYY-MM-DD`. Defaults to today (UAE time). |

**Success Response `200 OK`:**

```json
{
  "date": "2026-04-13",
  "available_slots": [
    {
      "id": 1,
      "name": "Early Morning",
      "start_time": "08:00:00",
      "end_time": "09:00:00",
      "cutoff_time": "07:30:00",
      "start_time_display": "08:00 AM",
      "end_time_display": "09:00 AM",
      "sort_order": 1
    },
    {
      "id": 2,
      "name": "Morning",
      "start_time": "10:00:00",
      "end_time": "11:00:00",
      "cutoff_time": "09:30:00",
      "start_time_display": "10:00 AM",
      "end_time_display": "11:00 AM",
      "sort_order": 2
    }
  ]
}
```

**If no slots available (today with all cutoffs passed, or admin disabled all):**

```json
{
  "date": "2026-04-12",
  "available_slots": []
}
```

**Error — Past date selected `400 Bad Request`:**

```json
{
  "detail": "Cannot select a past date.",
  "available_slots": []
}
```

**Error — Invalid date format `400 Bad Request`:**

```json
{
  "detail": "Invalid date format. Use YYYY-MM-DD."
}
```

---

### Step 3 — Display slots to the customer

Use `start_time_display` and `end_time_display` for human-readable labels.

**Example UI rendering:**

```
○  08:00 AM – 09:00 AM   (Early Morning)
●  10:00 AM – 11:00 AM   (Morning)        ← selected
○  12:00 PM – 01:00 PM   (Midday)
```

**Tip:** If `available_slots` is empty for today, suggest the customer pick a future date.

---

### Step 4 — Place order with selected slot

When calling the create order endpoint, include:

```
POST /api/orders/
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "shipping_address": 1,
  "preferred_delivery_date": "2026-04-13",
  "preferred_delivery_slot": 2,
  "delivery_notes": "Leave at the door"
}
```

| Field                      | Type    | Description                                    |
|----------------------------|---------|------------------------------------------------|
| `preferred_delivery_date`  | string  | `YYYY-MM-DD`                                   |
| `preferred_delivery_slot`  | integer | The `id` returned from the available slots API |
| `delivery_notes`           | string  | Optional free-text note for the delivery boy   |

---

### Step 5 — Read slot info from order details

When fetching an order, the slot details are embedded:

```
GET /api/orders/{id}/
```

**Response includes:**

```json
{
  "id": 123,
  "preferred_delivery_date": "2026-04-13",
  "preferred_delivery_slot": 2,
  "preferred_delivery_slot_details": {
    "id": 2,
    "name": "Morning",
    "start_time": "10:00:00",
    "end_time": "11:00:00",
    "cutoff_time": "09:30:00",
    "start_time_display": "10:00 AM",
    "end_time_display": "11:00 AM",
    "sort_order": 2
  }
}
```

---

## Recommended Frontend Logic

```js
async function loadAvailableSlots(date) {
  const response = await fetch(
    `/api/orders/delivery-slots/available/?date=${date}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const data = await response.json();

  if (!response.ok) {
    // Handle error (past date, invalid format)
    showError(data.detail);
    return [];
  }

  if (data.available_slots.length === 0) {
    showMessage("No delivery slots available for this date. Please select another date.");
    return [];
  }

  return data.available_slots;
}

// When customer picks a date
const slots = await loadAvailableSlots("2026-04-13");
// Render slot radio buttons using slot.id, slot.start_time_display, slot.end_time_display
```

---

## Admin Endpoints (Admin Panel / Dashboard)

> All admin endpoints require `is_staff = true`.

### Manage Timeslots (Global)

| Method | URL                                         | Description                    |
|--------|---------------------------------------------|--------------------------------|
| GET    | `/api/orders/delivery-slots/`               | List all slots                 |
| POST   | `/api/orders/delivery-slots/`               | Create a new slot              |
| GET    | `/api/orders/delivery-slots/{id}/`          | Get slot detail                |
| PATCH  | `/api/orders/delivery-slots/{id}/`          | Update a slot                  |
| DELETE | `/api/orders/delivery-slots/{id}/`          | Delete a slot                  |
| POST   | `/api/orders/delivery-slots/{id}/activate/` | Globally activate a slot       |
| POST   | `/api/orders/delivery-slots/{id}/deactivate/` | Globally deactivate a slot   |

**Create Slot — Request Body:**

```json
{
  "name": "Early Morning",
  "start_time": "08:00",
  "end_time": "09:00",
  "cutoff_time": "07:30",
  "is_active": true,
  "sort_order": 1
}
```

**Filter slots:**

```
GET /api/orders/delivery-slots/?is_active=true
GET /api/orders/delivery-slots/?ordering=sort_order
```

---

### Manage Date Overrides (Per-Date Disable/Enable)

Use this to block a slot on a specific date (e.g. Friday, holiday, no drivers).

| Method | URL                                              | Description                        |
|--------|--------------------------------------------------|------------------------------------|
| GET    | `/api/orders/delivery-slot-overrides/`           | List all overrides                 |
| POST   | `/api/orders/delivery-slot-overrides/`           | Create an override                 |
| GET    | `/api/orders/delivery-slot-overrides/{id}/`      | Get override detail                |
| PATCH  | `/api/orders/delivery-slot-overrides/{id}/`      | Update an override                 |
| DELETE | `/api/orders/delivery-slot-overrides/{id}/`      | Remove an override                 |

**Create Override — Disable "Early Morning" on April 15:**

```json
{
  "slot": 1,
  "date": "2026-04-15",
  "is_active": false,
  "reason": "No delivery boys available"
}
```

**Filter overrides:**

```
GET /api/orders/delivery-slot-overrides/?date=2026-04-15
GET /api/orders/delivery-slot-overrides/?slot=1
GET /api/orders/delivery-slot-overrides/?is_active=false
```

---

## Priority Rules Summary

| Condition                          | Result                           |
|------------------------------------|----------------------------------|
| Slot `is_active = false` (global)  | Hidden from all users, all dates |
| Override `is_active = false`        | Hidden for that specific date only |
| Override `is_active = true`         | Shown for that date (even if near cutoff — but cutoff still applies for today) |
| Today + current time ≥ cutoff       | Slot hidden for today            |
| Future date, no override, active   | Slot shown                       |

---

## Error Reference

| HTTP Status | Scenario                                         |
|-------------|--------------------------------------------------|
| `200`       | Success                                          |
| `400`       | Past date selected or invalid date format        |
| `401`       | Missing or invalid authentication token          |
| `403`       | Non-admin accessing admin-only endpoints         |
