"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/context/auth-context";
import { useRouter } from "next/navigation";

// Login form validation schema
const loginSchema = z.object({
  email: z.string().email({ message: "Invalid email format." }),
  password: z.string().min(1, { message: "Password cannot be empty." }),
});

// Signup form validation schema
const signupSchema = z.object({
  email: z.string().email({ message: "Invalid email format." }),
  password: z.string().min(8, { message: "Password must be at least 8 characters long." }),
  confirmPassword: z.string().min(8, { message: "Password confirmation cannot be empty." }),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords do not match.",
  path: ["confirmPassword"],
});

export function AuthForm({ onClose }: { onClose: () => void }) {
  const { login: authLogin } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState("login");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [signupError, setSignupError] = useState<string | null>(null);
  const [signupSuccess, setSignupSuccess] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loginForm = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const signupForm = useForm<z.infer<typeof signupSchema>>({
    resolver: zodResolver(signupSchema),
    defaultValues: { email: "", password: "", confirmPassword: "" },
  });

  async function handleLogin(values: z.infer<typeof loginSchema>) {
    setIsLoading(true);
    setLoginError(null);
    try {
      const formData = new URLSearchParams();
      formData.append("username", values.email);
      formData.append("password", values.password);

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/token`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData.toString(),
      });

      if (!response.ok) {
        const errorData = await response.json();
        setLoginError(errorData.detail || "Invalid email or password.");
        return;
      }

      const data = await response.json();
      authLogin(data.access_token, values.email);
      onClose(); // Close dialog on successful login
      router.refresh(); // Refresh page to apply user context changes
    } catch (error) {
      console.error("Login error:", error);
      setLoginError("An error occurred during login.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSignup(values: z.infer<typeof signupSchema>) {
    setIsLoading(true);
    setSignupError(null);
    setSignupSuccess(null);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: values.email,
          password: values.password,
          current_level: "A1", // Default user level upon registration
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        setSignupError(errorData.detail || "Registration error.");
        return;
      }

      setSignupSuccess("Registration successful! You can now log in.");
      signupForm.reset(); // Reset signup form
      setActiveTab("login"); // Switch to login tab
    } catch (error) {
      console.error("Registration error:", error);
      setSignupError("An error occurred during registration.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
      <TabsList className="grid w-full grid-cols-2">
        <TabsTrigger value="login">Login</TabsTrigger>
        <TabsTrigger value="signup">Sign Up</TabsTrigger>
      </TabsList>
      <TabsContent value="login">
        <form onSubmit={loginForm.handleSubmit(handleLogin)} className="space-y-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="loginEmail">Email</Label>
            <Input
              id="loginEmail"
              type="email"
              placeholder="your@email.com"
              {...loginForm.register("email")}
              disabled={isLoading}
            />
            {loginForm.formState.errors.email && (
              <p className="text-red-500 text-sm">{loginForm.formState.errors.email.message}</p>
            )}
          </div>
          <div className="grid gap-2">
            <Label htmlFor="loginPassword">Password</Label>
            <Input
              id="loginPassword"
              type="password"
              placeholder="••••••••"
              {...loginForm.register("password")}
              disabled={isLoading}
            />
            {loginForm.formState.errors.password && (
              <p className="text-red-500 text-sm">{loginForm.formState.errors.password.message}</p>
            )}
          </div>
          {loginError && <p className="text-red-500 text-sm">{loginError}</p>}
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? "Logging in..." : "Login"}
          </Button>
        </form>
      </TabsContent>
      <TabsContent value="signup">
        <form onSubmit={signupForm.handleSubmit(handleSignup)} className="space-y-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="signupEmail">Email</Label>
            <Input
              id="signupEmail"
              type="email"
              placeholder="your@email.com"
              {...signupForm.register("email")}
              disabled={isLoading}
            />
            {signupForm.formState.errors.email && (
              <p className="text-red-500 text-sm">{signupForm.formState.errors.email.message}</p>
            )}
          </div>
          <div className="grid gap-2">
            <Label htmlFor="signupPassword">Password</Label>
            <Input
              id="signupPassword"
              type="password"
              placeholder="••••••••"
              {...signupForm.register("password")}
              disabled={isLoading}
            />
            {signupForm.formState.errors.password && (
              <p className="text-red-500 text-sm">{signupForm.formState.errors.password.message}</p>
            )}
          </div>
          <div className="grid gap-2">
            <Label htmlFor="confirmPassword">Confirm Password</Label>
            <Input
              id="confirmPassword"
              type="password"
              placeholder="••••••••"
              {...signupForm.register("confirmPassword")}
              disabled={isLoading}
            />
            {signupForm.formState.errors.confirmPassword && (
              <p className="text-red-500 text-sm">{signupForm.formState.errors.confirmPassword.message}</p>
            )}
          </div>
          {signupError && <p className="text-red-500 text-sm">{signupError}</p>}
          {signupSuccess && <p className="text-green-500 text-sm">{signupSuccess}</p>}
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? "Signing up..." : "Sign Up"}
          </Button>
        </form>
      </TabsContent>
    </Tabs>
  );
}