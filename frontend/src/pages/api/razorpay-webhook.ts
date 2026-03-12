import { createHmac, timingSafeEqual } from 'crypto';
import type { NextApiRequest, NextApiResponse } from 'next';

export const config = {
  api: {
    bodyParser: false,
  },
};

function jsonError(res: NextApiResponse, statusCode: number, code: string, message: string) {
  return res.status(statusCode).json({ code, detail: message });
}

async function readRawBody(req: NextApiRequest): Promise<Buffer> {
  const chunks: Uint8Array[] = [];

  for await (const chunk of req) {
    chunks.push(typeof chunk === 'string' ? Buffer.from(chunk) : chunk);
  }

  return Buffer.concat(chunks);
}

function verifyWebhookSignature(rawBody: Buffer, signature: string, secret: string): boolean {
  const digest = createHmac('sha256', secret).update(rawBody).digest('hex');
  const expected = Buffer.from(digest, 'utf8');
  const actual = Buffer.from(signature, 'utf8');

  if (expected.length !== actual.length) {
    return false;
  }

  return timingSafeEqual(expected, actual);
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return jsonError(res, 405, 'method_not_allowed', 'Only POST is supported.');
  }

  try {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, '');
    const internalSecret = process.env.BILLING_INTERNAL_API_SECRET;
    const webhookSecret = process.env.RAZORPAY_WEBHOOK_SECRET;
    const signature = req.headers['x-razorpay-signature'];

    if (!apiBase || !internalSecret || !webhookSecret) {
      return jsonError(res, 500, 'billing_env_missing', 'Billing environment variables are not configured.');
    }

    if (typeof signature !== 'string') {
      return jsonError(res, 401, 'missing_signature', 'Missing Razorpay webhook signature.');
    }

    const rawBody = await readRawBody(req);
    if (!verifyWebhookSignature(rawBody, signature, webhookSecret)) {
      return jsonError(res, 401, 'invalid_signature', 'Razorpay webhook signature verification failed.');
    }

    const payload = JSON.parse(rawBody.toString('utf8')) as { event?: string } & Record<string, unknown>;
    const eventName = typeof payload.event === 'string' ? payload.event : '';
    const supportedEvents = new Set(['payment.captured', 'subscription.charged', 'subscription.cancelled']);

    if (!supportedEvents.has(eventName)) {
      return res.status(202).json({ received: true, handled: false, event: eventName || 'unknown' });
    }

    const backendResponse = await fetch(`${apiBase}/api/v1/billing/internal/webhook`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-API-Secret': internalSecret,
      },
      body: JSON.stringify({
        event: eventName,
        payload,
      }),
    });

    if (!backendResponse.ok) {
      const errorBody = await backendResponse.json().catch(() => null);
      return jsonError(
        res,
        502,
        'webhook_sync_failed',
        typeof errorBody?.detail === 'string' ? errorBody.detail : 'Unable to persist webhook event.',
      );
    }

    return res.status(200).json({ received: true, handled: true, event: eventName });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unable to process Razorpay webhook.';
    return jsonError(res, 500, 'webhook_processing_failed', message);
  }
}
