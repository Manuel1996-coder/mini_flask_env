import { rest } from 'msw';

export const handlers = [
  // Mock the recommendations endpoint
  rest.post('/api/recommendations', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        recommendation: 'Based on your traffic patterns, you should consider implementing abandoned cart recovery emails to capture the 15% of customers who add items to cart but don\'t complete checkout. This could potentially increase your revenue by up to 10%.',
        timestamp: new Date().toISOString()
      })
    );
  }),
  
  // Mock the price optimization endpoint
  rest.post('/api/price-optimize', (req, res, ctx) => {
    // Extract products from the request body
    const { products } = req.body as { products: any[] };
    
    // Generate mock price suggestions
    const optimizedProducts = products.map(product => ({
      ...product,
      suggestedPrice: Math.round((parseFloat(product.price) * 1.05) * 100) / 100, // 5% increase
      reasoning: 'Based on market analysis, a slight price increase is recommended to maximize revenue while maintaining competitiveness.'
    }));
    
    return res(
      ctx.status(200),
      ctx.json({
        products: optimizedProducts,
        timestamp: new Date().toISOString()
      })
    );
  }),
  
  // Mock the product fetch endpoint
  rest.get('/api/products', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        products: [
          {
            id: 'gid://shopify/Product/1',
            title: 'Classic T-Shirt',
            variants: [
              {
                id: 'gid://shopify/ProductVariant/1',
                price: '19.99'
              }
            ]
          },
          {
            id: 'gid://shopify/Product/2',
            title: 'Premium Hoodie',
            variants: [
              {
                id: 'gid://shopify/ProductVariant/2',
                price: '49.99'
              }
            ]
          },
          {
            id: 'gid://shopify/Product/3',
            title: 'Denim Jeans',
            variants: [
              {
                id: 'gid://shopify/ProductVariant/3',
                price: '79.99'
              }
            ]
          }
        ]
      })
    );
  }),
  
  // Mock the price update endpoint
  rest.post('/api/update-product-price', (req, res, ctx) => {
    const { productId, variantId, price } = req.body as { 
      productId: string; 
      variantId: string; 
      price: number;
    };
    
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        variant: {
          id: variantId,
          price: price.toString()
        }
      })
    );
  })
]; 