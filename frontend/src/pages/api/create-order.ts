import type { NextApiRequest, NextApiResponse } from 'next';
import Razorpay from 'razorpay';
import { BILLING_PLANS, type BillingPlanCode } from '@/lib/razorpay';

interface BackendUserResponse {
  id: string;
  email: string;
}

function jsonError(res: NextApiResponse, statusCode: number, code: string, message: string) {
  return res.status(statusCode).json({ code, detail: message });
}

function getServerConfig() {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, '');
  const keyId = process.env.RAZORPAY_KEY_ID;
  const keySecret = process.env.RAZORPAY_KEY_SECRET;
  const internalSecret = process.env.BILLING_INTERNAL_API_SECRET;

  if (!apiBase || !keyId || !keySecret || !internalSecret) {
    throw new Error('Billing environment variables are not configured.');
  }

  return { apiBase, keyId, keySecret, internalSecret };
}

function getAuthHeader(req: NextApiRequest): string {
  const authorization = req.headers.authorization;
  if (!authorization?.startsWith('Bearer ')) {
    throw new Error('Authentication is required.');
  }
  return authorization;
}

async function fetchCurrentUser(apiBase: string, authorization: string): Promise<BackendUserResponse> {
  const response = await fetch(`${apiBase}/api/v1/users/me`, {
    headers: { Authorization: authorization },
  });

  if (!response.ok) {
    throw new Error('Unable to resolve the current user.');
  }

  return response.json() as Promise<BackendUserResponse>;
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return jsonError(res, 405, 'method_not_allowed', 'Only POST is supported.');
  }

  try {
    const { apiBase, keyId, keySecret, internalSecret } = getServerConfig();
    const authorization = getAuthHeader(req);
    const body = typeof req.body === 'string' ? JSON.parse(req.body) as { planCode?: BillingPlanCode } : req.body as { planCode?: BillingPlanCode };
    const planCode = body.planCode;

    if (!planCode || !(planCode in BILLING_PLANS)) {
      return jsonError(res, 400, 'invalid_plan', 'A valid billing plan is required.');
    }

    const plan = BILLING_PLANS[planCode];
    const user = await fetchCurrentUser(apiBase, authorization);
    const razorpay = new Razorpay({ key_id: keyId, key_secret: keySecret });
    const receipt = `pdforbit_${plan.code.toLowerCase()}_${Date.now()}`;
    const order = await razorpay.orders.create({
      amount: plan.amountPaise,
      currency: 'INR',
      receipt,
      notes: {
        user_id: user.id,
        user_email: user.email,
        plan_code: plan.code,
        subscription_interval: plan.interval,
      },
    });

    const registerResponse = await fetch(`${apiBase}/api/v1/billing/internal/order-created`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-API-Secret': internalSecret,
      },
      body: JSON.stringify({
        user_id: user.id,
        plan_code: plan.code,
        razorpay_order_id: order.id,
        receipt,
        amount_paise: plan.amountPaise,
        currency: 'INR',
      }),
    });

    if (!registerResponse.ok) {
      return jsonError(res, 502, 'billing_register_failed', 'Unable to persist the pending payment order.');
    }

    return res.status(200).json({
      orderId: order.id,
      keyId,
      currency: 'INR',
      amount: plan.amountPaise,
      planCode: plan.code,
      planName: plan.name,
      description: plan.description,
      prefill: {
        email: user.email,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unable to create Razorpay order.';
    return jsonError(res, 500, 'create_order_failed', message);
  }
}
