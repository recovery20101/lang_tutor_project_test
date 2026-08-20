"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { jwtDecode } from 'jwt-decode';

interface AuthContextType {
  token: string | null;
  userEmail: string | null;
  userLevel: string;
  isAuthenticated: boolean;
  login: (token: string, email: string) => void;
  logout: () => void;
  updateUserLevel: (newLevel: string) => Promise<void>;
}

interface DecodedToken {
  exp: number;
  sub: string;
  current_level?: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {

  const [token, setToken] = useState<string | null>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('token');
    }
    return null;
  });

  const [userEmail, setUserEmail] = useState<string | null>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('userEmail');
    }
    return null;
  });

  const [userLevel, setUserLevel] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('userLevel') || "A1";
    }
    return "A1";
  });

  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  const logout = useCallback(() => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
      localStorage.removeItem('userEmail');
      localStorage.removeItem('userLevel');
    }
    setToken(null);
    setUserEmail(null);
    setUserLevel("A1");
    setIsAuthenticated(false);
  }, []);

  const checkTokenValidity = useCallback((jwtToken: string | null) => {
    if (!jwtToken) {
      setIsAuthenticated(false);
      return false;
    }
    try {
      const decodedToken: DecodedToken = jwtDecode(jwtToken);
      const currentTime = Date.now() / 1000;

      if (decodedToken.exp < currentTime) {
        console.log("Token expired.");
        logout();
        return false;
      }

      const levelFromToken = decodedToken.current_level || "A1";
      setUserLevel(levelFromToken);
      if (typeof window !== 'undefined') {
        localStorage.setItem('userLevel', levelFromToken);
      }

      setIsAuthenticated(true);
      return true;
    } catch (error) {
      console.error("Error decoding token:", error);
      logout();
      return false;
    }
  }, [logout]);

  useEffect(() => {
    let isMounted = true;

    const verify = async () => {
      if (token) {
        await checkTokenValidity(token);
      } else {
        if (isMounted) {
          setIsAuthenticated(false);
          setUserLevel("A1");
        }
      }
    };

    verify();

    return () => {
      isMounted = false;
    };
  }, [token, checkTokenValidity]);

  const login = (newToken: string, email: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('token', newToken);
      localStorage.setItem('userEmail', email);
    }
    setToken(newToken);
    setUserEmail(email);

    try {
      const decoded: DecodedToken = jwtDecode(newToken);
      const level = decoded.current_level || "A1";
      setUserLevel(level);
      if (typeof window !== 'undefined') {
        localStorage.setItem('userLevel', level);
      }
    } catch {
      setUserLevel("A1");
      if (typeof window !== 'undefined') {
        localStorage.setItem('userLevel', "A1");
      }
    }

    setIsAuthenticated(true);
  };

  const updateUserLevel = async (newLevel: string) => {
    if (!token) {
      console.error("No token available for updating user level.");
      return;
    }

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/user/update_level`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ level: newLevel }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to update user level on backend.");
      }

      const data = await response.json();
      if (data.new_token) {
        login(data.new_token, userEmail || '');
      } else {
        setUserLevel(newLevel);
        if (typeof window !== 'undefined') {
          localStorage.setItem('userLevel', newLevel);
        }
      }
      console.log("User level updated successfully to:", newLevel);
    } catch (error) {
      console.error("Error updating user level:", error);
    }
  };

  return (
    <AuthContext.Provider value={{ token, userEmail, userLevel, isAuthenticated, login, logout, updateUserLevel }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};