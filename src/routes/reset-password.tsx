import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/services/api";

export const Route = createFileRoute("/reset-password")({
  component: ResetPage,
});

function ResetPage() {
  const navigate = useNavigate();
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  return (
    <AuthLayout title="Set a new password" subtitle="Choose a strong password you don't reuse">
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (pw !== confirm) return toast.error("Passwords don't match");
          try {
            await api.reset(pw);
            toast.success("Password updated");
            navigate({ to: "/login" });
          } catch (error) {
            toast.error(error instanceof Error ? error.message : "Unable to update password");
          }
        }}
        className="space-y-4"
      >
        <div className="space-y-2">
          <Label>New password</Label>
          <Input
            type="password"
            value={pw}
            onChange={(e) => setPw(e.target.value)}
            required
            minLength={6}
          />
        </div>
        <div className="space-y-2">
          <Label>Confirm password</Label>
          <Input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
          />
        </div>
        <Button type="submit" className="w-full">
          Update password
        </Button>
      </form>
    </AuthLayout>
  );
}
