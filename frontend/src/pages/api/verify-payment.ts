import { createHmac, timingSafeEqual } from 'crypto';
import type { NextApiRequest, NextApiResponse } from 'next';
import Razorpay from 'razorpay';
import { BILLING_PLANS, type BillingPlanCode } from '@/lib/razorpay';

interface BackendUserResponse {
  id: string;
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

async function fetchCurrentUser(apiBase: string, authorization: string): Promise<BackendUserResponse> {
  const response = await fetch(`${apiBase}/api/v1/users/me`, {
    headers: { Authorization: authorization },
  });

  if (!response.ok) {
    throw new Error('Unable to resolve the current user.');
  }

  return response.json() as Promise<BackendUserResponse>;
}

function verifySignature(orderId: string, paymentId: string, signature: string, secret: string): boolean {
  const expected = createHmac('sha256', secret).update(`${orderId}|${paymentId}`).digest('hex');
  const expectedBuffer = Buffer.from(expected, 'utf8');
  const actualBuffer = Buffer.from(signature, 'utf8');

  if (expectedBuffer.length !== actualBuffer.length) {
    return false;
  }

  return timingSafeEqual(expectedBuffer, actualBuffer);
}

function mapPaymentStatus(status: string): 'authorized' | 'captured' {
  if (status === 'captured') {
    return 'captured';
  }

  if (status === 'authorized') {
    return 'authorized';
  }

  throw new Error(`Unexpected Razorpay payment status: ${status}`);
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return jsonError(res, 405, 'method_not_allowed', 'Only POST is supported.');
  }

  try {
    const { apiBase, keyId, keySecret, internalSecret } = getServerConfig();
    const authorization = req.headers.authorization;

    if (!authorization?.startsWith('Bearer ')) {
      return jsonError(res, 401, 'authentication_required', 'Authentication is required.');
    }

    const body = typeof req.body === 'string'
      ? JSON.parse(req.body) as {
          planCode?: BillingPlanCode;
          razorpay_order_id?: string;
          razorpay_payment_id?: string;
          razorpay_signature?: string;
        }
      : req.body as {
          planCode?: BillingPlanCode;
          razorpay_order_id?: string;
          razorpay_payment_id?: string;
          razorpay_signature?: string;
        };

    const planCode = body.planCode;
    const orderId = body.razorpay_order_id;
    const paymentId = body.razorpay_payment_id;
    const signature = body.razorpay_signature;

    if (!planCode || !(planCode in BILLING_PLANS) || !orderId || !paymentId || !signature) {
      return jsonError(res, 400, 'invalid_payload', 'Payment verification payload is incomplete.');
    }

    if (!verifySignature(orderId, paymentId, signature, keySecret)) {
      return jsonError(res, 400, 'invalid_signature', 'Razorpay signature verification failed.');
    }

    const user = await fetchCurrentUser(apiBase, authorization);
    const plan = BILLING_PLANS[planCode];
    const razorpay = new Razorpay({ key_id: keyId, key_secret: keySecret });
    const payment = await razorpay.payments.fetch(paymentId);

    if (payment.order_id !== orderId) {
      return jsonError(res, 400, 'order_mismatch', 'Payment order mismatch detected.');
    }

    if (payment.amount !== plan.amountPaise || payment.currency !== 'INR') {
      return jsonError(res, 400, 'amount_mismatch', 'Payment amount validation failed.');
    }

    const notes = payment.notes && typeof payment.notes === 'object' ? payment.notes as Record<string, unknown> : {};
    const providerSubscriptionId = typeof notes.razorpay_subscription_id === 'string' ? notes.razorpay_subscription_id : null;

    const activateResponse = await fetch(`${apiBase}/api/v1/billing/internal/activate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-API-Secret': internalSecret,
      },
      body: JSON.stringify({
        user_id: user.id,
        plan_code: plan.code,
        razorpay_order_id: orderId,
        razorpay_payment_id: paymentId,
        amount_paise: payment.amount,
        currency: payment.currency,
        status: mapPaymentStatus(payment.status),
        signature_verified: true,
        provider_subscription_id: providerSubscriptionId,
        paid_at: typeof payment.created_at === 'number' ? new Date(payment.created_at * 1000).toISOString() : null,
        raw_payload: payment,
      }),
    });

    if (!activateResponse.ok) {
      const errorBody = await activateResponse.json().catch(() => null);
      return jsonError(
        res,
        502,
        'subscription_activation_failed',
        typeof errorBody?.detail === 'string' ? errorBody.detail : 'Unable to activate subscription.',
      );
    }

    const subscription = await activateResponse.json();
    return res.status(200).json({ ok: true, subscription });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unable to verify Razorpay payment.';
    return jsonError(res, 500, 'verify_payment_failed', message);
  }
}
