# Appointment Frontend

React (Vite) single-page app for the Appointment Scheduling App. It talks to
the Flask backend in `../appointment-backend` to list, create, edit, and
cancel appointments.

For a full overview of the whole project (what it does, the tech stack, and
how to run everything end to end), see the [root README](../README.md).

## Tech stack

- **React 19** with **React Router** for client-side routing
- **Vite** as the dev server / build tool
- **Axios** for HTTP requests to the backend API

## Pages / routes

| Route         | Component               | Purpose                        |
|---------------|--------------------------|---------------------------------|
| `/`           | `AppointmentList`        | Lists all appointments          |
| `/new`        | `AppointmentForm`        | Creates a new appointment       |
| `/edit/:id`   | `EditAppointment`        | Edits an existing appointment   |

## Backend connection

`src/api.js` creates an Axios instance pointed at the backend:

```js
const API = axios.create({
  baseURL: "http://127.0.0.1:5000"
});
```

Make sure the Flask backend (see `appointment-backend/`) is running on
`127.0.0.1:5000` before using the app, otherwise API requests will fail.

## Running locally

```bash
npm install
npm run dev
```

This starts the Vite dev server (default `http://localhost:5173`) with hot
module reloading.

Other available scripts:

```bash
npm run build    # production build
npm run preview  # preview the production build locally
npm run lint     # run ESLint
```
