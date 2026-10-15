import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { RouterProvider, type createBrowserRouter } from "react-router";
import { I18nProvider } from "./i18n";

type AppProps = {
  router: ReturnType<typeof createBrowserRouter>;
  queryClient: QueryClient;
};

export function App({ router, queryClient }: AppProps) {
  return (
    <I18nProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </I18nProvider>
  );
}
