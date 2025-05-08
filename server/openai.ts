import OpenAI from 'openai';

// Default mock API key for development if none is provided
const DEFAULT_OPENAI_API_KEY = 'dummy_openai_key';

// Initialize the OpenAI client with API key from environment variables, fallback to dummy key in dev
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY || DEFAULT_OPENAI_API_KEY,
});

// Check if using dummy key and warn in console
if (!process.env.OPENAI_API_KEY) {
  console.warn('Warning: Using dummy OpenAI API key. OpenAI features will return mock data.');
}

// Define types for our recommendation functions
interface TrackingData {
  pageviews: number[];
  visitors: number[];
  conversions?: number[];
  productViews?: Record<string, number>;
  [key: string]: any;
}

interface Product {
  id: string;
  title: string;
  price: number;
  [key: string]: any;
}

/**
 * Generate recommendations based on tracking data
 * @param trackingData Analytics data from the merchant's store
 * @returns A recommendation string with the most impactful action
 */
export const generateRecommendation = async (trackingData: TrackingData): Promise<string> => {
  try {
    // If using dummy key, return mock data to avoid OpenAI API errors
    if (!process.env.OPENAI_API_KEY) {
      return "Based on your decreasing conversion rate, optimize your product pages with improved product descriptions and high-quality images. Add social proof by incorporating more customer reviews, and consider offering a limited-time discount to boost conversions.";
    }
    
    const prompt = `Based on the following tracking data from a Shopify store, suggest the single most impactful next action for the merchant. Be specific, actionable, and concise:
    
Tracking Data:
${JSON.stringify(trackingData, null, 2)}

Your recommendation (max 150 words):`;

    const response = await openai.chat.completions.create({
      model: 'gpt-4o',
      messages: [
        { role: 'system', content: 'You are a Shopify ecommerce growth expert focusing on actionable insights.' },
        { role: 'user', content: prompt }
      ],
      max_tokens: 300,
      temperature: 0.7,
    });

    return response.choices[0]?.message?.content || 'No recommendation generated';
  } catch (error) {
    console.error('Error generating recommendation with OpenAI:', error);
    // Return fallback recommendation in case of API error
    return 'Consider optimizing your product pages with more detailed descriptions and high-quality images to improve conversion rates.';
  }
};

/**
 * Generate price optimization suggestions for products
 * @param products Array of products with current prices
 * @returns Array of products with suggested prices and reasoning
 */
export const optimizePrices = async (products: Product[]): Promise<Array<Product & { suggestedPrice: number, reasoning: string }>> => {
  try {
    // If using dummy key, return mock data to avoid OpenAI API errors
    if (!process.env.OPENAI_API_KEY) {
      return products.map(product => ({
        ...product,
        suggestedPrice: Math.round(product.price * 1.1 * 100) / 100, // 10% price increase
        reasoning: "Based on market analysis, a slight price increase would maximize revenue while maintaining competitive positioning."
      }));
    }
    
    const prompt = `As a pricing optimization expert for Shopify stores, analyze these products and suggest optimal pricing to maximize revenue while staying competitive:
    
Products:
${JSON.stringify(products, null, 2)}

For each product, provide:
1. A suggested price (only the number)
2. A brief reasoning (1-2 sentences max)

Your response should be valid JSON in exactly this format:
[
  {
    "id": "product1",
    "suggestedPrice": 19.99,
    "reasoning": "Brief explanation"
  },
  ...
]`;

    const response = await openai.chat.completions.create({
      model: 'gpt-4o',
      messages: [
        { role: 'system', content: 'You are a pricing optimization expert for ecommerce stores.' },
        { role: 'user', content: prompt }
      ],
      max_tokens: 800,
      temperature: 0.3,
    });

    const content = response.choices[0]?.message?.content || '[]';
    
    // Parse the response and merge with original product data
    try {
      const suggestions = JSON.parse(content);
      return products.map(product => {
        const suggestion = suggestions.find((s: any) => s.id === product.id);
        return {
          ...product,
          suggestedPrice: suggestion?.suggestedPrice || product.price,
          reasoning: suggestion?.reasoning || 'No optimization suggestion available.'
        };
      });
    } catch (parseError) {
      console.error('Error parsing OpenAI response:', parseError);
      // Return original products with default suggestions
      return products.map(product => ({
        ...product,
        suggestedPrice: product.price,
        reasoning: 'Unable to generate price optimization.'
      }));
    }
  } catch (error) {
    console.error('Error optimizing prices with OpenAI:', error);
    // Return original products with default suggestions
    return products.map(product => ({
      ...product,
      suggestedPrice: product.price,
      reasoning: 'Unable to generate price optimization due to an error.'
    }));
  }
};

export default {
  generateRecommendation,
  optimizePrices
}; 