// App-wide session state: the auto-started session and the chosen location.
import React, { createContext, useContext, useEffect, useState } from "react";
import { startSession } from "./api";

const SessionCtx = createContext(null);

// Default location until the user changes it. "lat,lon" is accepted too.
const DEFAULT_LOCATION = "Lake Tahoe";

export function SessionProvider({ children }) {
  const [location, setLocation] = useState(DEFAULT_LOCATION);
  const [session, setSession] = useState(null);
  const [error, setError] = useState(null);

  // Auto-start a session whenever the location changes (the "session concept").
  useEffect(() => {
    let cancelled = false;
    startSession(location)
      .then((s) => !cancelled && setSession(s))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [location]);

  return (
    <SessionCtx.Provider value={{ location, setLocation, session, error }}>
      {children}
    </SessionCtx.Provider>
  );
}

export function useSession() {
  return useContext(SessionCtx);
}
