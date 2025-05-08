import { test, expect } from '@playwright/test';

// Mock Shopify app query parameters
const mockShopParams = '?shop=test-store.myshopify.com&host=test-host';

test.describe('ShopPulseAI App', () => {
  test('should load the dashboard', async ({ page }) => {
    // Navigate to the app with mock shop parameters
    await page.goto(`http://localhost:5173/dashboard${mockShopParams}`);
    
    // Check if the page title is correct
    await expect(page).toHaveTitle(/ShopPulseAI/);
    
    // Verify dashboard elements are visible
    await expect(page.locator('h1.dashboard-title')).toBeVisible();
    await expect(page.locator('text=Handlungsempfehlungen')).toBeVisible();
    await expect(page.locator('text=Preisoptimierung')).toBeVisible();
  });

  test('should generate a recommendation', async ({ page }) => {
    // Navigate to the app
    await page.goto(`http://localhost:5173/dashboard${mockShopParams}`);
    
    // Click the generate recommendation button
    await page.locator('button:has-text("Generate New Recommendation")').click();
    
    // Wait for loading spinner to appear and then disappear
    await page.locator('.loading-container').waitFor({ state: 'visible' });
    await page.locator('.loading-container').waitFor({ state: 'hidden', timeout: 10000 });
    
    // Verify that a recommendation is displayed
    const recommendationText = page.locator('.recommendation-main');
    await expect(recommendationText).not.toHaveText('No recommendation available');
  });

  test('should optimize product prices', async ({ page }) => {
    // Navigate to the app
    await page.goto(`http://localhost:5173/dashboard${mockShopParams}`);
    
    // Click the optimize prices button
    await page.locator('button:has-text("Optimize Prices")').click();
    
    // Wait for loading spinner to appear and then disappear
    await page.locator('.loading-container').waitFor({ state: 'visible' });
    await page.locator('.loading-container').waitFor({ state: 'hidden', timeout: 10000 });
    
    // Verify that price data is displayed
    await expect(page.locator('text=Product')).toBeVisible();
    await expect(page.locator('text=Current Price')).toBeVisible();
    await expect(page.locator('text=Suggested Price')).toBeVisible();
  });
});

// Test API endpoints directly
test.describe('API Endpoints', () => {
  test('recommendations endpoint should return valid data', async ({ request }) => {
    // Post to the recommendations endpoint with mock data
    const response = await request.post('http://localhost:3000/api/recommendations', {
      headers: {
        'Content-Type': 'application/json',
      },
      data: {
        trackingData: {
          pageviews: [100, 150, 200],
          visitors: [50, 75, 100]
        }
      }
    });
    
    // Verify response is successful
    expect(response.ok()).toBeTruthy();
    
    // Verify response has the expected format
    const data = await response.json();
    expect(data).toHaveProperty('recommendation');
    expect(data).toHaveProperty('timestamp');
  });

  test('price-optimize endpoint should return valid data', async ({ request }) => {
    // Post to the price optimization endpoint with mock data
    const response = await request.post('http://localhost:3000/api/price-optimize', {
      headers: {
        'Content-Type': 'application/json',
      },
      data: {
        products: [
          { id: 'prod1', title: 'Test Product 1', price: 19.99 },
          { id: 'prod2', title: 'Test Product 2', price: 29.99 }
        ]
      }
    });
    
    // Verify response is successful
    expect(response.ok()).toBeTruthy();
    
    // Verify response has the expected format
    const data = await response.json();
    expect(data).toHaveProperty('products');
    expect(data).toHaveProperty('timestamp');
    expect(data.products).toHaveLength(2);
    expect(data.products[0]).toHaveProperty('suggestedPrice');
    expect(data.products[0]).toHaveProperty('reasoning');
  });
}); 