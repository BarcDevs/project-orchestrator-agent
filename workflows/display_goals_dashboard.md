# Workflow: Display Goals + Milestones in Dashboard

## Objective
Wire goals data from backend to dashboard UI. User sees their recovery goals and milestones on first login.

## Required Inputs
- Goals already created in PostgreSQL (backend done: task created 2026-04-13)
- Milestones added to goals table
- Dashboard component exists but not connected

## Steps

### 1. Backend: Verify goals schema
- Check `prisma/schema.prisma` for Goal model
- Verify fields: id, title, description, milestones[], createdAt
- Run `prisma db push` if schema changed

### 2. Backend: Create GET /api/goals endpoint
- Location: `pages/api/goals.ts` or `src/routes/goals.ts`
- Returns: `{ goals: [{ id, title, description, milestones: [...] }] }`
- Test with Postman: GET /api/goals → should return mock/real data

### 3. Frontend: Hook dashboard to goals API
- File: `components/Dashboard.tsx`
- Use `useQuery` (TanStack Query) to fetch `/api/goals`
- Map goals to display: title + milestone list
- Show loading state while fetching

### 4. Test end-to-end
- Login → Dashboard loads → Goals visible
- Refresh page → Data persists
- Check browser console: no errors

## Done When
- ✓ Goals display on dashboard with title, description, milestones
- ✓ Data persists across page reloads
- ✓ No console errors
- ✓ Postman test passes

## Time Estimate
~90 minutes (backend 30m + frontend 45m + test 15m)

## Blockers
- None if schema already exists
- Check Git history if uncertain

## Edge Cases
- No goals exist yet: return empty array `[]`, show "No goals yet" UI
- API timeout: TanStack Query retry logic handles (3 retries default)
