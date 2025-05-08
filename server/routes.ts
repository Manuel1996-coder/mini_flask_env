import express from 'express';
import { createClient } from './auth';
import openai from './openai';

// Typ-Definition für GraphQL-Antwort
interface GraphQLResponse {
  body: {
    data?: {
      productVariantUpdate?: {
        productVariant?: {
          id: string;
          price: string;
        };
        userErrors?: Array<{
          field: string;
          message: string;
        }>;
      };
    };
    errors?: any[];
  };
}

const router = express.Router();

// Feature A: Handlungsempfehlungen endpoint
router.post('/recommendations', async (req, res) => {
  try {
    // Get the authenticated session from middleware
    const session = (req as any).shopifySession;
    
    if (!session) {
      return res.status(401).json({ error: 'Unauthorized' });
    }
    
    // Get tracking data from request body
    const { trackingData } = req.body;
    
    if (!trackingData) {
      return res.status(400).json({ error: 'Missing tracking data' });
    }
    
    // Generate recommendation using OpenAI
    const recommendation = await openai.generateRecommendation(trackingData);
    
    // Return the recommendation with timestamp
    return res.status(200).json({
      recommendation,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error generating recommendation:', error);
    return res.status(500).json({ error: 'Failed to generate recommendation' });
  }
});

// Feature B: Preisoptimierung endpoint
router.post('/price-optimize', async (req, res) => {
  try {
    // Get the authenticated session from middleware
    const session = (req as any).shopifySession;
    
    if (!session) {
      return res.status(401).json({ error: 'Unauthorized' });
    }
    
    // Get products from request body
    const { products } = req.body;
    
    if (!products || !Array.isArray(products)) {
      return res.status(400).json({ error: 'Missing or invalid products array' });
    }
    
    // Validate product data
    const validProducts = products.filter(p => 
      p && typeof p === 'object' && p.id && p.title && typeof p.price === 'number'
    );
    
    if (validProducts.length === 0) {
      return res.status(400).json({ 
        error: 'No valid products found. Each product must have id, title, and price properties.' 
      });
    }
    
    // Generate price optimization suggestions
    const optimizedProducts = await openai.optimizePrices(validProducts);
    
    return res.status(200).json({
      products: optimizedProducts,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error optimizing prices:', error);
    return res.status(500).json({ error: 'Failed to optimize prices' });
  }
});

// GraphQL endpoint for applying price updates
router.post('/update-product-price', async (req, res) => {
  try {
    // Get the authenticated session from middleware
    const session = (req as any).shopifySession;
    
    if (!session) {
      return res.status(401).json({ error: 'Unauthorized' });
    }
    
    const { productId, variantId, price } = req.body;
    
    if (!productId || !variantId || typeof price !== 'number') {
      return res.status(400).json({ 
        error: 'Missing required fields: productId, variantId, and price are required' 
      });
    }
    
    try {
      // Create GraphQL client
      const client = await createClient(session);
      
      // Update variant price using GraphQL
      const response = await client.query({
        data: {
          query: `
            mutation productVariantUpdate($input: ProductVariantInput!) {
              productVariantUpdate(input: $input) {
                productVariant {
                  id
                  price
                }
                userErrors {
                  field
                  message
                }
              }
            }
          `,
          variables: {
            input: {
              id: variantId,
              price: price.toString()
            }
          }
        }
      }) as GraphQLResponse;
      
      // Sichere Überprüfung, ob die erwarteten Daten vorhanden sind
      if (!response?.body?.data?.productVariantUpdate) {
        console.error('Unexpected GraphQL response format:', response);
        return res.status(500).json({ error: 'Invalid response from Shopify API' });
      }
      
      const result = response.body.data.productVariantUpdate;
      
      // Überprüfe, ob Fehler zurückgegeben wurden
      if (result.userErrors && result.userErrors.length > 0) {
        return res.status(400).json({ 
          error: 'Failed to update product price',
          details: result.userErrors 
        });
      }
      
      // Überprüfe, ob das productVariant-Objekt existiert
      if (!result.productVariant) {
        return res.status(500).json({ error: 'No product variant data returned from API' });
      }
      
      return res.status(200).json({
        success: true,
        variant: result.productVariant
      });
    } catch (graphQLError: unknown) {
      console.error('GraphQL error:', graphQLError);
      const errorMessage = graphQLError instanceof Error ? graphQLError.message : 'Unknown GraphQL error';
      return res.status(500).json({ error: 'Error in GraphQL request', details: errorMessage });
    }
  } catch (error) {
    console.error('Error updating product price:', error);
    return res.status(500).json({ error: 'Failed to update product price' });
  }
});

export default router; 