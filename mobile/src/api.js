// Thin API client for the Fishing Copilot backend.
import Constants from "expo-constants";
import AsyncStorage from "@react-native-async-storage/async-storage";

const BASE_URL =
  Constants.expoConfig?.extra?.apiBaseUrl ||
  Constants.manifest?.extra?.apiBaseUrl ||
  "http://localhost:8000";

const USER_KEY = "fc_user_id";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

export async function getStoredUserId() {
  return AsyncStorage.getItem(USER_KEY);
}

export async function storeUserId(userId) {
  if (userId) await AsyncStorage.setItem(USER_KEY, userId);
}

// A session starts automatically when the app opens.
export async function startSession(location) {
  const userId = await getStoredUserId();
  const session = await request("/session/start", {
    method: "POST",
    body: JSON.stringify({ location, user_id: userId || undefined }),
  });
  await storeUserId(session.user_id);
  return session;
}

export function getDecision(location) {
  return request(`/decision?location=${encodeURIComponent(location)}`);
}

export function getPlan({ location, fishingType, skillLevel }) {
  return request("/plan", {
    method: "POST",
    body: JSON.stringify({
      location,
      fishing_type: fishingType,
      skill_level: skillLevel,
    }),
  });
}

export function logResult({ sessionId, result, bait, notes }) {
  return request("/log", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      result,
      bait: bait || null,
      notes: notes || null,
    }),
  });
}

export async function getHistory() {
  const userId = await getStoredUserId();
  if (!userId) return { user_id: null, sessions: [] };
  return request(`/history?user_id=${encodeURIComponent(userId)}`);
}

export { BASE_URL };
