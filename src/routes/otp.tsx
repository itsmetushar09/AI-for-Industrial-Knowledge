import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Button } from "@/components/ui/button";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { api } from "@/services/api";

export const Route = createFileRoute("/otp")({
  component: OtpPage,
});

function OtpPage() {
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  return (
    <AuthLayout title="Enter verification code" subtitle="Sent to your registered email">
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            await api.verifyOtp(code);
            toast.success("Verified");
            navigate({ to: "/reset-password" });
          } catch (error) {
            toast.error(error instanceof Error ? error.message : "Invalid verification code");
          }
        }}
        className="space-y-6 flex flex-col items-center"
      >
        <InputOTP maxLength={6} value={code} onChange={setCode}>
          <InputOTPGroup>
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <InputOTPSlot key={i} index={i} />
            ))}
          </InputOTPGroup>
        </InputOTP>
        <Button type="submit" className="w-full" disabled={code.length < 6}>
          Verify
        </Button>
        <button type="button" className="text-sm text-primary">
          Resend code
        </button>
      </form>
    </AuthLayout>
  );
}
