import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/services/api";

export const Route = createFileRoute("/forgot-password")({
  component: ForgotPage,
});

function ForgotPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  return (
    <AuthLayout
      title="Reset your password"
      subtitle="We'll send a verification code to your email"
      footer={
        <Link to="/login" className="text-primary">
          Back to sign in
        </Link>
      }
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            await api.forgot(email);
            toast.success("Code sent");
            navigate({ to: "/otp" });
          } catch (error) {
            toast.error(error instanceof Error ? error.message : "Unable to send code");
          }
        }}
        className="space-y-4"
      >
        <div className="space-y-2">
          <Label>Email</Label>
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <Button type="submit" className="w-full">
          Send verification code
        </Button>
      </form>
    </AuthLayout>
  );
}
