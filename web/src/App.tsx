import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { type ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import { Layout } from "@/components/Layout";
import { Login } from "@/pages/Login";
import { Register } from "@/pages/Register";
import { Dashboard } from "@/pages/Dashboard";
import { Queues } from "@/pages/Queues";
import { QueueDetail } from "@/pages/QueueDetail";
import { ConsumerDetail } from "@/pages/ConsumerDetail";
import { DeliveryDetail } from "@/pages/DeliveryDetail";
import { ApiKeys } from "@/pages/ApiKeys";
import { AdminUsers } from "@/pages/AdminUsers";
import { Search } from "@/pages/Search";
import { Profile } from "@/pages/Profile";
import { SdkDocs } from "@/pages/SdkDocs";
import { Activity } from "lucide-react";

function FullScreenLoader() {
  return (
    <div className="flex h-full items-center justify-center text-muted-foreground">
      <Activity className="animate-pulse" />
    </div>
  );
}

function Protected({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <FullScreenLoader />;
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  return <Layout>{children}</Layout>;
}

function AdminOnly({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (user?.role !== "admin") return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  const { loading, user } = useAuth();
  if (loading) return <FullScreenLoader />;

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/register" element={user ? <Navigate to="/" replace /> : <Register />} />

      <Route path="/" element={<Protected><Dashboard /></Protected>} />
      <Route path="/queues" element={<Protected><Queues /></Protected>} />
      <Route path="/queues/:queueId" element={<Protected><QueueDetail /></Protected>} />
      <Route path="/consumers/:consumerId" element={<Protected><ConsumerDetail /></Protected>} />
      <Route path="/deliveries/:deliveryId" element={<Protected><DeliveryDetail /></Protected>} />
      <Route path="/search" element={<Protected><Search /></Protected>} />
      <Route path="/profile" element={<Protected><Profile /></Protected>} />
      <Route path="/api-keys" element={<Protected><ApiKeys /></Protected>} />
      <Route path="/sdk" element={<Protected><SdkDocs /></Protected>} />
      <Route
        path="/admin/users"
        element={<Protected><AdminOnly><AdminUsers /></AdminOnly></Protected>}
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
