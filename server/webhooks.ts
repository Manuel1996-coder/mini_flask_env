import { DeliveryMethod } from '@shopify/shopify-api';
import express from 'express';

const router = express.Router();

// Create the router without depending on storage yet
export const gdprRoutes = router;

// Will be initialized by setupWebhooks
let shopifyClient: any;
let storageRef: any;

// Set up the module with dependencies from outside
export const initWebhooks = (shopifyApi: any, storage: any) => {
  shopifyClient = shopifyApi;
  storageRef = storage;
};

// Register webhook handlers
const handleAppUninstalled = async (topic: string, shop: string, webhookRequestBody: string) => {
  // Delete all sessions for the shop to cleanup after uninstallation
  await storageRef.deleteSessions([shop]);
  console.log(`App uninstalled by shop: ${shop}`);
};

const handleCustomersDataRequest = async (topic: string, shop: string, webhookRequestBody: string) => {
  // GDPR customer data request handler
  const payload = JSON.parse(webhookRequestBody);
  console.log(`Customer data request for shop ${shop}, customer ${payload.customer.id}`);
  
  // In a real implementation, you'd collect all customer data and send it back 
  // to Shopify. For this example, we'll just log it.
  return { success: true };
};

const handleCustomersRedact = async (topic: string, shop: string, webhookRequestBody: string) => {
  // GDPR customer data deletion request handler
  const payload = JSON.parse(webhookRequestBody);
  console.log(`Customer data redaction request for shop ${shop}, customer ${payload.customer.id}`);

  // In a real implementation, you'd remove this customer's data
  // For this example, we'll just log it
  return { success: true };
};

const handleShopRedact = async (topic: string, shop: string, webhookRequestBody: string) => {
  // GDPR shop data deletion request handler
  console.log(`Shop data redaction request for shop ${shop}`);
  
  // Delete all data for this shop
  await storageRef.deleteSessions([shop]);
  return { success: true };
};

// Register the webhooks when server starts
export const setupWebhooks = async (shop: string, accessToken: string) => {
  if (!shopifyClient) {
    console.error('Webhook module not initialized');
    return;
  }

  try {
    // Register required webhooks
    const webhookRegistrations = [
      {
        topic: 'APP_UNINSTALLED',
        path: '/webhooks/app-uninstalled',
        handler: handleAppUninstalled
      },
      {
        topic: 'CUSTOMERS_DATA_REQUEST',
        path: '/webhooks/customers-data-request',
        handler: handleCustomersDataRequest
      },
      {
        topic: 'CUSTOMERS_REDACT',
        path: '/webhooks/customers-redact',
        handler: handleCustomersRedact
      },
      {
        topic: 'SHOP_REDACT',
        path: '/webhooks/shop-redact',
        handler: handleShopRedact
      }
    ];

    // Register each webhook with Shopify
    for (const { topic, path, handler } of webhookRegistrations) {
      // Register webhook with Shopify
      const webhookResponse = await shopifyClient.webhooks.register({
        path,
        topic: topic as any,
        accessToken,
        shop,
        deliveryMethod: DeliveryMethod.Http
      });

      if (webhookResponse.success) {
        console.log(`Registered ${topic} webhook for ${shop}`);
      } else {
        console.error(`Failed to register ${topic} webhook:`, webhookResponse.result);
      }
    }
  } catch (error) {
    console.error('Error setting up webhooks:', error);
  }
};

// Webhook handler middleware
const verifyWebhook = async (req: express.Request, res: express.Response, next: express.NextFunction) => {
  if (!shopifyClient) {
    console.error('Webhook module not initialized');
    return res.status(500).send('Webhook module not initialized');
  }

  try {
    // Verify the webhook with Shopify
    const valid = await shopifyClient.webhooks.validate({
      rawBody: req.body ? JSON.stringify(req.body) : '',
      rawRequest: req,
      rawResponse: res
    });

    if (!valid) {
      console.error('Invalid webhook signature');
      return res.status(401).send('Invalid webhook signature');
    }
    
    next();
  } catch (error) {
    console.error('Error validating webhook:', error);
    return res.status(401).send('Invalid webhook');
  }
};

// App uninstalled webhook
router.post('/app-uninstalled', verifyWebhook, async (req, res) => {
  try {
    // Process the uninstall
    const shop = req.body.shop_domain;
    await handleAppUninstalled('APP_UNINSTALLED', shop, JSON.stringify(req.body));
    res.status(200).send('Webhook processed');
  } catch (error) {
    console.error('Error processing app uninstalled webhook:', error);
    if (!res.headersSent) {
      res.status(500).send('Error processing webhook');
    }
  }
});

// GDPR Data Request webhook
router.post('/customers-data-request', verifyWebhook, async (req, res) => {
  try {
    const shop = req.body.shop_domain;
    await handleCustomersDataRequest('CUSTOMERS_DATA_REQUEST', shop, JSON.stringify(req.body));
    res.status(200).send('GDPR data request will be processed');
  } catch (error) {
    console.error('Error processing GDPR data request webhook:', error);
    if (!res.headersSent) {
      res.status(500).send('Error processing webhook');
    }
  }
});

// GDPR Customer Redact webhook
router.post('/customers-redact', verifyWebhook, async (req, res) => {
  try {
    const shop = req.body.shop_domain;
    await handleCustomersRedact('CUSTOMERS_REDACT', shop, JSON.stringify(req.body));
    res.status(200).send('GDPR customer redaction will be processed');
  } catch (error) {
    console.error('Error processing GDPR customer redaction webhook:', error);
    if (!res.headersSent) {
      res.status(500).send('Error processing webhook');
    }
  }
});

// GDPR Shop Redact webhook
router.post('/shop-redact', verifyWebhook, async (req, res) => {
  try {
    const shop = req.body.shop_domain;
    await handleShopRedact('SHOP_REDACT', shop, JSON.stringify(req.body));
    res.status(200).send('GDPR shop redaction will be processed');
  } catch (error) {
    console.error('Error processing GDPR shop redaction webhook:', error);
    if (!res.headersSent) {
      res.status(500).send('Error processing webhook');
    }
  }
});

export default setupWebhooks; 