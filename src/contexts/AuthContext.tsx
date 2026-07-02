import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "@/services/api";
import type { User } from "@/types";

interface AuthCtx {
  user: User | null;
  isLoading: boolean;
  login: (u: User) => void;
  logout: () => void;
  setRole: (role: User["role"]) => void;
}

const Ctx = createContext<AuthCtx>({
  user: null,
  isLoading: true,
  login: () => {},
  logout: () => {},
  setRole: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (typeof window === "undefined") return;
    let active = true;
    void api.restoreUser().then((restored) => {
      if (active) {
        setUser(restored);
        setIsLoading(false);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (user) localStorage.setItem("indus-user", JSON.stringify(user));
    else localStorage.removeItem("indus-user");
  }, [user]);

  return (
    <Ctx.Provider
      value={{
        user,
        isLoading,
        login: (u) => setUser(u),
        logout: () => {
          setUser(null);
          void api.logout();
        },
        setRole: (role) => setUser((u) => (u ? { ...u, role } : u)),
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);
