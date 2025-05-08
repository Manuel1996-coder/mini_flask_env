import React, { useState, useEffect, useCallback } from 'react';
import { TitleBar, Toast } from '@shopify/app-bridge-react';
import RecommendationCard from '../components/RecommendationCard';
import PriceOptimizerCard from '../components/PriceOptimizerCard';
import { useAppBridge } from '@shopify/app-bridge-react';
import { authenticatedFetch } from '@shopify/app-bridge-utils';
import '../styles/styles.css';

const Dashboard: React.FC = () => {
  const app = useAppBridge();
  const fetch = authenticatedFetch(app);
  
  const [recommendation, setRecommendation] = useState<string>('');
  const [recommendationTimestamp, setRecommendationTimestamp] = useState<string>('');
  const [products, setProducts] = useState<any[]>([]);
  const [optimizedProducts, setOptimizedProducts] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [toast, setToast] = useState({ active: false, content: '', error: false });
  
  // Function to fetch products from Shopify GraphQL API
  const fetchProducts = useCallback(async () => {
    try {
      const response = await fetch('/api/products');
      const data = await response.json();
      
      if (data.products) {
        setProducts(data.products);
      }
    } catch (error) {
      console.error('Error fetching products:', error);
      showToast('Failed to load products', true);
    }
  }, [fetch]);
  
  // Function to generate a recommendation
  const generateRecommendation = useCallback(async () => {
    setIsLoading(true);
    
    try {
      // Mock tracking data for demo purposes
      const trackingData = {
        pageviews: [450, 520, 480, 630, 580, 520, 680],
        visitors: [320, 380, 350, 450, 420, 380, 480],
        conversions: [12, 18, 15, 22, 25, 20, 28],
        productViews: {
          'product1': 120,
          'product2': 85,
          'product3': 210
        }
      };
      
      const response = await fetch('/api/recommendations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ trackingData }),
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setRecommendation(data.recommendation);
        setRecommendationTimestamp(data.timestamp);
        showToast('New recommendation generated');
      } else {
        showToast(`Error: ${data.error || 'Failed to generate recommendation'}`, true);
      }
    } catch (error) {
      console.error('Error generating recommendation:', error);
      showToast('Failed to generate recommendation', true);
    } finally {
      setIsLoading(false);
    }
  }, [fetch]);
  
  // Function to optimize product prices
  const optimizePrices = useCallback(async () => {
    if (products.length === 0) {
      showToast('No products available to optimize', true);
      return;
    }
    
    setIsLoading(true);
    
    try {
      const response = await fetch('/api/price-optimize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          products: products.map(p => ({
            id: p.id,
            title: p.title,
            price: parseFloat(p.variants[0]?.price || '0')
          }))
        }),
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setOptimizedProducts(data.products);
        showToast('Price optimization complete');
      } else {
        showToast(`Error: ${data.error || 'Failed to optimize prices'}`, true);
      }
    } catch (error) {
      console.error('Error optimizing prices:', error);
      showToast('Failed to optimize prices', true);
    } finally {
      setIsLoading(false);
    }
  }, [fetch, products]);
  
  // Function to apply price updates
  const applyPriceUpdate = useCallback(async (productId: string, variantId: string, price: number) => {
    setIsLoading(true);
    
    try {
      const response = await fetch('/api/update-product-price', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ productId, variantId, price }),
      });
      
      const data = await response.json();
      
      if (response.ok) {
        showToast('Price updated successfully');
        // Refresh product list
        fetchProducts();
      } else {
        showToast(`Error: ${data.error || 'Failed to update price'}`, true);
      }
    } catch (error) {
      console.error('Error updating price:', error);
      showToast('Failed to update price', true);
    } finally {
      setIsLoading(false);
    }
  }, [fetch, fetchProducts]);
  
  // Helper function to show toast messages
  const showToast = (content: string, error = false) => {
    setToast({ active: true, content, error });
    
    // Auto dismiss toast after 4 seconds
    setTimeout(() => {
      setToast(prev => ({ ...prev, active: false }));
    }, 4000);
  };
  
  // Load products on initial render
  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);
  
  // Generate initial recommendation
  useEffect(() => {
    generateRecommendation();
  }, [generateRecommendation]);
  
  return (
    <div className="dashboard-container">
      <TitleBar title="ShopPulseAI Dashboard" />
      
      {/* Toast notification */}
      {toast.active && (
        <Toast
          content={toast.content}
          error={toast.error}
          onDismiss={() => setToast(prev => ({ ...prev, active: false }))}
        />
      )}
      
      <div className="dashboard-content">
        <h1 className="dashboard-title">Dashboard</h1>
        
        <div className="dashboard-cards">
          {/* Recommendation Card */}
          <RecommendationCard 
            recommendation={recommendation} 
            timestamp={recommendationTimestamp}
            isLoading={isLoading}
            onRefresh={generateRecommendation}
          />
          
          {/* Price Optimizer Card */}
          <PriceOptimizerCard 
            products={products}
            optimizedProducts={optimizedProducts}
            isLoading={isLoading}
            onOptimize={optimizePrices}
            onApplyPrice={applyPriceUpdate}
          />
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 