import { Outlet } from "react-router-dom";
import { AuthProvider } from "@/context/AuthProvider";

export function RootLayout() {
  return (
    <AuthProvider>
      <Outlet />
    </AuthProvider>
  );
}
