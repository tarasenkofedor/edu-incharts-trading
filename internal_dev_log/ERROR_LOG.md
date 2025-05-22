# Development Error Log

This document logs errors encountered during the development of the InChart project, their resolutions, and key takeaways to improve future development and troubleshooting.

---

## Error Entries

### Error Entry 1
**Date:** 2025-05-18 (Approximate, based on recent conversation)
**Error Description:** 
Backend returning `401 Unauthorized` for `POST /data/upload/price` requests, even after attempting to make the endpoint accessible to unauthenticated users.
Log shows: `INFO: 127.0.0.1:0 - "POST /data/upload/price HTTP/1.1" 401 Unauthorized`

**Context/Tool:**
Implementing unauthenticated access for the price data upload feature. Modifying FastAPI backend (`backend/app/routers/data.py`, `backend/app/security.py`) and Vue.js frontend (`frontend/src/components/PriceDataUploader.vue`).

**Attempts to Resolve (if any failed initially):**
1.  **Initial thought:** The `Depends(get_current_active_user)` was still active at the router level in `data.py`.
    *   **Action:** Removed router-level dependency.
    *   **Result:** Error persisted.
2.  **Second thought:** Made `current_user: Optional[User] = Depends(get_current_active_user)` in the `upload_price_data` endpoint definition.
    *   **Action:** Modified the endpoint signature.
    *   **Result:** Error persisted. The `401` was likely coming from deeper within the `Depends(get_current_active_user)` chain, specifically from `Depends(oauth2_scheme)` in `get_current_user`, which mandates a token.
3.  **Frontend Check:** Ensured `PriceDataUploader.vue` was modified to not require a token from Vuex store before attempting upload (i.e., removed the `else` block that stopped the upload).
    *   **Action:** Confirmed frontend change.
    *   **Result:** Error persisted, confirming it was a backend authentication enforcement issue.

**Solution/Resolution (Current Strategy):**
Instead of trying to make the existing authentication scheme purely optional (which is tricky with `OAuth2PasswordBearer`), the strategy shifted to implementing anonymous session tokens:
1.  **Backend:** Create an endpoint (`/auth/anonymous/token`) to issue JWTs for anonymous sessions.
2.  **Backend:** Modify `get_current_user` to recognize these anonymous tokens and return a specific indicator (e.g., a dummy User object or None with specific properties) instead of raising 401 if the token is for an anonymous session. For regular tokens, it works as before. It will still raise 401 if the token is malformed, expired, or a non-anonymous token for a non-existent user.
3.  **Frontend (Vuex):** The `autoLogin` action in Vuex store will be updated. If no existing `authToken` is found in `localStorage`, it will call the new anonymous token endpoint and store the received anonymous session token. This ensures all subsequent API calls have a token.
4.  **Backend Endpoints:** Endpoints like `/data/upload/price` will then expect a token (anonymous or authenticated) and can differentiate behavior if needed based on token type. The `Depends(get_current_active_user)` can be used generally, as it will receive an indication of an anonymous user if that's the token type.

**Key Takeaway/Prevention:**
- FastAPI's `OAuth2PasswordBearer` scheme, when used as a direct dependency, inherently enforces the presence of a token and will raise a 401 if it's missing or malformed before custom logic in the dependent function is reached. Making a dependency `Optional[User]` is not enough if the underlying scheme providing the token requires it strictly.
- For scenarios requiring truly optional authentication or handling unauthenticated users gracefully alongside authenticated ones, a more explicit mechanism like issuing distinct anonymous/guest tokens is often a cleaner and more robust solution. This allows all protected endpoints to consistently expect a token, simplifying their dependency definitions.

### Error Entry 2
**Date:** 2025-05-18
**Error Description:** 
Price data upload is reported as successful by `PriceDataUploader.vue` ("Price data uploaded and validated successfully."), but the `TradingChart.vue` component does not display the uploaded OHLCV data. No console errors are immediately visible related to data rendering.

**Context/Tool:**
Testing the anonymous price data upload feature after resolving backend 500 errors. The frontend successfully sends the data, and the backend processes it without error.

**Attempts to Resolve (if any failed initially):**
- N/A (This is the first log entry for this specific issue).

**Solution/Resolution (Investigation Plan):**
1.  **Examine `frontend/src/App.vue`:** 
    - Verify how the `handlePriceDataUploaded` method updates the `ohlcvData` prop that is passed to `TradingChart.vue`.
    - Ensure the `chartKey` is being updated/changed when new data is received to force a re-render of the `TradingChart` component if necessary.
2.  **Examine `frontend/src/components/TradingChart.vue`:**
    - Review how the `chartData` prop is received and processed internally by the `TradingVue` library component.
    - Check for any specific data structure requirements or update mechanisms for `trading-vue-js`.
    - Ensure the data format passed from `App.vue` matches what `TradingVue` expects (e.g., array of arrays: `[timestamp, open, high, low, close, volume]`).
3.  **Console Logging:** Add `console.log` statements in `App.vue` (when `ohlcvData` is updated) and in `TradingChart.vue` (when `chartData` prop is received or updated) to inspect the data structure and values at each step.
4.  **`trading-vue-js` Documentation:** If the issue isn't apparent, consult the `trading-vue-js` library's documentation for specific guidance on dynamic data updates and expected data formats.

**Key Takeaway/Prevention:**
- When integrating third-party UI components, especially for complex visualizations like charts, closely verify their data update mechanisms and expected data structures. A successful API call doesn't always mean the UI will update correctly without proper prop handling and component reactivity.

--- 
