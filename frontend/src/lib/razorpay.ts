import type { UserProfile } from '@/lib/auth';

export type BillingPlanCode = 'PRO_MONTHLY' | 'PRO_YEARLY';
export type SubscriptionStatus = 'inactive' | 'active' | 'cancelled' | 'expired';
export type SubscriptionInterval = 'monthly' | 'yearly';

export interface BillingPlanDefinition {
  code: BillingPlanCode;
  name: string;
  shortLabel: string;
  amountPaise: number;
  priceLabel: string;
  periodLabel: string;
  description: string;
  interval: SubscriptionInterval;
}

export interface SubscriptionSnapshot {
  user_id: string;
  plan_type: 'free' | 'pro' | 'enterprise';
  credits_remaining: number;
  credit_limit: number;
  subscription_status: SubscriptionStatus;
  subscription_interval: SubscriptionInterval | null;
  subscription_started_at: string | null;
  subscription_expires_at: string | null;
}

export interface CreateOrderResponse {
  orderId: string;
  keyId: string;
  currency: string;
  amount: number;
  planCode: BillingPlanCode;
  planName: string;
  description: string;
  prefill: {
    email: string;
  };
}

export interface VerifyPaymentResponse {
  ok: true;
  subscription: SubscriptionSnapshot;
}

export interface RazorpaySuccessPayload {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

export const BILLING_PLANS: Record<BillingPlanCode, BillingPlanDefinition> = {
  PRO_MONTHLY: {
    code: 'PRO_MONTHLY',
    name: 'Pro Monthly',
    shortLabel: 'Monthly',
    amountPaise: 50000,
    priceLabel: '₹500',
    periodLabel: 'per month',
    description: '1000 credits per day with verified Pro activation after successful server-side payment checks.',
    interval: 'monthly',
  },
  PRO_YEARLY: {
    code: 'PRO_YEARLY',
    name: 'Pro Yearly',
    shortLabel: 'Yearly',
    amountPaise: 240000,
    priceLabel: '₹2400',
    periodLabel: 'per year',
    description: 'Best value at an effective ₹200/month with the same verified Pro benefits and annual billing.',
    interval: 'yearly',
  },
};

function readErrorMessage(payload: unknown, fallback: string): string {
  if (typeof payload === 'string' && payload.trim()) {
    return payload;
  }

  if (payload && typeof payload === 'object') {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }

    const message = (payload as { message?: unknown }).message;
    if (typeof message === 'string' && message.trim()) {
      return message;
    }
  }

  return fallback;
}

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(path, init);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(readErrorMessage(body, `Request failed (${response.status})`));
  }

  return response.json() as Promise<T>;
}

let checkoutLoader: Promise<void> | null = null;

export function getBillingPlan(planCode: BillingPlanCode): BillingPlanDefinition {
  return BILLING_PLANS[planCode];
}

export function getEnterpriseContactUrl(): string {
  return '/enterprise#contact-sales-form';
}

export function hasActiveProSubscription(user: UserProfile | null): boolean {
  if (!user) {
    return false;
  }

  return user.plan_type === 'pro' && user.subscription_status === 'active';
}

export async function loadRazorpayCheckoutScript(): Promise<void> {
  if (typeof window === 'undefined') {
    throw new Error('Razorpay checkout can only be loaded in the browser.');
  }

  if ((window as Window & { Razorpay?: unknown }).Razorpay) {
    return;
  }

  if (!checkoutLoader) {
    checkoutLoader = new Promise<void>((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Failed to load Razorpay checkout.'));
      document.body.appendChild(script);
    });
  }

  await checkoutLoader;
}

export async function createCheckoutOrder(accessToken: string, planCode: BillingPlanCode): Promise<CreateOrderResponse> {
  return requestJson<CreateOrderResponse>('/api/create-order', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ planCode }),
  });
}

export async function verifyCheckoutPayment(
  accessToken: string,
  planCode: BillingPlanCode,
  payload: RazorpaySuccessPayload,
): Promise<VerifyPaymentResponse> {
  return requestJson<VerifyPaymentResponse>('/api/verify-payment', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ planCode, ...payload }),
  });
}
