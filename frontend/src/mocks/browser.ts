import { setupWorker } from 'msw';
import { handlers } from './handlers';

// This configures a Service Worker with the given request handlers
export const worker = setupWorker(...handlers);

// Initialize the MSW worker when in development
if (process.env.NODE_ENV === 'development') {
  console.log('MSW initialized in development mode');
} 