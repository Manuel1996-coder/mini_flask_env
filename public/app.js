// Simple JavaScript file to test MIME type handling
document.addEventListener('DOMContentLoaded', function() {
  console.log('ShopPulseAI app.js loaded successfully');
  
  // Add this script to pages to verify proper loading
  const appElement = document.createElement('div');
  appElement.id = 'app-loaded-indicator';
  appElement.style.display = 'none';
  appElement.dataset.status = 'loaded';
  document.body.appendChild(appElement);
}); 