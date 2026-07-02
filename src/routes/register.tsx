import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";

export const Route = createFileRoute("/register")({
  component: RegisterPage,
});

const schema = z.object({
  name: z.string().min(2, "Required"),
  email: z.string().email(),
  password: z.string().min(6, "At least 6 characters"),
  org: z.string().min(2, "Required"),
});
type FormData = z.infer<typeof schema>;

function RegisterPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    try {
      const res = await api.register(data.name, data.email, data.password);
      if (res.requiresConfirmation) {
        toast.success("Account created. Confirm your email, then sign in.");
        navigate({ to: "/login" });
        return;
      }
      login(res.user);
      toast.success("Account created");
      navigate({ to: "/dashboard" });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to create account");
    }
  };

  return (
    <AuthLayout
      title="Create your workspace"
      subtitle="Start indexing your industrial knowledge in minutes"
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="text-primary font-medium">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-2">
          <Label>Full name</Label>
          <Input {...register("name")} />
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
        </div>
        <div className="space-y-2">
          <Label>Organization</Label>
          <Input {...register("org")} />
          {errors.org && <p className="text-xs text-destructive">{errors.org.message}</p>}
        </div>
        <div className="space-y-2">
          <Label>Work email</Label>
          <Input type="email" {...register("email")} />
          {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
        </div>
        <div className="space-y-2">
          <Label>Password</Label>
          <Input type="password" {...register("password")} />
          {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
        </div>
        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? "Creating…" : "Create account"}
        </Button>
      </form>
    </AuthLayout>
  );
}
