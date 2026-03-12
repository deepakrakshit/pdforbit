import { useRouter } from 'next/router';
import { useState } from 'react';
import type { ReactNode } from 'react';
import { useAuth } from '@/components/AuthProvider';
import { useToast } from '@/components/Toast';
import {
  createCheckoutOrder,
  getBillingPlan,
  loadRazorpayCheckoutScript,
  verifyCheckoutPayment,
  type BillingPlanCode,
  type RazorpaySuccessPayload,
} from '@/lib/razorpay';

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => {
      open: () => void;
    };
  }
}

interface CheckoutButtonProps {
  planCode: BillingPlanCode;
  className?: string;
  children: ReactNode;
  onSuccess?: () => Promise<void> | void;
}

export default function CheckoutButton({ planCode, className, children, onSuccess }: CheckoutButtonProps) {
  const router = useRouter();
  const { accessToken, refreshUser } = useAuth();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);

  const handleCheckout = async () => {
    if (!accessToken) {
      await router.push(`/login?redirect=${encodeURIComponent('/pricing')}`);
      return;
    }

    setIsLoading(true);

    try {
      await loadRazorpayCheckoutScript();
      const order = await createCheckoutOrder(accessToken, planCode);
      const plan = getBillingPlan(planCode);

      if (!window.Razorpay) {
        throw new Error('Razorpay checkout is unavailable.');
      }

      const checkout = new window.Razorpay({
        key: order.keyId,
        amount: order.amount,
        currency: order.currency,
        name: 'PdfORBIT',
        description: order.description,
        order_id: order.orderId,
        prefill: order.prefill,
        notes: {
          plan_code: plan.code,
        },
        theme: {
          color: '#f25f5c',
        },
        modal: {
          ondismiss: () => {
            setIsLoading(false);
          },
        },
        handler: async (payload: RazorpaySuccessPayload) => {
          try {
            await verifyCheckoutPayment(accessToken, planCode, payload);
            await refreshUser();
            await onSuccess?.();
            toast('success', `${plan.name} activated`, 'Your account has been upgraded and your daily Pro credits are live.');
          } catch (error) {
            const message = error instanceof Error ? error.message : 'Payment verification failed.';
            toast('error', 'Payment verification failed', message);
          } finally {
            setIsLoading(false);
          }
        },
      });

      checkout.open();
    } catch (error) {
      setIsLoading(false);
      const message = error instanceof Error ? error.message : 'Unable to start checkout.';
      toast('error', `${getBillingPlan(planCode).name} checkout failed`, message);
    }
  };

  return (
    <button
      type="button"
      className={className}
      onClick={() => {
        void handleCheckout();
      }}
      disabled={isLoading}
    >
      {isLoading ? 'Processing...' : children}
    </button>
  );
}
