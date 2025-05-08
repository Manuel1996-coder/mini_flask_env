import React from 'react';
import { Card, Button, Spinner, Text } from '@shopify/polaris';
import styled from '@emotion/styled';

interface RecommendationCardProps {
  recommendation: string;
  timestamp: string;
  isLoading: boolean;
  onRefresh: () => void;
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

const RecommendationContent = styled.div`
  display: flex;
  margin-bottom: 24px;
  gap: 16px;
`;

const RecommendationIcon = styled.div`
  color: var(--p-action-primary);
  flex-shrink: 0;
`;

const RecommendationText = styled.div`
  flex: 1;
`;

const RecommendationMain = styled.div`
  margin: 12px 0;
  line-height: 1.6;
`;

const RecommendationTimestamp = styled.div`
  margin-top: 8px;
`;

const RecommendationActions = styled.div`
  margin-top: auto;
  align-self: flex-start;
`;

const RecommendationCard: React.FC<RecommendationCardProps> = ({
  recommendation,
  timestamp,
  isLoading,
  onRefresh
}) => {
  // Format the timestamp for display
  const formatTimestamp = (timestamp: string) => {
    if (!timestamp) return '';
    
    const date = new Date(timestamp);
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };
  
  return (
    <Card sectioned title="Handlungsempfehlungen">
      <CardContent>
        {isLoading ? (
          <LoadingContainer>
            <Spinner accessibilityLabel="Loading recommendation" size="large" />
            <Text>Generating recommendation...</Text>
          </LoadingContainer>
        ) : (
          <>
            <RecommendationContent>
              <RecommendationIcon>
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
                  <path d="M12 3.21l-8 8V21h16V11.21l-8-8zM18 19H6v-7.79l6-6 6 6V19z" />
                  <path d="M10 15h4v4h-4z" />
                </svg>
              </RecommendationIcon>
              <RecommendationText>
                <Text variant="bodyLg" fontWeight="semibold">
                  AI-powered Growth Recommendation
                </Text>
                <RecommendationMain>
                  {recommendation || 'No recommendation available. Click "Generate" to create one.'}
                </RecommendationMain>
                {timestamp && (
                  <RecommendationTimestamp>
                    <Text variant="bodySm" color="subdued">
                      Last updated: {formatTimestamp(timestamp)}
                    </Text>
                  </RecommendationTimestamp>
                )}
              </RecommendationText>
            </RecommendationContent>
            
            <RecommendationActions>
              <Button onClick={onRefresh} primary>
                Generate New Recommendation
              </Button>
            </RecommendationActions>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default RecommendationCard; 