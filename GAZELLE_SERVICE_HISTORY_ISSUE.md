# Gazelle API Issue: Service History Not Appearing

## Problem Summary

We can successfully create events with `isTuning: true` that are correctly associated with pianos and show the "This is a tuning for this piano" checkbox checked in the UI. However, these completed events do **not** appear in the piano's service history.

## What Works ✅

1. **Event Creation**: `createEvent` mutation successfully creates an APPOINTMENT event
2. **Piano Association**: The event is correctly associated with the piano
3. **isTuning Flag**: The `isTuning: true` flag is set and persists
4. **UI Checkbox**: The "Il s'agit d'un accord pour ce piano" checkbox is checked in Gazelle UI
5. **Event Completion**: `completeEvent` mutation successfully completes the event with status COMPLETE

## What Doesn't Work ❌

- The completed event does **NOT** appear in the piano's service history
- This happens even when:
  - Event type: `APPOINTMENT`
  - Event status: `COMPLETE`
  - Piano is associated (checkbox checked in UI)
  - `isTuning: true` (checkbox checked in UI)

## GraphQL Mutations Used

### 1. Create Event
```graphql
mutation CreateEvent($input: PrivateEventInput!) {
  createEvent(input: $input) {
    event {
      id
      type
      status
      allEventPianos(first: 10) {
        nodes {
          piano { id }
          isTuning
        }
      }
    }
  }
}
```

**Variables:**
```json
{
  "input": {
    "title": "Service: TUNING",
    "start": "2026-01-02T23:44:45.774946",
    "duration": 60,
    "type": "APPOINTMENT",
    "notes": "Test service note",
    "clientId": "cli_xxx",
    "userId": "usr_xxx",
    "pianos": [{"pianoId": "ins_xxx", "isTuning": true}]
  }
}
```

### 2. Update Event (to ensure isTuning)
```graphql
mutation UpdateEvent($eventId: String!, $input: PrivateEventInput!) {
  updateEvent(id: $eventId, input: $input) {
    event {
      id
      allEventPianos(first: 10) {
        nodes {
          piano { id }
          isTuning
        }
      }
    }
  }
}
```

**Variables:**
```json
{
  "eventId": "evt_xxx",
  "input": {
    "pianos": [{"pianoId": "ins_xxx", "isTuning": true}]
  }
}
```

### 3. Complete Event
```graphql
mutation CompleteEvent($eventId: String!, $input: PrivateCompleteEventInput!) {
  completeEvent(eventId: $eventId, input: $input) {
    event {
      id
      status
      allEventPianos(first: 10) {
        nodes {
          piano { id }
          isTuning
        }
      }
    }
  }
}
```

**Variables:**
```json
{
  "eventId": "evt_xxx",
  "input": {
    "resultType": "COMPLETE"
  }
}
```

## Test Results

**Event ID**: `evt_VA1oI96XldqVmipZ`  
**Piano ID**: `ins_1HdzW806WqxPo2Gh`

- ✅ Event created successfully
- ✅ Piano associated: `ins_1HdzW806WqxPo2Gh`
- ✅ `isTuning: true` confirmed in API response
- ✅ Event status: `COMPLETE`
- ✅ UI shows checkbox "Il s'agit d'un accord pour ce piano" is checked
- ❌ Event does NOT appear in piano service history

## Questions for Gazelle Support

1. **Is there a specific mutation or field required** to make a COMPLETE APPOINTMENT event with `isTuning:true` appear in the piano's service history?

2. **Are there additional requirements** beyond `isTuning:true` and `status: COMPLETE`?

3. **Is there a different mutation** (like `addServiceHistory` or similar) that should be used instead of `createEvent` for service history entries?

4. **Does the event need specific properties** (date range, additional fields, etc.) to appear in service history?

5. **Is there a delay or synchronization process** that needs to occur before events appear in service history?

6. **Are there permissions or settings** that control whether events appear in service history?

## Attempted Solutions

- ✅ Creating event with `pianos` and `isTuning: true` in `createEvent`
- ✅ Using `updateEvent` to explicitly set `isTuning: true` after creation
- ✅ Using `completeEvent` with `resultType: COMPLETE`
- ✅ Various combinations of the above
- ❌ No mutation `addServiceHistory` found in API
- ❌ No mutation to associate piano after event creation found

## Expected Behavior

When an event is:
- Type: `APPOINTMENT`
- Status: `COMPLETE`
- Associated with a piano
- Has `isTuning: true`

It should appear in the piano's service history with a tuning icon (wrench icon).

## Current Behavior

The event exists, is associated with the piano, has `isTuning: true`, but does not appear in the service history section of the piano's page.

