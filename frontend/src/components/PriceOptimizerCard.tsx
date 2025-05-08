import React, { useState } from 'react';
import { Card, Button, DataTable, Spinner, Text, Badge } from '@shopify/polaris';
import styled from '@emotion/styled';

interface PriceOptimizerCardProps {
  products: any[];
  optimizedProducts: any[];
  isLoading: boolean;
  onOptimize: () => void;
  onApplyPrice: (productId: string, variantId: string, price: number) => void;
}

// Styled components
const CardContent = styled.div`
  min-height: 200px;
  display: flex;
  flex-direction: column;
`;

const LoadingContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  gap: 16px;
`;

const TableContainer = styled.div`
  margin-bottom: 20px;
  overflow-x: auto;
`;

const ProductInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
`;

const ProductTitle = styled.span`
  font-weight: 500;
`;

const SuggestedPrice = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
`;

const PriceReasoning = styled.div`
  font-size: 0.875rem;
  color: var(--p-text-subdued);
`;

const EmptyState = styled.div`
  padding: 12px 0;
  text-align: center;
  grid-column: 1 / -1;
`;

const OptimizerActions = styled.div`
  display: flex;
  gap: 12px;
  margin-top: auto;
`;

const PriceOptimizerCard: React.FC<PriceOptimizerCardProps> = ({
  products,
  optimizedProducts,
  isLoading,
  onOptimize,
  onApplyPrice
}) => {
  const [selectedProducts, setSelectedProducts] = useState<string[]>([]);
  
  // Toggle product selection
  const toggleProductSelection = (productId: string) => {
    setSelectedProducts(prev => 
      prev.includes(productId)
        ? prev.filter(id => id !== productId)
        : [...prev, productId]
    );
  };
  
  // Format price with currency
  const formatPrice = (price: number | string) => {
    const numericPrice = typeof price === 'string' ? parseFloat(price) : price;
    return `$${numericPrice.toFixed(2)}`;
  };
  
  // Calculate price difference as percentage
  const calculatePriceDiff = (original: number, suggested: number) => {
    if (original === 0) return 0;
    return ((suggested - original) / original) * 100;
  };
  
  // Prepare data table rows
  const rows = optimizedProducts.length > 0
    ? optimizedProducts.map(product => {
        const isSelected = selectedProducts.includes(product.id);
        const originalPrice = parseFloat(product.price);
        const suggestedPrice = parseFloat(product.suggestedPrice);
        const priceDiff = calculatePriceDiff(originalPrice, suggestedPrice);
        const isPriceIncrease = priceDiff > 0;
        
        return [
          <ProductInfo>
            <input 
              type="checkbox" 
              checked={isSelected}
              onChange={() => toggleProductSelection(product.id)}
            />
            <ProductTitle>{product.title}</ProductTitle>
          </ProductInfo>,
          formatPrice(originalPrice),
          <SuggestedPrice>
            {formatPrice(suggestedPrice)}
            <Badge status={isPriceIncrease ? 'success' : 'warning'}>
              {priceDiff > 0 ? '+' : ''}{priceDiff.toFixed(1)}%
            </Badge>
          </SuggestedPrice>,
          <PriceReasoning>{product.reasoning}</PriceReasoning>,
          <Button 
            size="slim"
            onClick={() => onApplyPrice(product.id, product.id, suggestedPrice)}
          >
            Apply
          </Button>
        ];
      })
    : [
        [
          <EmptyState>
            <Text color="subdued">
              No optimized products. Click "Optimize Prices" to generate suggestions.
            </Text>
          </EmptyState>,
          '',
          '',
          '',
          ''
        ]
      ];
  
  // Apply selected prices in bulk
  const applySelectedPrices = () => {
    if (selectedProducts.length === 0) return;
    
    optimizedProducts
      .filter(product => selectedProducts.includes(product.id))
      .forEach(product => {
        onApplyPrice(product.id, product.id, parseFloat(product.suggestedPrice));
      });
    
    // Clear selection after applying
    setSelectedProducts([]);
  };
  
  return (
    <Card sectioned title="Preisoptimierung">
      <CardContent>
        {isLoading ? (
          <LoadingContainer>
            <Spinner accessibilityLabel="Loading price optimization" size="large" />
            <Text>Optimizing prices...</Text>
          </LoadingContainer>
        ) : (
          <>
            <TableContainer>
              <DataTable
                columnContentTypes={['text', 'text', 'text', 'text', 'text']}
                headings={[
                  'Product',
                  'Current Price',
                  'Suggested Price',
                  'Reasoning',
                  'Action'
                ]}
                rows={rows}
              />
            </TableContainer>
            
            <OptimizerActions>
              <Button onClick={onOptimize} primary>
                Optimize Prices
              </Button>
              
              {selectedProducts.length > 0 && (
                <Button onClick={applySelectedPrices}>
                  Apply Selected ({selectedProducts.length})
                </Button>
              )}
            </OptimizerActions>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default PriceOptimizerCard; 