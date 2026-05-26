import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { createRoot } from 'react-dom/client';
import { Navigate, RouterProvider, createBrowserRouter } from 'react-router-dom';
import { AppShell } from './components/app-shell';
import { BacktestsPage } from './pages/backtests-page';
import { FactorsPage } from './pages/factors-page';
import { JobsPage } from './pages/jobs-page';
import { LifecyclePage } from './pages/lifecycle-page';
import { NotFoundPage } from './pages/not-found-page';
import { PaperPage } from './pages/paper-page';
import { RiskPage } from './pages/risk-page';
import { RuntimePage } from './pages/runtime-page';
import { StrategiesPage } from './pages/strategies-page';
import './styles/main.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/strategies" replace /> },
      { path: 'strategies', element: <StrategiesPage /> },
      { path: 'lifecycle', element: <LifecyclePage /> },
      { path: 'backtests', element: <BacktestsPage /> },
      { path: 'runtime', element: <RuntimePage /> },
      { path: 'jobs', element: <JobsPage /> },
      { path: 'paper', element: <PaperPage /> },
      { path: 'risk', element: <RiskPage /> },
      { path: 'factors', element: <FactorsPage /> },
      { path: 'settings', element: <NotFoundPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>,
);
