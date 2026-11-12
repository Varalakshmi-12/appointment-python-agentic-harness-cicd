import axios from "axios";

const API = axios.create({
  baseURL: "http://127.0.0.1:5000"
});

// Convert a datetime-local input value (local time) to a UTC ISO string.
// Returns null for empty or invalid input.
export function localInputToUtcIso(v) {
  if (!v) return null;
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

// Convert a UTC ISO string to a datetime-local value (YYYY-MM-DDTHH:mm, local time).
// Returns "" for empty or invalid input.
export function utcIsoToLocalInput(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

export default API;
