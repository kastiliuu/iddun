# IDDUN mobile

Expo SDK 57, React Native and Expo Router. The Flask application in the repository root is the authoritative source for accounts, published experiences, real availability and reservations.

## Run locally

```bash
cd mobile
npm ci
npm run typecheck
npm start
```

For a physical device, set `EXPO_PUBLIC_API_URL` to a Flask address that the device can reach on the same network. The default API host is `https://iddun-web.onrender.com`. Set `EXPO_PUBLIC_WEB_URL` if the web catalogue lives elsewhere.

## Current integration status

The app is a visual prototype with local mock profiles, feed, favourites, login and service availability. The Discover screen reads published experiences from Flask's `/api/v1/experiences` endpoint and opens their real web pages. Other `src/api` modules describe planned endpoints that Flask does not yet expose. Data saved in the local store does not sync with web accounts.

The booking preview never confirms a reservation. Its final action opens the real web catalogue, where Flask checks slots and creates reservations. The selected mock service, date and time do not carry over. Do not publish the prototype as a transactional app before replacing the mock flows with the shared API.

## Shared contract to implement

1. Version a Flask API for session and account contexts, public catalogues and profiles.
2. Serve published experiences and available slots from the same services used by the web pages. Expose stable IDs and real media URLs.
3. Perform booking holds, confirmation, cancellation and verified reviews through the existing Flask services. Enforce ownership, availability, cutoff and conflicts on the server.
4. Connect the mobile screens to the API, including loading, empty and error states. Keep prototype data available only in development.
5. Validate the same account, reservation and reputation flows on web, Android and iOS.

Visual layouts can suit each platform; prices, availability, account identity and reservation status must come from the same backend.
