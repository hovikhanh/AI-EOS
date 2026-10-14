import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { RouterProvider, type createBrowserRouter } from "react-router";

type AppProps = {
  router: ReturnType<typeof createBrowserRouter>;
  queryClient: QueryClient;
};

export function App({ router, queryClient }: AppProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
