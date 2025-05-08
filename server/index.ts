// Load environment variables first
import dotenv from 'dotenv';
dotenv.config();
console.log('Environment variables loaded');

// Other imports
import express from 'express';
import cors from 'cors';
import path from 'path';
import { setupAuth } from './auth';
import apiRoutes from './routes';

// Create Express app
const app = express();

// Use a different port if the configured port is in use
// Try using PORT from env, fallback to 8081, then try 3000 if needed
let PORT = parseInt(process.env.PORT || '8081');

// Middleware
app.use(express.json());
app.use(cors());

// Set up Shopify authentication
setupAuth(app);

// API routes
app.use('/api', apiRoutes);

// In production, serve the static frontend files
if (process.env.NODE_ENV === 'production') {
  app.use(express.static(path.join(__dirname, '../frontend/dist')));
  
  // Handle all other routes by serving the index.html
  app.get('*', (_req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/dist', 'index.html'));
  });
}

// Start the server with error handling for port in use
const startServer = (port: number): void => {
  app.listen(port, () => {
    console.log(`Server running on port ${port}`);
    console.log(`- Local: http://localhost:${port}`);
    console.log(`- Environment: ${process.env.NODE_ENV || 'development'}`);
    
    if (process.env.RAILWAY_STATIC_URL) {
      console.log(`- Railway URL: ${process.env.RAILWAY_STATIC_URL}`);
    }
  }).on('error', (err: any) => {
    if (err.code === 'EADDRINUSE') {
      console.log(`Port ${port} is already in use, trying port ${port + 1}`);
      startServer(port + 1);
    } else {
      console.error('Server startup error:', err);
    }
  });
};

// Start with the configured port
startServer(PORT);

export default app; 