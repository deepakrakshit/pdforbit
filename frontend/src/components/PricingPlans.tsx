import CheckoutButton from '@/components/CheckoutButton';
import { getBillingPlan } from '@/lib/razorpay';

interface PricingPlansProps {
  onSuccess?: () => void;
}

export default function PricingPlans({ onSuccess }: PricingPlansProps) {
  const monthlyPlan = getBillingPlan('PRO_MONTHLY');
  const yearlyPlan = getBillingPlan('PRO_YEARLY');

  return (
    <div className="billing-modal-grid">
      <div className="billing-modal-card">
        <div className="pc-name billing-modal-title">{monthlyPlan.name}</div>
        <div className="pc-period">{monthlyPlan.description}</div>
        <CheckoutButton planCode="PRO_MONTHLY" className="btn btn-red btn-lg pricing-cta" onSuccess={onSuccess}>
          Subscribe Monthly · {monthlyPlan.priceLabel}
        </CheckoutButton>
      </div>
      <div className="billing-modal-card featured">
        <div className="pricing-badge">Best Value</div>
        <div className="pc-name billing-modal-title">{yearlyPlan.name}</div>
        <div className="pc-period">{yearlyPlan.description}</div>
        <CheckoutButton planCode="PRO_YEARLY" className="btn btn-red btn-lg pricing-cta" onSuccess={onSuccess}>
          Subscribe Yearly · {yearlyPlan.priceLabel}
        </CheckoutButton>
      </div>
    </div>
  );
}
