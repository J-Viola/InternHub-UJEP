import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  createApiClient,
  setAccessToken as setApiClientToken,
} from "@api/apiClient";
import { useUser } from "@hooks/UserProvider";
import { useNavigate } from "react-router-dom";
import { useMessage } from "@hooks/MessageContext";

const AuthContext = createContext(null);

const PUBLIC_PATHS = ["/", "/login", "/registrace", "/reset-password"];

function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const isRefreshingRef = useRef(false);
  const accessTokenRef = useRef(accessToken);
  const { setUser, cleanUser } = useUser();
  const navigate = useNavigate();
  const { addMessage } = useMessage();
  const [apiClient] = useState(() => createApiClient(navigate));

  const _updateToken = (token) => {
    setAccessToken(token);
    setApiClientToken(token);
  };

  useEffect(() => {
    accessTokenRef.current = accessToken;
  }, [accessToken]);

  const refreshUX = async () => {
    if (!apiClient) return false;

    try {
      const res = await apiClient.post(
        "/users/token/refresh/",
        {},
        { withCredentials: true },
      );

      if (res?.data?.access) {
        _updateToken(res.data.access);

        if (res.data.user) {
          setUser(res.data.user);
          localStorage.setItem("user", JSON.stringify(res.data.user));
        }
        return true;
      }
    } catch {
      handleAuthFailure();
      return false;
    }
    return false;
  };

  const handleAuthFailure = () => {
    const wasLoggedIn = !!accessTokenRef.current;
    _updateToken(null);
    localStorage.removeItem("user");
    cleanUser();
    if (wasLoggedIn) {
      sessionStorage.setItem(
        "pendingMessage",
        JSON.stringify({
          text: "Vaše relace vypršela. Přihlaste se prosím znovu.",
          type: "W",
        }),
      );
    }
  };

  // On mount: try to restore session via cookie-based refresh
  useEffect(() => {
    const currentPath = window.location.pathname;

    refreshUX()
      .then((success) => {
        if (
          success &&
          PUBLIC_PATHS.some(
            (p) =>
              currentPath === p || currentPath.startsWith("/reset-password"),
          )
        ) {
          navigate("/nabidka");
        }
      })
      .finally(() => {
        setIsInitializing(false);
      });
  }, []);

  // Periodic token refresh every 4.5 minutes
  useEffect(() => {
    if (accessToken) {
      const intervalId = setInterval(refreshUX, 1000 * 60 * 4.5);
      return () => clearInterval(intervalId);
    }
  }, [accessToken]);

  // Handle 401 auto-refresh with request queue
  useEffect(() => {
    if (!apiClient) return;

    let refreshSubscribers = [];
    let refreshPromise = null;

    const subscribeTokenRefresh = (cb) => {
      refreshSubscribers.push(cb);
    };

    const onTokenRefreshed = (newToken) => {
      refreshSubscribers.forEach((cb) => cb(newToken, null));
      refreshSubscribers = [];
      refreshPromise = null;
    };

    const onRefreshFailed = (err) => {
      refreshSubscribers.forEach((cb) => cb(null, err));
      refreshSubscribers = [];
      refreshPromise = null;
    };

    const responseInterceptor = apiClient.interceptors.response.use(
        (response) => response,
        async (error) => {
          const originalRequest = error.config;
        const requestUrl = originalRequest?.url || "";
        const isAuthEndpoint = ["/users/token/refresh/", "/users/login/"].some(
          (endpoint) => requestUrl.includes(endpoint),
        );
        if (error.response?.status === 401 && !isAuthEndpoint && !originalRequest?._retry) {
          // If a refresh is already in progress, queue this request
          if (isRefreshingRef.current) {
            return new Promise((resolve, reject) => {
              subscribeTokenRefresh((newToken, err) => {
                if (err) {
                  reject(err);
                } else {
                  originalRequest.headers.Authorization = `Bearer ${newToken}`;
                  resolve(apiClient(originalRequest));
                }
              });
            });
          }

          isRefreshingRef.current = true;
          originalRequest._retry = true;

          refreshPromise = apiClient
            .post("/users/token/refresh/", {}, { withCredentials: true })
            .then((res) => {
              if (res?.data?.access) {
                _updateToken(res.data.access);
                onTokenRefreshed(res.data.access);
                return res.data.access;
              }
              throw new Error("No access token in refresh response");
            })
            .catch((refreshError) => {
              onRefreshFailed(refreshError);
              handleAuthFailure();
              throw refreshError;
            })
            .finally(() => {
              isRefreshingRef.current = false;
            });

          const newToken = await refreshPromise;
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return apiClient(originalRequest);
        }
        throw error;
      },
    );

    return () => {
      apiClient.interceptors.response.eject(responseInterceptor);
    };
  }, [apiClient]);

  const login = async (loginData) => {
    if (!apiClient) throw new Error("API není inicializován!");

    const response = await apiClient.post("/users/login/", loginData, {
      headers: { "Content-Type": "application/json" },
      withCredentials: true,
    });

    if (response.data) {
      _updateToken(response.data.access);

      if (response.data.user) {
        setUser(response.data.user);
        sessionStorage.setItem(
          "pendingMessage",
          JSON.stringify({
            text: `Uživatel ${response.data.user?.email ?? ""} byl úspěšně přihlášen`,
            type: "S",
          }),
        );
        localStorage.setItem("user", JSON.stringify(response.data.user));
      }

      setTimeout(() => navigate("/nabidka"), 100);
    }

    return response;
  };

  const logout = async () => {
    if (!apiClient) throw new Error("API není inicializován!");

    try {
      await apiClient.post("/users/logout/", {}, { withCredentials: true });
    } finally {
      _updateToken(null);
      localStorage.removeItem("user");
      cleanUser();
      navigate("/");
    }
  };

  // TODO: Wrap login, logout, apiClient in useCallback for stable memo deps
  const contextValue = useMemo(
    () => ({
      accessToken,
      login,
      logout,
      apiClient,
      isInitializing,
    }),
    [accessToken, isInitializing],
  );

  return (
    <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth volej, pokud jsi pod AuthProvider!");
  }
  return context;
}

export default AuthProvider;
