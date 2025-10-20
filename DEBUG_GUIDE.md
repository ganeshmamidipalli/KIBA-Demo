# 🐛 Debug Guide: KPA One-Flow Black Screen Issue

## Issue Description
After clicking "Continue" in Step 2, the user sees a black screen instead of the follow-up questions in Step 3.

## Debugging Steps

### 1. Check Browser Console
1. Open the application at `http://localhost:5173`
2. Open browser DevTools (F12)
3. Go to the Console tab
4. Complete the flow step by step and watch for console logs

### 2. Expected Console Logs
You should see these logs in order:

**Step 2 (Product Details):**
```
StepProductDetails: Starting KPA One-Flow intake...
StepProductDetails: KPA One-Flow intake completed: {session_id: "...", intake: {...}}
```

**Step 3 (Specifications):**
```
StepSpecifications: Rendering with props: {kpaSessionId: "...", intakeData: {...}, ...}
StepSpecifications: Render conditions: {hasIntakeData: true, hasQuestions: true, ...}
```

### 3. Troubleshooting

#### If you see "No session ID found":
- The intake process didn't complete successfully
- Check if Step 2 "Continue" button is working
- Verify backend is running on port 8000

#### If you see "Already have intake data, skipping rehydration":
- This is normal - the data was set in Step 2
- Check if the render conditions are correct

#### If you see "shouldShowQuestions: false":
- Check what's causing the condition to fail
- `hasIntakeData` should be true
- `hasQuestions` should be true  
- `hasRecommendations` should be false

### 4. Manual Testing

#### Test Backend Directly:
```bash
# Test intake
curl -X POST http://localhost:8000/api/intake_recommendations \
  -H "Content-Type: application/json" \
  -d '{"product_name": "Test Laptop", "budget_usd": 1500, "quantity": 1, "scope_text": "Test"}'

# Test session retrieval
curl -X GET http://localhost:8000/api/session/{session_id}
```

#### Test Frontend Flow:
1. Complete Step 1 (Project Context)
2. Complete Step 2 (Product Details) - watch console
3. Navigate to Step 3 - watch console
4. Check if follow-up questions appear

### 5. Common Issues

#### Issue: Black screen with no console logs
- **Cause**: JavaScript error preventing component from rendering
- **Solution**: Check for TypeScript/JavaScript errors in console

#### Issue: Console shows "No session ID found"
- **Cause**: Step 2 didn't complete successfully
- **Solution**: Check Step 2 "Continue" button functionality

#### Issue: Console shows correct data but no UI
- **Cause**: Render condition issue
- **Solution**: Check the render conditions in console logs

### 6. Quick Fix

If the issue persists, try this quick fix:

1. **Clear browser storage:**
   - Open DevTools → Application → Storage → Clear All

2. **Restart both servers:**
   ```bash
   # Backend
   cd backend && python server.py
   
   # Frontend  
   cd frontend-new && npm run dev
   ```

3. **Complete the flow again:**
   - Step 1 → Step 2 → Step 3
   - Watch console logs carefully

### 7. Expected Behavior

**Step 2 → Step 3 Transition:**
1. User fills product details
2. Clicks "Continue" 
3. Backend creates session and generates questions
4. Frontend stores session ID and intake data
5. User navigates to Step 3
6. Step 3 shows follow-up questions in a blue card

**Step 3 UI:**
- Blue card with "We need a few more details" title
- List of follow-up questions with input fields
- "Continue to Recommendations" button

---

**If you're still seeing issues, please share the console logs and I'll help debug further! 🐛**
