import posthog from "posthog-js";

const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY || "";
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST || "https://analytics.yantra4d.com";

let initialized = false;

export function initPostHog() {
  if (initialized || typeof window === "undefined") return;
  if (!POSTHOG_KEY) return;
  if (navigator.doNotTrack === "1") return;

  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    capture_pageview: true,
    autocapture: true,
    respect_dnt: true,
    persistence: "localStorage+cookie",
    secure_cookie: true,
    disable_session_recording: true,
  });
  initialized = true;
}

export function identifyUser(userId, traits) {
  if (!initialized) return;
  posthog.identify(userId, traits);
}

export function resetUser() {
  if (!initialized) return;
  posthog.reset();
}

export function trackEvent(event, properties) {
  if (!initialized) return;
  posthog.capture(event, properties);
}
